from datetime import UTC, datetime


def str_to_dt_utc(date: str) -> datetime:
    return datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=UTC)
