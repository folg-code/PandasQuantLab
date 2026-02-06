import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

from core.live_trading.market_state import MarketStateProvider
from core.utils.timeframe import MT5_TIMEFRAME_MAP


class MT5MarketStateProvider(MarketStateProvider):
    """
    Polls MT5 for last closed candle.
    """

    def __init__(self, *, symbol: str, timeframe: str):
        self.symbol = symbol
        self.timeframe = timeframe
        self._last_candle_time = None

    def poll(self):
        tf = MT5_TIMEFRAME_MAP[self.timeframe]
        rates = mt5.copy_rates_from_pos(self.symbol, tf, 0, 2)

        if rates is None or len(rates) < 2:
            return None

        last_closed = rates[-2]
        candle_time = pd.to_datetime(
            last_closed["time"], unit="s", utc=True
        )

        is_new_candle = candle_time != self._last_candle_time
        self._last_candle_time = candle_time

        return {
            "price": float(last_closed["close"]),
            "time": candle_time,
            "candle_time": candle_time if is_new_candle else None,
        }