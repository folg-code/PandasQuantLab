import pandas as pd

OHLCV_COLUMNS = ["time", "open", "high", "low", "close", "volume"]
OHLCV_SET = set(OHLCV_COLUMNS)


def validate_ohlcv_schema(df: pd.DataFrame) -> None:
    missing = OHLCV_SET - set(df.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {missing}")


def ensure_utc_time(df: pd.DataFrame) -> pd.DataFrame:
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df


def sort_and_deduplicate(df: pd.DataFrame, *, keep: str = "last") -> pd.DataFrame:
    return (
        df.sort_values("time")
          .drop_duplicates(subset="time", keep=keep)
          .reset_index(drop=True)
    )


def finalize_ohlcv(df: pd.DataFrame, *, keep: str = "last") -> pd.DataFrame:

    if df is None:
        raise ValueError("df is None")

    df = df.copy()

    df.columns = [c.lower() for c in df.columns]

    validate_ohlcv_schema(df)

    ensure_utc_time(df)

    df = sort_and_deduplicate(df, keep=keep)

    return df[OHLCV_COLUMNS]