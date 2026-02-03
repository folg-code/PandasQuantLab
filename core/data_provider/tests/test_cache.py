import pandas as pd

from core.data_provider import CsvMarketDataCache


def test_coverage_none_when_missing(tmp_path):
    c = CsvMarketDataCache(tmp_path)
    assert c.coverage(symbol="EURUSD", timeframe="M1") is None

def test_save_skips_empty(tmp_path):
    c = CsvMarketDataCache(tmp_path)
    c.save(symbol="EURUSD", timeframe="M1", df=pd.DataFrame())
    assert c.coverage(symbol="EURUSD", timeframe="M1") is None

def test_load_range_filters_inclusive(tmp_path):
    c = CsvMarketDataCache(tmp_path)

    df = pd.DataFrame({
        "time": pd.date_range("2022-01-01 00:00:00", periods=11, freq="1min", tz="UTC"),
        "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1.0,
    })
    c.save(symbol="EURUSD", timeframe="M1", df=df)

    start = pd.Timestamp("2022-01-01 00:03:00", tz="UTC")
    end   = pd.Timestamp("2022-01-01 00:05:00", tz="UTC")

    out = c.load_range(symbol="EURUSD", timeframe="M1", start=start, end=end)
    assert out["time"].tolist() == list(pd.date_range(start, end, freq="1min", tz="UTC"))

def test_append_guard_no_change(tmp_path):
    c = CsvMarketDataCache(tmp_path)
    base = pd.DataFrame({
        "time": pd.date_range("2022-01-01 00:00:00", periods=3, freq="1min", tz="UTC"),
        "open": [1,1,1], "high":[1,1,1], "low":[1,1,1], "close":[1,1,1], "volume":[1.0]*3,
    })
    c.save(symbol="EURUSD", timeframe="M1", df=base)

    c.append(symbol="EURUSD", timeframe="M1", df=base.copy())

    out = c.load_range(
        symbol="EURUSD", timeframe="M1",
        start=base["time"].min(), end=base["time"].max()
    )
    assert len(out) == 3