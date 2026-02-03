from __future__ import annotations

from pathlib import Path
import pandas as pd

from core.data_provider.cache.cache_key import build_cache_key
from core.data_provider.ohlcv_schema import ensure_utc_time


class CsvMarketDataCache:
    """
    CSV-based OHLCV cache.
    One file per (symbol, timeframe).

    Cache is PASSIVE:
    - does NOT decide whether data is missing
    - writes ONLY when provider explicitly asks
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)




    # -------------------------------------------------
    # Coverage
    # -------------------------------------------------

    def coverage(self, *, symbol: str, timeframe: str):
        path = build_cache_key(self.root,symbol,timeframe)
        if not path.exists():
            return None

        df = pd.read_csv(path)
        if df.empty:
            return None

        t = pd.to_datetime(df["time"], utc=True)

        cov_start = t.min()
        cov_end = t.max()

        return cov_start, cov_end

    # -------------------------------------------------
    # Load
    # -------------------------------------------------

    def load_range(
            self,
            *,
            symbol: str,
            timeframe: str,
            start: pd.Timestamp,
            end: pd.Timestamp,
    ) -> pd.DataFrame:
        path = build_cache_key(self.root, symbol, timeframe)
        if not path.exists():
            raise FileNotFoundError(path)

        # normalize range to UTC
        start = pd.Timestamp(start)
        end = pd.Timestamp(end)
        start = start.tz_localize("UTC") if start.tzinfo is None else start.tz_convert("UTC")
        end = end.tz_localize("UTC") if end.tzinfo is None else end.tz_convert("UTC")

        df = pd.read_csv(path)
        df = ensure_utc_time(df)

        mask = (df["time"] >= start) & (df["time"] <= end)

        return (
            df.loc[mask]
            .sort_values("time")
            .reset_index(drop=True)
        )

    # -------------------------------------------------
    # Save / append
    # -------------------------------------------------

    def save(
        self,
        *,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame,
    ) -> None:
        if df.empty:
            return

        path = build_cache_key(self.root,symbol,timeframe)
        (
            df.sort_values("time")
              .reset_index(drop=True)
              .to_csv(path, index=False)
        )

    def append(
            self,
            *,
            symbol: str,
            timeframe: str,
            df: pd.DataFrame,
    ) -> None:
        if df.empty:
            return

        path = build_cache_key(self.root,symbol,timeframe)

        if not path.exists():
            self.save(symbol=symbol, timeframe=timeframe, df=df)
            return

        existing = pd.read_csv(path)

        before = len(existing)

        combined = pd.concat([existing, df], ignore_index=True)
        combined["time"] = pd.to_datetime(combined["time"], utc=True)
        combined = (
            combined.sort_values("time")
            .drop_duplicates(subset="time", keep="last")
            .reset_index(drop=True)
        )

        if len(combined) == before:
            return

        combined.to_csv(path, index=False)
