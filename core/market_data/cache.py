from pathlib import Path
import pandas as pd


class MarketDataCache:
    """
    Range-aware OHLCV cache.
    Cache key = (source, symbol, timeframe)
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------
    # Paths
    # -------------------------------------------------

    def _path(self, *, source: str, symbol: str, timeframe: str) -> Path:
        return self.root / source / f"{symbol}_{timeframe}.csv"

    # -------------------------------------------------
    # Coverage
    # -------------------------------------------------

    def coverage(self, *, source: str, symbol: str, timeframe: str):
        path = self._path(source=source, symbol=symbol, timeframe=timeframe)
        if not path.exists():
            return None

        df = pd.read_csv(path, usecols=["time"])
        if df.empty:
            return None

        times = pd.to_datetime(df["time"], utc=True)
        return times.min(), times.max()

    # -------------------------------------------------
    # Load
    # -------------------------------------------------

    def load_range(
        self,
        *,
        source: str,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        path = self._path(source=source, symbol=symbol, timeframe=timeframe)
        if not path.exists():
            raise FileNotFoundError(path)

        df = pd.read_csv(path)
        df["time"] = pd.to_datetime(df["time"], utc=True)

        return (
            df[(df["time"] >= start) & (df["time"] <= end)]
            .sort_values("time")
            .reset_index(drop=True)
        )

    # -------------------------------------------------
    # Save / append
    # -------------------------------------------------

    def save(
        self,
        *,
        source: str,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame,
    ) -> None:
        path = self._path(source=source, symbol=symbol, timeframe=timeframe)
        path.parent.mkdir(parents=True, exist_ok=True)

        df = (
            df.sort_values("time")
            .drop_duplicates(subset="time", keep="last")
            .reset_index(drop=True)
        )

        df.to_csv(path, index=False)

    def append(
        self,
        *,
        source: str,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame,
    ) -> None:
        path = self._path(source=source, symbol=symbol, timeframe=timeframe)

        if not path.exists():
            self.save(
                source=source,
                symbol=symbol,
                timeframe=timeframe,
                df=df,
            )
            return

        existing = pd.read_csv(path)
        combined = pd.concat([existing, df], ignore_index=True)

        combined["time"] = pd.to_datetime(combined["time"], utc=True)
        combined = (
            combined.sort_values("time")
            .drop_duplicates(subset="time", keep="last")
            .reset_index(drop=True)
        )

        combined.to_csv(path, index=False)