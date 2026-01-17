from __future__ import annotations

import pandas as pd

from core.data_provider.provider import (
    OhlcvDataProvider,
    validate_request,
)
from core.data_provider.backend import MarketDataBackend
from core.data_provider.cache import MarketDataCache
from core.data_provider.exceptions import (
    InvalidDataRequest,
    DataNotAvailable,
)


class DefaultOhlcvDataProvider(OhlcvDataProvider):
    """
    Default OHLCV data provider for BACKTEST mode.

    Characteristics:
    - one cache file per (symbol, timeframe)
    - cache is extended ONLY on edges (no internal gap filling)
    - real market gaps (weekends, holidays) are preserved
    """

    def __init__(
        self,
        *,
        backend: MarketDataBackend,
        cache: MarketDataCache,
    ):
        self.backend = backend
        self.cache = cache

    # ---------- helpers ----------

    @staticmethod
    def _to_utc(ts: pd.Timestamp) -> pd.Timestamp:
        ts = pd.Timestamp(ts)
        if ts.tzinfo is None:
            return ts.tz_localize("UTC")
        return ts.tz_convert("UTC")

    @staticmethod
    def _validate_output(df: pd.DataFrame) -> pd.DataFrame:
        required = ["time", "open", "high", "low", "close", "volume"]
        missing = set(required) - set(df.columns)
        if missing:
            raise ValueError(f"OHLCV missing columns: {missing}")

        df = df.copy()
        df["time"] = pd.to_datetime(df["time"], utc=True)

        return (
            df.sort_values("time")
            .drop_duplicates(subset="time", keep="last")
            .reset_index(drop=True)
        )[required]

    def _fetch(
        self,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        df = self.backend.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
        )

        if df is None or df.empty:
            raise DataNotAvailable(
                f"No OHLCV fetched for {symbol} {timeframe}"
            )

        return self._validate_output(df)

    # ---------- main API ----------

    def get_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
        lookback: pd.Timedelta | None = None,
    ) -> pd.DataFrame:
        # 1️⃣ validate request
        validate_request(start=start, end=end, lookback=lookback)

        if lookback is not None:
            raise InvalidDataRequest(
                "Lookback mode is not supported in DefaultOhlcvDataProvider"
            )

        assert start is not None and end is not None

        start = self._to_utc(start)
        end = self._to_utc(end)

        # 2️⃣ load cache if exists
        if self.cache.has(symbol, timeframe):
            cached = self._validate_output(
                self.cache.load(symbol, timeframe)
            )
        else:
            cached = pd.DataFrame()

        pieces: list[pd.DataFrame] = []

        # 3️⃣ determine missing EDGES only
        if cached.empty:
            pieces.append(self._fetch(symbol, timeframe, start, end))
        else:
            cache_start = cached["time"].min()
            cache_end = cached["time"].max()

            if start < cache_start:
                pieces.append(
                    self._fetch(symbol, timeframe, start, cache_start)
                )

            if end > cache_end:
                pieces.append(
                    self._fetch(symbol, timeframe, cache_end, end)
                )

            pieces.append(cached)

        # 4️⃣ merge + persist full cache
        merged = self._validate_output(
            pd.concat(pieces, ignore_index=True)
        )

        self.cache.save(symbol, timeframe, merged)

        # 5️⃣ slice requested window
        mask = (merged["time"] >= start) & (merged["time"] <= end)
        result = merged.loc[mask].reset_index(drop=True)

        if result.empty:
            raise DataNotAvailable(
                f"No OHLCV data for {symbol} {timeframe} in requested range"
            )

        return result