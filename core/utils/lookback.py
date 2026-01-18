import re
import pandas as pd
from datetime import timedelta

_LOOKBACK_RE = re.compile(r"^(\d+)([hdwmy])$")

_UNIT_TO_DELTA = {
    "h": lambda n: timedelta(hours=n),
    "d": lambda n: timedelta(days=n),
    "w": lambda n: timedelta(weeks=n),
    "m": lambda n: timedelta(days=30 * n),   # miesiąc ≈ 30 dni
    "y": lambda n: timedelta(days=365 * n),  # rok ≈ 365 dni
}


def parse_lookback(lookback: str, *, now: pd.Timestamp | None = None) -> pd.Timestamp:
    """
    Zamienia np. '30d', '24h', '3y' na timestamp startowy (UTC).

    Zwraca:
        pd.Timestamp (UTC)
    """
    if now is None:
        now = pd.Timestamp.utcnow()

    if not isinstance(lookback, str):
        raise TypeError(f"lookback must be str, got {type(lookback)}")

    m = _LOOKBACK_RE.match(lookback.lower())
    if not m:
        raise ValueError(
            f"Invalid lookback format: {lookback} "
            f"(expected e.g. '24h', '7d', '3y')"
        )

    value = int(m.group(1))
    unit = m.group(2)

    delta_fn = _UNIT_TO_DELTA.get(unit)
    if delta_fn is None:
        raise ValueError(f"Unsupported lookback unit: {unit}")

    start = now - delta_fn(value)
    return start.tz_localize("UTC") if start.tzinfo is None else start