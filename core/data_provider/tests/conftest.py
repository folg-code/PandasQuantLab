import pandas as pd
import pytest

def make_ohlcv(start: str, periods: int, freq: str, *, dup_last=False):
    idx = pd.date_range(start=start, periods=periods, freq=freq, tz="UTC")
    df = pd.DataFrame({
        "time": idx,
        "open": range(periods),
        "high": range(periods),
        "low": range(periods),
        "close": range(periods),
        "volume": [1.0] * periods,
    })
    if dup_last:
        df = pd.concat([df, df.tail(1).assign(close=999)], ignore_index=True)
    return df

class FakeBackend:
    def __init__(self, frames_by_key):
        self.frames_by_key = frames_by_key
        self.calls = []

    def fetch_ohlcv(self, *, symbol, timeframe, start, end):
        self.calls.append((symbol, timeframe, pd.Timestamp(start), pd.Timestamp(end)))
        key = (symbol, timeframe, pd.Timestamp(start), pd.Timestamp(end))
        return self.frames_by_key.get(key, pd.DataFrame(columns=["time","open","high","low","close","volume"]))

@pytest.fixture
def utc():
    return lambda s: pd.Timestamp(s, tz="UTC")