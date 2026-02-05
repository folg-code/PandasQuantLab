from __future__ import annotations

from core.domain.cost.execution_cost import attach_execution_costs
from core.domain.cost.financing import attach_financing_costs
from core.domain.cost.instrument_ctx import InstrumentCtx
from core.domain.cost.pricing import attach_net_pnl
from core.domain.cost.traded_volume import attach_traded_volume
from core.domain.execution.execution_types import attach_execution_types


class TradeCostEngine:
    """
    Single responsibility:
      - enrich trade_dict with execution types, traded volume, spread/slippage costs,
        financing (overnight/weekend), and pnl_net_usd.

    It does NOT change entry/exit prices. It's an accounting overlay.
    """

    def __init__(self, execution_policy):
        self.execution_policy = execution_policy


    def apply(self, trade_dict: dict, *, df, ctx: InstrumentCtx) -> None:
        attach_execution_types(
            trade_dict,
            df=df,
            execution_policy=self.execution_policy,
        )
        attach_traded_volume(trade_dict, ctx)
        attach_execution_costs(trade_dict, ctx)
        attach_financing_costs(trade_dict, ctx)
        attach_net_pnl(trade_dict)




