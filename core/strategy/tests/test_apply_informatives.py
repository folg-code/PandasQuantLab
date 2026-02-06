import pandas as pd

from core.strategy.orchestration.informatives import apply_informatives
from Strategies.Samplestrategyreport import Samplestrategyreport
from core.strategy.tests.helper import TestStrategy, DummyProvider


def test_apply_informatives_merges_htf():
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

    out = apply_informatives(
        df=df,
        strategy=strat,
        data_by_tf={"M30":df},
    )

    assert any(c.endswith("_M30") for c in out.columns)


def test_informative_decorator_registers_timeframe():
    tfs = TestStrategy.get_required_informatives()
    assert tfs == ["M30"]
