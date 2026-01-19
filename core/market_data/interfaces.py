# core/market_data/interfaces.py

from abc import ABC, abstractmethod
import pandas as pd
from pandas import Timestamp

from core.market_data.features import MarketDataCapabilities
from core.market_data.errors import MarketDataError


class MarketDataBackend(ABC):
    """
    Raw market data source.

    Responsibilities:
    - fetch raw OHLCV for a given time range
    - declare its capabilities explicitly
    """

    def __init__(self, *, capabilities: MarketDataCapabilities):
        self.capabilities = capabilities

    @abstractmethod
    def fetch_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: Timestamp,
        end: Timestamp,
    ) -> pd.DataFrame:
        """
        Must return a DataFrame with at least:
        - time (UTC)
        - open, high, low, close

        Volume / spread columns are optional and declared via capabilities.
        """
        raise MarketDataError(
            "fetch_ohlcv must be implemented by MarketDataBackend subclass"
        )


class MarketDataProvider(ABC):
    """
    High-level OHLCV access used by strategies and engines.
    """

    @abstractmethod
    def get_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: Timestamp,
        end: Timestamp,
    ) -> pd.DataFrame:
        """
        Returns normalized OHLCV DataFrame.
        """
        raise MarketDataError(
            "get_ohlcv must be implemented by MarketDataProvider subclass"
        )