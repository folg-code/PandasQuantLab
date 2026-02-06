from __future__ import annotations

import pandas as pd

from config.logger_config import RunLogger
from core.data_provider.ohlcv_schema import sort_and_deduplicate, ensure_utc_time
from core.utils.timeframe import timeframe_to_pandas_freq


class DefaultOhlcvDataProvider:
    """
    BACKTEST OHLCV provider.

    Responsibilities:
    - decide if data is missing (TIME-BASED)
    - fetch ONLY missing ranges
    - write to cache ONLY when something was fetched
    """

    def __init__(
        self,
        *,
        backend,
        cache,
        backtest_start: pd.Timestamp,
        backtest_end: pd.Timestamp,
        logger
    ):
        self.backend = backend
        self.cache = cache
        self.backtest_start = self._to_utc(backtest_start)
        self.backtest_end = self._to_utc(backtest_end)
        self.logger = logger

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    @staticmethod
    def _to_utc(ts: pd.Timestamp) -> pd.Timestamp:
        ts = pd.Timestamp(ts)
        return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")

    @staticmethod
    def _validate(df: pd.DataFrame) -> pd.DataFrame:
        BASE_ORDER = ["time", "open", "high", "low", "close", "volume"]

        missing = set(BASE_ORDER) - set(df.columns)
        if missing:
            raise ValueError(f"OHLCV missing columns: {missing}")


        df = ensure_utc_time(df)

        df = sort_and_deduplicate(df=df, keep="last")

        base = [c for c in BASE_ORDER if c in df.columns]
        rest = [c for c in df.columns if c not in base]
        return df[base + rest]

    @staticmethod
    def shift_time_by_candles(
            *,
            end: pd.Timestamp,
            timeframe: str,
            candles: int,
    ) -> pd.Timestamp:
        freq = timeframe_to_pandas_freq(timeframe)
        return end - pd.tseries.frequencies.to_offset(freq) * candles

    # -------------------------------------------------
    # Main API
    # -------------------------------------------------

    def get_ohlcv(
            self,
            *,
            symbol: str,
            timeframe: str,
            start: pd.Timestamp,
            end: pd.Timestamp,
    ) -> pd.DataFrame:

        start = self._to_utc(start)
        end = self._to_utc(end)

        with self.logger.section(f"{symbol} {timeframe}"):

            coverage = self.cache.coverage(
                symbol=symbol,
                timeframe=timeframe,
            )

            pieces: list[pd.DataFrame] = []

            # =================================================
            # 1️⃣ NO CACHE
            # =================================================
            if coverage is None:
                self.logger.log("cache MISS → fetch full range")

                df = self.backend.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    start=start,
                    end=end,
                )
                df = self._validate(df)

                self.cache.save(symbol=symbol, timeframe=timeframe, df=df)
                self.logger.log(f"fetched {len(df)} bars")

                return df

            cov_start, cov_end = coverage
            self.logger.log(f"cache coverage {cov_start} → {cov_end}")

            freq = timeframe_to_pandas_freq(timeframe)
            first_required_bar = start.floor(freq)
            last_required_bar = end.floor(freq)

            # =================================================
            # 2️⃣ BEFORE
            # =================================================
            if first_required_bar < cov_start:
                self.logger.log("cache MISS before")

                df_pre = self.backend.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    start=first_required_bar,
                    end=cov_start,
                )
                df_pre = self._validate(df_pre)

                if not df_pre.empty:
                    self.cache.append(symbol=symbol, timeframe=timeframe, df=df_pre)
                    pieces.append(df_pre)
                    self.logger.log(f"fetched {len(df_pre)} bars (pre)")
            else:
                self.logger.log("cache HIT before")

            # =================================================
            # 3️⃣ MIDDLE
            # =================================================
            df_mid = self.cache.load_range(
                symbol=symbol,
                timeframe=timeframe,
                start=max(start, cov_start),
                end=min(end, cov_end),
            )
            pieces.append(df_mid)
            self.logger.log(f"cache HIT middle ({len(df_mid)} bars)")

            # =================================================
            # 4️⃣ AFTER
            # =================================================
            if last_required_bar > cov_end:
                self.logger.log("cache MISS after")

                df_post = self.backend.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    start=cov_end,
                    end=last_required_bar,
                )
                df_post = self._validate(df_post)

                if not df_post.empty:
                    self.cache.append(symbol=symbol, timeframe=timeframe, df=df_post)
                    pieces.append(df_post)
                    self.logger.log(f"fetched {len(df_post)} bars (post)")
            else:
                self.logger.log("cache HIT after")

            # =================================================
            # 5️⃣ MERGE
            # =================================================
            df = pd.concat(pieces, ignore_index=True)
            self.logger.log(f"final {len(df)} bars")

            return self._validate(df)

    # -------------------------------------------------
    # Informative data
    # -------------------------------------------------

    def get_informative_df(
            self,
            *,
            symbol: str,
            timeframe: str,
            startup_candle_count: int,
    ) -> pd.DataFrame:
        """
        Informative data for BACKTEST.

        Fetches EXTENDED range:
        [backtest_start - startup_candle_count * timeframe, backtest_end]

        No trimming here. Trimming happens AFTER merge.
        """

        extended_start = self.shift_time_by_candles(
            end=self.backtest_start,
            timeframe=timeframe,
            candles=startup_candle_count,
        )

        df = self.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            start=extended_start,
            end=self.backtest_end,
        )

        return df.copy()
