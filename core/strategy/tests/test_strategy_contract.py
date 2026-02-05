import pandas as pd

from core.strategy.orchestration.informatives import apply_informatives
from Strategies.Samplestrategyreport import Samplestrategyreport
from core.strategy.tests.helper import DummyProvider


def make_df(n=100):
    return pd.DataFrame({
        "time": pd.date_range("2024-01-01", periods=n, freq="1min", tz="UTC"),
        "open": 100.0,
        "high": 101.0,
        "low": 99.0,
        "close": 100.0,
        "volume": 1.0,
    })

def test_strategy_domain_execution_with_informatives():
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

    strategy.validate()
    strategy.populate_indicators()
    strategy.populate_entry_trend()
    strategy.populate_exit_trend()

    assert "signal_entry" in strategy.df.columns
    assert "signal_exit" in strategy.df.columns
