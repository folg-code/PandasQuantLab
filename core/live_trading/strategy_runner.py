from __future__ import annotations

from typing import  Optional

import pandas as pd

from core.strategy.orchestration.informatives import apply_informatives
from core.strategy.plan_builder import PlanBuildContext
from core.utils.timeframe import tf_to_minutes




class StrategyCandleResult:
    def __init__(self, *, last_row: pd.Series, plan):
        self.last_row = last_row
        self.plan = plan


class LiveStrategyRunner:
    """
    Runs strategy on each new candle.
    """

    def __init__(
        self,
        *,
        strategy,
        data_provider,
        symbol: str,
    ):
        self.strategy = strategy
        self.data_provider = data_provider
        self.symbol = symbol
        self._last_df: Optional[pd.DataFrame] = None

    def run(self) -> StrategyCandleResult:
        data_by_tf = self.data_provider.fetch(self.symbol)

        base_tf = min(data_by_tf.keys(), key=tf_to_minutes)
        df_base = data_by_tf[base_tf]

        df_context = apply_informatives(
            df=df_base,
            strategy=self.strategy,
            data_by_tf=data_by_tf,
        )

        self.strategy.df = df_context
        self.strategy.populate_indicators()
        self.strategy.populate_entry_trend()
        self.strategy.populate_exit_trend()

        last_row = df_context.iloc[-1]

        ctx = PlanBuildContext(
            symbol=self.symbol,
            strategy_name=self.strategy.get_strategy_name(),
            strategy_config=self.strategy.strategy_config,
        )

        plan = self.strategy.build_trade_plan_live(
            row=last_row,
            ctx=ctx,
        )

        self._last_df = df_context

        return StrategyCandleResult(
            last_row=last_row,
            plan=plan,
        )