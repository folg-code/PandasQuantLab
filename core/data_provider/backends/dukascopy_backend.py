from __future__ import annotations

import pandas as pd

from core.data_provider import MarketDataBackend, DataNotAvailable
from core.data_provider.ohlcv_schema import finalize_ohlcv


class DukascopyBackend(MarketDataBackend):
    """
    Dukascopy OHLCV backend.

    Responsibilities:
    - fetch raw OHLCV data from Dukascopy
    - return clean, UTC-based DataFrame
    - NO cache
    - NO live/backtest logic
    """

    def __init__(self, client):
        """
        Parameters
        ----------
        client :
            Low-level Dukascopy client / adapter responsible
            for actual HTTP / binary downloads.
        """
        self.client = client

    def fetch_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        if start >= end:
            raise ValueError("start must be earlier than end")

        start = start.tz_convert("UTC") if start.tzinfo else start.tz_localize("UTC")
        end = end.tz_convert("UTC") if end.tzinfo else end.tz_localize("UTC")

        try:
            df = self.client.get_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
            )
        except Exception as exc:
            raise DataNotAvailable(
                f"Failed to fetch Dukascopy data for {symbol} {timeframe}"
            ) from exc

        if df is None or df.empty:
            raise DataNotAvailable(
                f"No Dukascopy data for {symbol} {timeframe}"
            )

        return finalize_ohlcv(df=df)