from openai import OpenAI
from collections import Counter
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT = """
You are a business operations expert.

Classify this business message into ONE category:

Categories:
- Order Status
- Refund/Return
- Payment Issue
- Sales Lead
- Vendor Communication
- HR/Admin
- Other

Message:
"""

def classify_message(message):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": PROMPT + message}
            ]
        )
        return response.choices[0].message.content.strip()
    except:
        return "Other"

def classify_bulk(messages):
    counts = Counter()
    for msg in messages[:100]:  # limit cost
        category = classify_message(msg)
        counts[category] += 1
    return counts
