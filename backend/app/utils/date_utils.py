from datetime import date, datetime, timezone


def last_day_of_month(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    from datetime import timedelta

    return date(year, month + 1, 1) - timedelta(days=1)



def utcnow() -> datetime:
    """Current UTC time as a naive datetime, with microsecond precision.

    Used as a Python-side column default so that:
      * SQLite gets sub-second precision (CURRENT_TIMESTAMP only has seconds,
        which makes rows created in the same second unorderable);
      * Postgres gets the real wall clock instead of now(), which returns the
        *transaction start* time and is therefore identical for every row
        written in one transaction.

    Naive (tzinfo stripped) because the DateTime columns in this schema are
    `TIMESTAMP WITHOUT TIME ZONE`. Everything stored is UTC by convention.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)