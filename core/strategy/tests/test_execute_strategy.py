import pandas as pd
from core.strategy.orchestration.strategy_execution import execute_strategy
from Strategies.Samplestrategyreport import Samplestrategyreport
from core.strategy.tests.helper import DummyProvider


def test_execute_strategy_pipeline():
    df = pd.DataFrame({
        "time": pd.date_range(
            "2024-01-01", periods=100, freq="1min", tz="UTC"
        ),
        "open": 100.0,
        "high": 101.0,
        "low": 99.0,
        "close": 100.0,
        "volume": 1.0,
    })

    strat = Samplestrategyreport(
        df=df.copy(),
        symbol="XAUUSD",
        startup_candle_count=10,
    )

    out = execute_strategy(
        strategy=strat,
        df=df,
        data_by_tf={"M30": df},

    )

    assert "signal_entry" in out.columns
