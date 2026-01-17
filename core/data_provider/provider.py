from typing import Protocol
import pandas as pd

class OhlcvDataProvider(Protocol):
    def get_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
        lookback: pd.Timedelta | None = None,
    ) -> pd.DataFrame:
        """
        BACKTEST: start + end
        LIVE: lookback
        Exactly one mode must be used.
        """