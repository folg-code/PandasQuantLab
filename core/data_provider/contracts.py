from abc import ABC, abstractmethod
from typing import Protocol

import pandas as pd


class MarketDataBackend(Protocol):
    def fetch_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        ...


class MarketDataProvider(ABC):

    @abstractmethod
    def get_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        bars: int,
    ) -> pd.DataFrame:
        pass


class CsvMarketDataCache(Protocol):
    def coverage(self, *, symbol: str, timeframe: str): ...
    def load_range(self, *, symbol: str, timeframe: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame: ...
    def save(self, *, symbol: str, timeframe: str, df: pd.DataFrame) -> None: ...
    def append(self, *, symbol: str, timeframe: str, df: pd.DataFrame) -> None: ...


class OhlcvProvider(Protocol):
    def get_ohlcv(self, *, symbol: str, timeframe: str, start: pd.Timestamp, end: pd.Timestamp,) -> pd.DataFrame: ...