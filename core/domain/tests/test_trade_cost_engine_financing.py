from datetime import datetime, timedelta

from core.domain.trade_cost_engine import TradeCostEngine, InstrumentCtx
from core.backtesting.execution_policy import ExecutionPolicy


def test_financing_is_zero_when_disabled(monkeypatch):
    monkeypatch.setattr(
        "core.domain.trade_cost_engine.FINANCING_ENABLED",
        False
    )

    engine = TradeCostEngine(ExecutionPolicy())

    trade = {
        "entry_time": datetime(2023, 1, 1, 10),
        "exit_time": datetime(2023, 1, 1, 20),
        "entry_price": 1.0,
        "exit_price": 1.01,
        "position_size": 1.0,
        "direction": "long",
        "tp1_time": None,
        "pnl_usd": 1000.0,
    }

    ctx = InstrumentCtx(
        symbol="EURUSD",
        point_size=0.0001,
        pip_value=10.0,
        contract_size=1.0,
        spread_abs=0.0002,
        half_spread=0.0001,
        slippage_abs=0.0,
    )

    engine.enrich(trade, df=None, ctx=ctx)

    assert trade["financing_usd_total"] == 0.0