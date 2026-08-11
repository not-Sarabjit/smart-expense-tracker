from datetime import date


def last_day_of_month(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    from datetime import timedelta
    return date(year, month + 1, 1) - timedelta(days=1)