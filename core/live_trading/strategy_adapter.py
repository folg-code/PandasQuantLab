from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd

from core.strategy.orchestration.informatives import apply_informatives
from core.strategy.orchestration.strategy_execution import execute_strategy
from core.strategy.plan_builder import PlanBuildContext
from core.strategy.trade_plan import TradePlan
from core.utils.timeframe import tf_to_minutes


@dataclass(frozen=True)
class StrategyCandleResult:
    df_plot: pd.DataFrame
    last_row: pd.Series
    plan: TradePlan | None


class LiveStrategyRunner:

    def __init__(self, *, strategy, provider, symbol, startup_candle_count):
        self.strategy = strategy
        self.provider = provider
        self.symbol = symbol
        self.startup_candle_count = startup_candle_count

    def run(self) -> StrategyCandleResult:
        data_by_tf = self.provider.fetch(self.symbol)

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

        ctx = PlanBuildContext(...)
        plan = self.strategy.build_trade_plan_live(last_row, ctx)

        return StrategyCandleResult(
            df_plot=df_context,
            last_row=last_row,
            plan=plan,
        )