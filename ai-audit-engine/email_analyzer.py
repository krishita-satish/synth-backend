from collections import Counter

CATEGORIES = {
    "Order Status": ["where is my order", "tracking"],
    "Refund/Return": ["refund", "return"],
    "Payment Issues": ["payment failed", "charged"],
}

def analyze_emails(email_list):
    counts = Counter()

    for email in email_list:
        text = email.lower()

        for category, keywords in CATEGORIES.items():
            if any(keyword in text for keyword in keywords):
                counts[category] += 1

    return counts
