import pandas as pd
from datetime import datetime
from typing import Optional

from core.data_provider.exceptions import DataNotAvailable


class DukascopyClient:
    """
    Low-level Dukascopy OHLCV client.

    Responsibilities:
    - talk to Dukascopy data source (HTTP / binary)
    - return raw OHLCV as pandas DataFrame
    - NO cache
    - NO timeframe logic
    - NO live/backtest logic
    """

    def __init__(self):
        # tutaj w przyszłości:
        # - base_url
        # - auth
        # - rate limiting
        pass

    def get_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from Dukascopy.

        Parameters
        ----------
        symbol : str
        timeframe : str  (e.g. M1, M5, M15, H1)
        start : UTC Timestamp
        end   : UTC Timestamp

        Returns
        -------
        pd.DataFrame with columns:
        time, open, high, low, close, volume
        """

        start = self._ensure_utc(start)
        end = self._ensure_utc(end)

        if start >= end:
            raise ValueError("start must be earlier than end")

        # 🔴 TU NORMALNIE BYŁOBY PRAWDZIWE POBIERANIE
        # Na razie: symulacja / placeholder logiczny

        df = self._download_stub(
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
        )

        if df is None or df.empty:
            raise DataNotAvailable(
                f"No Dukascopy data for {symbol} {timeframe}"
            )

        return df

    # ==================================================
    # Helpers
    # ==================================================

    @staticmethod
    def _ensure_utc(ts: pd.Timestamp) -> pd.Timestamp:
        ts = pd.Timestamp(ts)
        if ts.tzinfo is None:
            return ts.tz_localize("UTC")
        return ts.tz_convert("UTC")

    # ==================================================
    # STUB (do zastąpienia realnym downloaderem)
    # ==================================================

    def _download_stub(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        """
        Temporary stub.
        Replace with real Dukascopy downloader.
        """

        # ⚠️ TYLKO DO TESTÓW
        # Realna implementacja:
        # - iteracja po miesiącach
        # - binarki Dukascopy
        # - resampling do OHLCV

        times = pd.date_range(
            start=start,
            end=end,
            freq=self._pandas_freq(timeframe),
            inclusive="left",
            tz="UTC",
        )

        if times.empty:
            return pd.DataFrame()

        df = pd.DataFrame(
            {
                "time": times,
                "open": 1.0,
                "high": 1.0,
                "low": 1.0,
                "close": 1.0,
                "volume": 1.0,
            }
        )

        return df

    @staticmethod
    def _pandas_freq(timeframe: str) -> str:
        """
        Convert Dukascopy timeframe to pandas frequency.
        """
        mapping = {
            "M1": "1min",
            "M5": "5min",
            "M15": "15min",
            "M30": "30min",
            "H1": "1h",
            "H4": "4h",
            "D1": "1D",
        }

        try:
            return mapping[timeframe]
        except KeyError:
            raise ValueError(f"Unsupported timeframe: {timeframe}")