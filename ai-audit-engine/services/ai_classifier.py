import os
import json
from openai import OpenAI
from collections import Counter

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

# ─── Industry-specific category sets ───────────────────────────────────
INDUSTRY_CATEGORIES = {
    "general": [
        "Order Status",
        "Refund/Return",
        "Payment Issue",
        "Sales Lead",
        "Vendor Communication",
        "HR/Admin",
        "Customer Complaint",
        "Technical Support",
        "Billing Inquiry",
        "Other",
    ],
    "ecommerce": [
        "Order Status",
        "Refund/Return",
        "Payment Issue",
        "Shipping/Delivery",
        "Product Inquiry",
        "Inventory/Stock",
        "Pricing/Discount",
        "Account Issue",
        "Other",
    ],
    "customer_support": [
        "Account Access",
        "Billing Inquiry",
        "Technical Issue",
        "Feature Request",
        "Bug Report",
        "Complaint/Escalation",
        "General Inquiry",
        "Cancellation",
        "Other",
    ],
    "hr_admin": [
        "Leave Request",
        "Payroll Query",
        "Onboarding",
        "Policy Question",
        "Benefits Inquiry",
        "Performance Review",
        "Training Request",
        "Compliance",
        "Other",
    ],
    "sales": [
        "New Lead",
        "Follow-up",
        "Demo Request",
        "Proposal/Quote",
        "Negotiation",
        "Closing",
        "Upsell/Cross-sell",
        "Lost Deal",
        "Other",
    ],
    "it_helpdesk": [
        "Access/Permissions",
        "Software Issue",
        "Hardware Issue",
        "Network/Connectivity",
        "Email Issue",
        "Security Concern",
        "Setup/Installation",
        "Data Recovery",
        "Other",
    ],
}


def _build_system_prompt(industry: str = "general") -> str:
    """Build a detailed system prompt with few-shot examples for the classifier."""
    categories = INDUSTRY_CATEGORIES.get(industry, INDUSTRY_CATEGORIES["general"])
    category_list = "\n".join(f"  - {cat}" for cat in categories)

    return f"""You are an expert business operations analyst specializing in workflow classification.

Your task: Classify each business message into EXACTLY ONE category from the list below.

## Categories
{category_list}

## Rules
1. Choose the SINGLE most relevant category
2. If a message fits multiple categories, choose the primary intent
3. Use "Other" only when no category clearly fits
4. Be consistent — similar messages should get the same category

## Few-Shot Examples (General)
- "Where is my order #12345? It's been 5 days" → Order Status
- "I want a refund for the damaged item I received" → Refund/Return
- "My card was charged twice for the same order" → Payment Issue
- "Hi, I'm interested in your enterprise plan pricing" → Sales Lead
- "Please send the updated invoice for PO-2024-001" → Vendor Communication
- "Can I take leave from March 10-15?" → HR/Admin
- "The checkout page keeps showing an error" → Technical Support
- "Your service is terrible, I've been waiting 2 weeks" → Customer Complaint
- "Why was I charged $50 extra this month?" → Billing Inquiry

## Output Format
Respond with ONLY a valid JSON array. Each element should be an object with:
- "index": the message number (starting from 0)
- "category": one of the categories listed above
- "confidence": a number 0-100 indicating classification confidence

Example output:
[{{"index": 0, "category": "Order Status", "confidence": 95}}, {{"index": 1, "category": "Refund/Return", "confidence": 88}}]
"""


