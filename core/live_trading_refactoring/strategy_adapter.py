# core/live_trading/strategy_adapter.py

import pandas as pd
from typing import Optional

from core.strategy.BaseStrategy import BaseStrategy, TradePlan


class LiveStrategyAdapter:
    """
    Adapts BaseStrategy to live on-close signal provider.
    """

    def __init__(
        self,
        *,
        strategy: BaseStrategy,
        volume: float,
    ):
        self.strategy = strategy
        self.volume = volume

        self._last_bar_time: pd.Timestamp | None = None

    # ==================================================
    # Public API (used by LiveEngine)
    # ==================================================

    def get_trade_plan(self) -> Optional[TradePlan]:
        """
        Called by live engine.
        Returns TradePlan only once per closed candle.
        """

        # 1️⃣ Pobierz DF BEZ uruchamiania strategii
        df = self.strategy.df
        if df.empty:
            return None

        last_time = df.iloc[-1]["time"]

        # debounce BEFORE run()
        if self._last_bar_time == last_time:
            return None

        # 2️⃣ Dopiero teraz odpal strategię
        df = self.strategy.run()
        if df.empty:
            return None

        last_row = df.iloc[-1]
        bar_time = last_row["time"]

        self._last_bar_time = bar_time

        # 3️⃣ TradePlan
        plan = self.strategy.build_trade_plan(row=last_row)
        if plan is None:
            return None

        return plan