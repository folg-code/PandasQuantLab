import pandas as pd

from core.market_data.cache import MarketDataCache
from core.market_data.interfaces import MarketDataBackend
from core.market_data.errors import DataNotAvailable


class DefaultMarketDataProvider:
    """
    Unified OHLCV provider.
    Orchestrates cache + backend.
    """

    def __init__(
        self,
        *,
        backend: MarketDataBackend,
        cache: MarketDataCache,
    ):
        self.backend = backend
        self.cache = cache

    def get_ohlcv(self, *, symbol, timeframe, start, end) -> pd.DataFrame:
        source = self.backend.capabilities.source

        coverage = self.cache.coverage(
            source=source,
            symbol=symbol,
            timeframe=timeframe,
        )

        pieces: list[pd.DataFrame] = []

        if coverage is None:
            df = self.backend.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
            )
            if df.empty:
                raise DataNotAvailable(symbol)

            self.cache.save(
                source=source,
                symbol=symbol,
                timeframe=timeframe,
                df=df,
            )
            return df

        cov_start, cov_end = coverage

        # before
        if start < cov_start:
            df_pre = self.backend.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=cov_start,
            )
            self.cache.append(
                source=source,
                symbol=symbol,
                timeframe=timeframe,
                df=df_pre,
            )
            pieces.append(df_pre)

        # middle
        df_mid = self.cache.load_range(
            source=source,
            symbol=symbol,
            timeframe=timeframe,
            start=max(start, cov_start),
            end=min(end, cov_end),
        )
        pieces.append(df_mid)

        # after
        if end > cov_end:
            df_post = self.backend.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start=cov_end,
                end=end,
            )
            self.cache.append(
                source=source,
                symbol=symbol,
                timeframe=timeframe,
                df=df_post,
            )
            pieces.append(df_post)

        return (
            pd.concat(pieces, ignore_index=True)
            .sort_values("time")
            .drop_duplicates(subset="time", keep="last")
            .reset_index(drop=True)
        )