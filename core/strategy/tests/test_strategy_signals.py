import pandas as pd
import pytest

from core.strategy.orchestration.informatives import apply_informatives
from Strategies.Samplestrategyreport import Samplestrategyreport
from core.strategy.exception import StrategyValidationError
from core.strategy.tests.helper import DummyProvider, DummyStrategy


def make_df(n=100):
    return pd.DataFrame({
        "time": pd.date_range("2024-01-01", periods=n, freq="1min", tz="UTC"),
        "open": 100.0,
        "high": 101.0,
        "low": 99.0,
        "close": 100.0,
        "volume": 1.0,
    })


def test_strategy_does_not_generate_entries_when_conditions_not_met():
    df = make_df()

    strategy = Samplestrategyreport(
        df=df.copy(),
        symbol="XAUUSD",
        startup_candle_count=10,
    )

    df_with_htf = apply_informatives(
        df=df,
        strategy=strategy,
        provider=DummyProvider(),
        symbol="XAUUSD",
        startup_candle_count=10,
    )

    strategy.df = df_with_htf

    strategy.populate_indicators()
    strategy.populate_entry_trend()

    entries = strategy.df["signal_entry"].dropna()

    assert len(entries) == 0


def test_base_strategy_validate_requires_time_column():
    df = pd.DataFrame({"close": [1, 2, 3]})

    strat = DummyStrategy(
        df=df,
        symbol="XAUUSD",
        startup_candle_count=1,
    )

    with pytest.raises(Exception):
        strat.validate()


def test_strategy_validation_error_exists():
    assert issubclass(StrategyValidationError, Exception)