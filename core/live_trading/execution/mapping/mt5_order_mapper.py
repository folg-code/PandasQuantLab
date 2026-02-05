from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.live_trading.execution.policy.exit_execution import ExitExecution
from core.strategy.trade_plan import TradePlan, FixedExitPlan

@dataclass(frozen=True)
class Mt5OrderParams:
    symbol: str
    direction: str
    volume: float
    price: float
    sl: float
    tp: Optional[float]


def trade_plan_to_mt5_order(
    *,
    plan: TradePlan,
    volume: float,
    execution: ExitExecution,
) -> Mt5OrderParams:
    tp: Optional[float] = None

    if isinstance(plan.exit_plan, FixedExitPlan) and execution.tp2 == "BROKER":
        tp = plan.exit_plan.tp2

    return Mt5OrderParams(
        symbol=plan.symbol,
        direction=plan.direction,
        volume=float(volume),
        price=float(plan.entry_price),
        sl=float(plan.exit_plan.sl),
        tp=None if tp is None else float(tp),
    )