from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import pandas as pd

from core.backtesting.reporting.config.report_config import ReportConfig
from core.backtesting.reporting.core.metrics import ExpectancyMetric, MaxDrawdownMetric
from core.strategy.trade_plan import TradePlan, TradeAction


class BaseStrategy(ABC):
    """
    Strategy domain contract.

    Strategy responsibilities:
    - observe market state
    - decide WHEN and WHY to trade
    - produce decisions (TradePlan / TradeAction)

    Strategy does NOT:
    - fetch or merge data
    - manage lifecycle
    - know about backtest or live execution
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
    # Strategy hooks
    # ==================================================

    @abstractmethod
    def populate_indicators(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def populate_entry_trend(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def populate_exit_trend(self) -> None:
        raise NotImplementedError

    # ==================================================
    # Decision layer
    # ==================================================

    def build_trade_plan(self, *, row: pd.Series) -> Optional[TradePlan]:
        return None

    def manage_trade(
        self,
        *,
        trade_state: Dict[str, Any],
        market_state: Dict[str, Any],
    ) -> Optional[TradeAction]:
        return None

    # ==================================================
    # Optional hooks (called by orchestrators)
    # ==================================================

    def validate(self):
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