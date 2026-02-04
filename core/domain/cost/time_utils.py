from datetime import datetime, timedelta


def to_dt(x) -> datetime:
    if hasattr(x, "to_pydatetime"):
        return x.to_pydatetime()
    if isinstance(x, datetime):
        return x
    return datetime.fromisoformat(str(x))


def rollover_anchor(dt: datetime, hour: int, minute: int) -> datetime:
    return dt.replace(hour=hour, minute=minute, second=0, microsecond=0)


def count_rollovers(entry_time: datetime, exit_time: datetime, hour: int, minute: int) -> list[datetime]:
    if exit_time <= entry_time:
        return []

    t = rollover_anchor(entry_time, hour, minute)
    if t <= entry_time:
        t += timedelta(days=1)

    out = []
    while t <= exit_time:
        out.append(t)
        t += timedelta(days=1)
    return out