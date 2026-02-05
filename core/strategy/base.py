from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import pandas as pd

from core.backtesting.reporting.config.report_config import ReportConfig
from core.backtesting.reporting.core.metrics import ExpectancyMetric, MaxDrawdownMetric
from core.strategy.plan_builder import PlanBuildContext, build_trade_plan_from_row, build_plans_frame
from core.strategy.trade_plan import TradePlan, TradeAction



class BaseStrategy(ABC):
    """
    Vector strategy contract.

    Responsibilities:
    - populate features/indicators on self.df (vectorized)
    - produce signals in df (e.g. signal_entry / signal_exit / levels)
    - optionally: map last-row decisions into TradePlan (live) or plan frame (backtest)

    Strategy does NOT:
    - fetch/merge data (provider does)
    - manage lifecycle/execution (runner/engine does)
    """

    def __init__(
        self,
        *,
        df: pd.DataFrame,
        symbol: str,
        strategy_config: Optional[Dict[str, Any]] = None,
        startup_candle_count: int = 0,
    ):
        self.df = df
        self.symbol = symbol
        self.strategy_config = strategy_config or {}
        self.startup_candle_count = startup_candle_count

    # ==================================================
    # Informatives (DECLARATION ONLY)
    # ==================================================

    @classmethod
    def get_required_informatives(cls) -> List[str]:
        tfs = set()
        for attr in dir(cls):
            fn = getattr(cls, attr)
            if callable(fn) and getattr(fn, "_informative", False):
                tfs.add(fn._informative_timeframe)
        return sorted(tfs)

    # ==================================================
    # Strategy hooks (vector)
    # ==================================================

    @abstractmethod
    def populate_indicators(self) -> None:
        """Compute indicators/features into self.df."""
        raise NotImplementedError

    @abstractmethod
    def populate_entry_trend(self) -> None:
        """Write entry signals into self.df (e.g. signal_entry / levels)."""
        raise NotImplementedError

    @abstractmethod
    def populate_exit_trend(self) -> None:
        """Write exit/management signals into self.df (e.g. signal_exit / custom_stop_loss)."""
        raise NotImplementedError

    # ==================================================
    # Decision layer (OPTIONAL by default)
    # ==================================================

    def build_trade_plan_live(self, *, row: pd.Series, ctx: PlanBuildContext) -> TradePlan | None:
        """
        Default live plan builder from last row.
        Strategies do NOT need to override this.
        """
        return build_trade_plan_from_row(row=row, ctx=ctx)

    def build_trade_plans_backtest(
        self,
        *,
        df: pd.DataFrame,
        ctx: PlanBuildContext,
        allow_managed_in_backtest: bool = False,
    ) -> pd.DataFrame:
        """
        Default backtest plan builder from full DF.
        Strategies do NOT need to override this.
        """
        return build_plans_frame(df=df, ctx=ctx, allow_managed_in_backtest=allow_managed_in_backtest)

    def build_trade_plans(self, *, df: pd.DataFrame) -> pd.DataFrame:
        """
        Backtest hook (vector-friendly).
        Default: empty -> runner/backtester may use shared plan_builder fallback.
        """
        return pd.DataFrame(index=df.index)

    def manage_trade(
        self,
        *,
        trade_state: Dict[str, Any],
        market_state: Dict[str, Any],
    ) -> Optional[TradeAction]:
        """
        Optional live management hook for active trades.
        Default: no-op.
        """
        return None

    # ==================================================
    # Optional hooks (called by orchestrators)
    # ==================================================

    def validate(self) -> None:
        if "time" not in self.df.columns:
            raise ValueError("Strategy DF must contain 'time' column")

    def build_report_config(self):
        return (
            ReportConfig()
            .add_metric(ExpectancyMetric())
            .add_metric(MaxDrawdownMetric())
        )

    def get_bullish_zones(self):
        return []

    def get_bearish_zones(self):
        return []

    def get_extra_values_to_plot(self):
        return []

    def bool_series(self):
        return []


# ==================================================
# Optional stricter base for live trading
# ==================================================

class BasePlanStrategy(BaseStrategy, ABC):
    """
    Use this base if the strategy MUST provide TradePlan (e.g. live trading).
    """

    @abstractmethod
    def build_trade_plan(self, *, row: pd.Series) -> TradePlan | None:
        ...
