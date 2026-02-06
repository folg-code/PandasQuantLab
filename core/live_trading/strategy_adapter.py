from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd

from core.strategy.orchestration.strategy_execution import execute_strategy
from core.strategy.plan_builder import PlanBuildContext
from core.strategy.trade_plan import TradePlan


@dataclass(frozen=True)
class StrategyCandleResult:
    df_plot: pd.DataFrame
    last_row: pd.Series
    plan: TradePlan | None


class LiveStrategyAdapter:
    """
    Live orchestration adapter.

    Responsibilities:
    - execute vector strategy update on df_execution
    - produce entry plan from last row using BaseStrategy default builder
    """

    def __init__(
        self,
        *,
        strategy,
        symbol: str,
        startup_candle_count: int,
        df_execution: pd.DataFrame,
    ):
        self.strategy = strategy
        self.symbol = symbol
        self.startup_candle_count = startup_candle_count
        self.df_execution = df_execution

        self._last_df_plot: Optional[pd.DataFrame] = None

    def on_new_candle(self) -> StrategyCandleResult:
        df_plot = execute_strategy(
            strategy=self.strategy,
            df=self.df_execution,
            symbol=self.symbol,
            startup_candle_count=self.startup_candle_count,
        )

        if df_plot is None or df_plot.empty:
            # hard guard: strategy must return df
            raise RuntimeError("execute_strategy returned empty df")

        last_row = df_plot.iloc[-1]

        ctx = PlanBuildContext(
            symbol=self.symbol,
            strategy_name=type(self.strategy).__name__,
            strategy_config=getattr(self.strategy, "strategy_config", {}) or {},
        )

        # Expect BaseStrategy provides this default method.
        build_fn = getattr(self.strategy, "build_trade_plan_live", None)
        plan = build_fn(row=last_row, ctx=ctx) if callable(build_fn) else None

        self._last_df_plot = df_plot
        return StrategyCandleResult(df_plot=df_plot, last_row=last_row, plan=plan)

    def last_df_plot(self) -> Optional[pd.DataFrame]:
        return self._last_df_plot