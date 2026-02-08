def estimate_hours_saved(issue_count):
    minutes_per_email = 8
    hours = (issue_count * minutes_per_email) / 60
    return round(hours, 2)

def estimate_money_saved(hours):
    hourly_salary = 300  # ₹ per hour (basic support staff)
    return int(hours * hourly_salary)
