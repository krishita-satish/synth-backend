def generate_report(results, hours_func, money_func):
    report = "\nAI Opportunity Audit Report\n"
    report += "-----------------------------\n"

    for category, count in results.items():
        hours = hours_func(count)
        money = money_func(hours)

        report += f"\n{category}\n"
        report += f"Emails per month: {count}\n"
        report += f"Hours saved/month: {hours}\n"
        report += f"Money saved/month: ₹{money}\n"

    return report
