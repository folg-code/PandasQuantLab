from datetime import datetime

from core.domain.cost.cost_engine import TradeCostEngine, InstrumentCtx
from core.backtesting.execution_policy import ExecutionPolicy


def test_trade_cost_engine_does_not_mutate_prices():
    engine = TradeCostEngine(ExecutionPolicy())

    trade = {
        "entry_time": datetime(2023, 1, 1, 10, 0),
        "exit_time": datetime(2023, 1, 1, 12, 0),
        "entry_price": 1.0000,
        "exit_price": 1.0100,
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

    assert trade["entry_price"] == 1.0000
    assert trade["exit_price"] == 1.0100
    assert "pnl_net_usd" in trade