def classify_batch(messages: list[str], industry: str = "general", batch_size: int = 10) -> Counter:
    """
    Classify messages in batches to reduce API calls.
    Instead of 1 API call per message, we send batch_size messages per call.
    100 messages = 10 API calls instead of 100 (90% cost reduction).
    """
    counts = Counter()
    confidence_scores = []
    total = len(messages)

    for i in range(0, total, batch_size):
        batch = messages[i : i + batch_size]
        numbered_messages = "\n".join(
            f"[Message {j}]: {msg[:500]}" for j, msg in enumerate(batch)  # truncate long messages
        )

        try:
            response = _get_client().chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": _build_system_prompt(industry)},
                    {"role": "user", "content": f"Classify these {len(batch)} messages:\n\n{numbered_messages}"},
                ],
                temperature=0.1,  # low temperature for consistent classification
                max_tokens=2000,
            )

            result_text = response.choices[0].message.content.strip()

            # Parse JSON response
            # Handle cases where model wraps in markdown code block
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1]
                result_text = result_text.rsplit("```", 1)[0]

            classifications = json.loads(result_text)

            for item in classifications:
                category = item.get("category", "Other")
                confidence = item.get("confidence", 50)

                # Validate category exists
                valid_categories = INDUSTRY_CATEGORIES.get(industry, INDUSTRY_CATEGORIES["general"])
                if category not in valid_categories:
                    category = "Other"

                counts[category] += 1
                confidence_scores.append(confidence)

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"⚠️ Batch parse error: {e}, falling back to individual classification")
            # Fallback: classify individually
            for msg in batch:
                cat = _classify_single(msg, industry)
                counts[cat] += 1
        except Exception as e:
            print(f"⚠️ API error on batch: {e}")
            for _ in batch:
                counts["Other"] += 1

    return counts


def _classify_single(message: str, industry: str = "general") -> str:
    """Fallback: classify a single message (used when batch parsing fails)."""
    categories = INDUSTRY_CATEGORIES.get(industry, INDUSTRY_CATEGORIES["general"])
    category_list = ", ".join(categories)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"Classify this message into ONE category: {category_list}. Reply with ONLY the category name.",
                },
                {"role": "user", "content": message[:500]},
            ],
            temperature=0.1,
            max_tokens=50,
        )
        result = response.choices[0].message.content.strip()
        return result if result in categories else "Other"
    except Exception:
        return "Other"


def classify_bulk(messages: list, industry: str = "general") -> Counter:
    """
    Main entry point — classifies up to 200 messages using batch processing.
    Backward compatible with the old API.
    """
    # Limit to 200 messages to control costs
    limited = [str(m) for m in messages[:200] if str(m).strip()]
    if not limited:
        return Counter({"Other": 1})

    return classify_batch(limited, industry=industry, batch_size=10)


def get_available_industries() -> list[str]:
    """Return list of supported industry templates."""
    return list(INDUSTRY_CATEGORIES.keys())


def generate_recommendations(category_counts: Counter, total_messages: int, industry: str = "general") -> list[str]:
    """
    Use AI to generate specific, actionable recommendations based on the actual audit data.
    """
    # Build a summary of findings
    top_categories = category_counts.most_common(5)
    findings_text = "\n".join(
        f"- {cat}: {count} messages ({int(count / total_messages * 100)}%)"
        for cat, count in top_categories
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are an AI automation consultant. Based on the business audit data provided,
generate 5-7 specific, actionable recommendations for AI automation.

Each recommendation should:
1. Reference the specific category/area from the data
2. Include a concrete AI solution (chatbot, classifier, workflow automation, etc.)
3. Estimate the impact (time saved, efficiency gain)
4. Be implementable within 1-3 months

Respond with a JSON array of strings, each being one recommendation.
Example: ["Deploy an AI chatbot to handle Order Status queries (35% of volume) — estimated 120 hours/month saved", ...]""",
                },
                {
                    "role": "user",
                    "content": f"""Industry: {industry}
Total messages analyzed: {total_messages}

Category breakdown:
{findings_text}

Generate specific automation recommendations based on this data.""",
                },
            ],
            temperature=0.7,
            max_tokens=1500,
        )

        result_text = response.choices[0].message.content.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1]
            result_text = result_text.rsplit("```", 1)[0]

        recommendations = json.loads(result_text)
        if isinstance(recommendations, list):
            return recommendations[:7]

    except Exception as e:
        print(f"⚠️ Recommendation generation failed: {e}")

    # Fallback: rule-based recommendations
    recommendations = []
    for cat, count in top_categories:
        pct = int(count / total_messages * 100)
        if pct > 15:
            recommendations.append(
                f"Deploy AI automation for '{cat}' — {pct}% of your volume ({count} messages). "
                f"Estimated time savings: {count * 8 // 60} hours/month."
            )
        elif pct > 5:
            recommendations.append(
                f"Consider AI-assisted handling for '{cat}' ({pct}% of volume) to reduce manual processing."
            )

    if not recommendations:
        recommendations.append("Implement a general AI email triage system to auto-route messages to the right team.")

    return recommendations
