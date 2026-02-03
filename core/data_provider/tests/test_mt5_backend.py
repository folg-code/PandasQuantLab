import pandas as pd
import pytest

from core.data_provider.backends.mt5 import Mt5Backend
from core.data_provider.exceptions import DataNotAvailable

def test_mt5_backend_unsupported_timeframe(monkeypatch):
    monkeypatch.setattr("core.data_provider.backends.mt5.mt5.initialize", lambda: True)
    b = Mt5Backend()

    with pytest.raises(ValueError):
        b.fetch_ohlcv(symbol="EURUSD", timeframe="NOPE", start=pd.Timestamp("2022-01-01"), end=pd.Timestamp("2022-01-02"))

def test_mt5_backend_no_data(monkeypatch):
    monkeypatch.setattr("core.data_provider.backends.mt5.mt5.initialize", lambda: True)
    monkeypatch.setattr("core.data_provider.backends.mt5.mt5.copy_rates_range", lambda *a, **k: [])
    b = Mt5Backend()

    with pytest.raises(DataNotAvailable):
        b.fetch_ohlcv(
            symbol="EURUSD", timeframe="M1",
            start=pd.Timestamp("2022-01-01", tz="UTC"),
            end=pd.Timestamp("2022-01-01 00:10:00", tz="UTC"),
        )

def test_mt5_backend_normalize(monkeypatch):
    monkeypatch.setattr("core.data_provider.backends.mt5.mt5.initialize", lambda: True)

    def fake_copy_rates_range(symbol, tf, start_dt, end_dt):
        return [
            {"time": 1640995200, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "tick_volume": 100},
            {"time": 1640995260, "open": 2, "high": 3, "low": 1.5, "close": 2.5, "tick_volume": 200},
        ]

    monkeypatch.setattr("core.data_provider.backends.mt5.mt5.copy_rates_range", fake_copy_rates_range)

    b = Mt5Backend()
    out = b.fetch_ohlcv(
        symbol="EURUSD", timeframe="M1",
        start=pd.Timestamp("2022-01-01", tz="UTC"),
        end=pd.Timestamp("2022-01-01 00:02:00", tz="UTC"),
    )

    assert list(out.columns) == ["time", "open", "high", "low", "close", "volume"]
    assert out["time"].dt.tz is not None
    assert out["volume"].tolist() == [100, 200]