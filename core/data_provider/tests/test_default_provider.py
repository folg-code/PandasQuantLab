import pandas as pd


from core.data_provider import CsvMarketDataCache
from core.data_provider.providers.default_provider import BacktestStrategyDataProvider
from core.logging.null_logger import NullLogger


def test_no_cache_fetches_and_saves(tmp_path, utc):

    cache = CsvMarketDataCache(tmp_path)

    start = utc("2022-01-01 00:00:00")
    end   = utc("2022-01-01 00:10:00")

    from core.data_provider.tests.conftest import FakeBackend, make_ohlcv
    df_full = make_ohlcv("2022-01-01 00:00:00", periods=11, freq="1min", dup_last=True)

    backend = FakeBackend({
        ("EURUSD", "M1", start, end): df_full,
    })

    p = BacktestStrategyDataProvider(
        backend=backend,
        cache=cache,
        backtest_start=start,
        backtest_end=end,
        logger=NullLogger(),
    )

    out = p.get_ohlcv(symbol="EURUSD", timeframe="M1", start=start, end=end)

    # assert
    assert len(backend.calls) == 1
    assert out["time"].is_monotonic_increasing
    assert out["time"].dt.tz is not None
    assert out["close"].iloc[-1] == 999


def test_missing_before_fetches_pre_and_appends(tmp_path, utc):
    cache = CsvMarketDataCache(tmp_path)

    df_cov = pd.DataFrame({
        "time": pd.date_range("2022-01-01 00:05:00", periods=6, freq="1min", tz="UTC"),
        "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1.0,
    })
    cache.save(symbol="EURUSD", timeframe="M1", df=df_cov)

    start = utc("2022-01-01 00:00:30")
    end   = utc("2022-01-01 00:10:00")

    from core.data_provider.tests.conftest import FakeBackend, make_ohlcv
    df_pre = make_ohlcv("2022-01-01 00:00:00", periods=5, freq="1min")  # 00:00..00:04

    backend = FakeBackend({
        ("EURUSD", "M1", utc("2022-01-01 00:00:00"), utc("2022-01-01 00:05:00")): df_pre
    })

    from core.data_provider.providers.default_provider import BacktestStrategyDataProvider
    p = BacktestStrategyDataProvider(
        backend=backend, cache=cache,
        backtest_start=start, backtest_end=end,
        logger=NullLogger(),
    )

    out = p.get_ohlcv(symbol="EURUSD", timeframe="M1", start=start, end=end)

    assert backend.calls == [("EURUSD","M1", utc("2022-01-01 00:00:00"), utc("2022-01-01 00:05:00"))]
    assert out["time"].min() == utc("2022-01-01 00:00:00")
    assert out["time"].max() == utc("2022-01-01 00:10:00")


def test_missing_after_fetches_post_and_appends(tmp_path, utc):
    cache = CsvMarketDataCache(tmp_path)

    # coverage: 00:00 -> 00:05
    df_cov = pd.DataFrame({
        "time": pd.date_range("2022-01-01 00:00:00", periods=6, freq="1min", tz="UTC"),
        "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1.0,
    })
    cache.save(symbol="EURUSD", timeframe="M1", df=df_cov)

    start = utc("2022-01-01 00:00:00")
    end   = utc("2022-01-01 00:10:59")  #

    from core.data_provider.tests.conftest import FakeBackend, make_ohlcv
    df_post = make_ohlcv("2022-01-01 00:05:00", periods=6, freq="1min")  # 00:05..00:10

    backend = FakeBackend({
        ("EURUSD", "M1", utc("2022-01-01 00:05:00"), utc("2022-01-01 00:10:00")): df_post
    })

    from core.data_provider.providers.default_provider import BacktestStrategyDataProvider
    p = BacktestStrategyDataProvider(
        backend=backend, cache=cache,
        backtest_start=start, backtest_end=end,
        logger=NullLogger(),
    )

    out = p.get_ohlcv(symbol="EURUSD", timeframe="M1", start=start, end=end)

    assert backend.calls == [("EURUSD","M1", utc("2022-01-01 00:05:00"), utc("2022-01-01 00:10:00"))]
    assert out["time"].max() == utc("2022-01-01 00:10:00")