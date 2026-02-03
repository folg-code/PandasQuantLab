import pandas as pd
import pytest

from core.data_provider.backends.dukascopy import DukascopyBackend
from core.data_provider.exceptions import DataNotAvailable


class DummyClient:
    def __init__(self, *, df=None, exc=None):
        self.df = df
        self.exc = exc
        self.calls = []

    def get_ohlcv(self, *, symbol, timeframe, start, end):
        self.calls.append((symbol, timeframe, start, end))
        if self.exc:
            raise self.exc
        return self.df


def _ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s)


def _df_ok_unsorted_with_dups():
    return pd.DataFrame(
        {
            "TiMe": ["2022-01-01 00:01:00", "2022-01-01 00:00:00", "2022-01-01 00:01:00"],
            "OPEN": [1, 1, 1],
            "High": [2, 2, 2],
            "low": [0.5, 0.5, 0.5],
            "CLOSE": [10, 9, 999],
            "VOLUME": [100, 100, 200],
        }
    )


def test_fetch_ohlcv_raises_when_start_ge_end():
    backend = DukascopyBackend(client=DummyClient(df=_df_ok_unsorted_with_dups()))
    with pytest.raises(ValueError, match="start must be earlier than end"):
        backend.fetch_ohlcv(
            symbol="EURUSD",
            timeframe="M1",
            start=pd.Timestamp("2022-01-01 00:00:00", tz="UTC"),
            end=pd.Timestamp("2022-01-01 00:00:00", tz="UTC"),
        )


def test_fetch_ohlcv_localizes_naive_timestamps_to_utc():
    df = _df_ok_unsorted_with_dups()
    client = DummyClient(df=df)
    backend = DukascopyBackend(client=client)

    start = _ts("2022-01-01 00:00:00")
    end = _ts("2022-01-01 00:02:00")

    out = backend.fetch_ohlcv(symbol="EURUSD", timeframe="M1", start=start, end=end)

    _, _, call_start, call_end = client.calls[0]
    assert call_start.tzinfo is not None and str(call_start.tzinfo) in ("UTC", "UTC+00:00")
    assert call_end.tzinfo is not None and str(call_end.tzinfo) in ("UTC", "UTC+00:00")

    assert out["time"].dt.tz is not None
    assert out["time"].is_monotonic_increasing
    assert out.loc[out["time"] == pd.Timestamp("2022-01-01 00:01:00", tz="UTC"), "close"].iloc[0] == 999


def test_fetch_ohlcv_converts_aware_timestamps_to_utc():
    df = _df_ok_unsorted_with_dups()
    client = DummyClient(df=df)
    backend = DukascopyBackend(client=client)

    start = pd.Timestamp("2022-01-01 01:00:00", tz="Europe/Warsaw")  # CET
    end = pd.Timestamp("2022-01-01 01:02:00", tz="Europe/Warsaw")

    backend.fetch_ohlcv(symbol="EURUSD", timeframe="M1", start=start, end=end)

    _, _, call_start, call_end = client.calls[0]
    assert str(call_start.tzinfo) in ("UTC", "UTC+00:00")
    assert str(call_end.tzinfo) in ("UTC", "UTC+00:00")


def test_fetch_ohlcv_wraps_client_exception_as_DataNotAvailable():
    client = DummyClient(exc=RuntimeError("boom"))
    backend = DukascopyBackend(client=client)

    with pytest.raises(DataNotAvailable, match="Failed to fetch Dukascopy data"):
        backend.fetch_ohlcv(
            symbol="EURUSD",
            timeframe="M1",
            start=pd.Timestamp("2022-01-01 00:00:00", tz="UTC"),
            end=pd.Timestamp("2022-01-01 00:01:00", tz="UTC"),
        )


def test_fetch_ohlcv_raises_DataNotAvailable_on_none_or_empty():
    backend1 = DukascopyBackend(client=DummyClient(df=None))
    with pytest.raises(DataNotAvailable, match="No Dukascopy data"):
        backend1.fetch_ohlcv(
            symbol="EURUSD",
            timeframe="M1",
            start=pd.Timestamp("2022-01-01 00:00:00", tz="UTC"),
            end=pd.Timestamp("2022-01-01 00:01:00", tz="UTC"),
        )

    # empty
    backend2 = DukascopyBackend(client=DummyClient(df=pd.DataFrame()))
    with pytest.raises(DataNotAvailable, match="No Dukascopy data"):
        backend2.fetch_ohlcv(
            symbol="EURUSD",
            timeframe="M1",
            start=pd.Timestamp("2022-01-01 00:00:00", tz="UTC"),
            end=pd.Timestamp("2022-01-01 00:01:00", tz="UTC"),
        )


def test_normalize_raises_on_missing_columns():
    df = pd.DataFrame({"time": ["2022-01-01"], "open": [1]})  # brak reszty
    with pytest.raises(ValueError, match="missing columns"):
        DukascopyBackend._normalize(df)


def test_normalize_lowercases_columns_and_returns_standard_schema():
    df = _df_ok_unsorted_with_dups()
    out = DukascopyBackend._normalize(df)

    assert set(out.columns) == {"time", "open", "high", "low", "close", "volume"}
    assert out["time"].dt.tz is not None
    assert out["time"].is_monotonic_increasing