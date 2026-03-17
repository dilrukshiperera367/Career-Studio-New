"""Leave attendance utility functions."""
from datetime import date, timedelta


def working_days_between(start: date, end: date) -> int:
    """
    Calculate the number of working days (Mon–Fri) between start and end (inclusive).
    Returns 0 if end < start.
    """
    if end < start:
        return 0
    count = 0
    current = start
    while current <= end:
        if current.weekday() < 5:  # 0=Mon … 4=Fri
            count += 1
        current += timedelta(days=1)
    return count
