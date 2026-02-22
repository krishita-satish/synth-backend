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
    """Build a detailed system prompt with industry-specific context and examples."""
    categories = INDUSTRY_CATEGORIES.get(industry, INDUSTRY_CATEGORIES["general"])
    category_list = "\n".join(f"  - {cat}" for cat in categories)
    
    industry_context = f"The dataset is for the {industry.replace('_', ' ').title()} industry."
    if industry == "general":
        industry_context = "The dataset covers a wide range of business operations."

    examples = {
        "sales": """
- "I'm interested in your enterprise plan for our 50-person team" -> New Lead
- "Just checking in if you had a chance to look at the contract" -> Follow-up
- "We need to see a live demo of the dashboard" -> Demo Request
- "The proposed price is slightly outside our budget" -> Negotiation""",
        "it_helpdesk": """
- "My laptop won't turn on after the update" -> Hardware Issue
- "I can't access the shared drive since morning" -> Access/Permissions
- "Is the guest wifi down?" -> Network/Connectivity
- "Please install Photoshop on my machine" -> Setup/Installation""",
        "hr_admin": """
- "When is the deadline for tax declarations?" -> Policy Question
- "Seeking approval for my October vacation" -> Leave Request
- "I haven't received my payslip for this month" -> Payroll Query
- "How do I add my spouse to the health insurance?" -> Benefits Inquiry""",
    }
    
    few_shot = examples.get(industry, """
- "Where is my order #12345?" -> Order Status
- "The product arrived damaged" -> Refund/Return
- "Why was I charged twice?" -> Payment Issue
- "I'm interested in your services" -> Sales Lead""")

    return f"""You are a senior business operations analyst. 
{industry_context}

Your task: Classify each message into EXACTLY ONE category from the list below.

## Categories
{category_list}

## Rules
1. Choose the SINGLE most relevant category.
2. If a message fits multiple categories, choose the primary intent.
3. Use "Other" ONLY when the message is completely irrelevant or junk (noise).
4. Do not classify noise (like IDs, single numbers, or random fragments) into specific categories; use "Other" for these.

## Examples
{few_shot}

## Output Format
Respond with ONLY a valid JSON array. Each element must be an object:
[{{"index": 0, "category": "... category ...", "confidence": 95}}]

Example:
[{{"index": 0, "category": "{categories[0]}", "confidence": 95}}]
"""


def classify_batch(messages: list[str], industry: str = "general", batch_size: int = 10) -> Counter:
    """
    Classify messages in batches to reduce API calls and provide industry context.
    """
    counts = Counter()
    total = len(messages)

    if not messages:
        return counts

    for i in range(0, total, batch_size):
        batch = messages[i : i + batch_size]
        numbered_messages = "\n".join(
            f"[Message {j}]: {msg[:800]}" for j, msg in enumerate(batch)
        )

        try:
            response = _get_client().chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": _build_system_prompt(industry)},
                    {"role": "user", "content": f"Classify these {len(batch)} messages:\n\n{numbered_messages}"},
                ],
                temperature=0.0,
                max_tokens=2000,
            )

            result_text = response.choices[0].message.content.strip()
            # print(f"DEBUG: AI Response for batch {i//batch_size}:\n{result_text}")
            
            # More robust JSON cleanup
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            data = json.loads(result_text)
            
            # Identify the list of classifications
            classifications = []
            if isinstance(data, list):
                classifications = data
            elif isinstance(data, dict):
                # Look for common keys: 'classifications', 'results', 'data'
                for key in ['classifications', 'results', 'data', 'items']:
                    if key in data and isinstance(data[key], list):
                        classifications = data[key]
                        break
                if not classifications:
                    # Maybe it's an object where values are the items? No, usually it's a list.
                    # Just take the first list found in values
                    for val in data.values():
                        if isinstance(val, list):
                            classifications = val
                            break

            valid_categories = set(INDUSTRY_CATEGORIES.get(industry, INDUSTRY_CATEGORIES["general"]))

            for item in classifications:
                raw_category = item.get("category", "Other")
                category = "Other"
                
                # Try exact match
                if raw_category in valid_categories:
                    category = raw_category
                else:
                    # Try case-insensitive and partial matches
                    for valid in valid_categories:
                        if valid.lower() == raw_category.lower() or valid.lower() in raw_category.lower():
                            category = valid
                            break
                
                counts[category] += 1

        except Exception as e:
            print(f"Batch parse error: {e}")
            for msg in batch:
                cat = _classify_single(msg, industry)
                counts[cat] += 1

    return counts


def _classify_single(message: str, industry: str = "general") -> str:
    """Fallback: classify a single message with industry context."""
    categories = INDUSTRY_CATEGORIES.get(industry, INDUSTRY_CATEGORIES["general"])
    category_list = ", ".join(categories)

    try:
        response = _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"Classify this {industry} sector message into EXACTLY ONE category: {category_list}. Reply with ONLY the category name.",
                },
                {"role": "user", "content": message[:1000]},
            ],
            temperature=0.0,
            max_tokens=50,
        )
        result = response.choices[0].message.content.strip()
        
        # Match result to categories
        for cat in categories:
            if cat.lower() == result.lower() or cat.lower() in result.lower():
                return cat
        return "Other"
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
        response = _get_client().chat.completions.create(
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
