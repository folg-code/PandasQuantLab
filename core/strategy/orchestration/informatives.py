from __future__ import annotations

from collections import defaultdict
from typing import Dict

import pandas as pd


def apply_informatives(
    *,
    df: pd.DataFrame,
    strategy,
    provider,
    symbol: str,
    startup_candle_count: int,
) -> pd.DataFrame:
    """
    Apply strategy informatives (HTF data) to main dataframe.

    Shared orchestration used by BOTH backtest and live runners.
    Strategy only declares informatives; this function executes them.
    """

    if provider is None:
        return df

    if "time" not in df.columns:
        raise ValueError("Main dataframe must contain 'time' column")

    # ==================================================
    # 1️⃣ Collect informative methods from strategy
    # ==================================================

    informatives: Dict[str, list] = defaultdict(list)

    for attr in dir(strategy):
        fn = getattr(strategy, attr)
        if callable(fn) and getattr(fn, "_informative", False):
            tf = fn._informative_timeframe
            informatives[tf].append(fn)

    if not informatives:
        return df

    informative_results: Dict[str, pd.DataFrame] = {}


    for tf in informatives:
        df_tf = provider.get_informative_df(
            symbol=symbol,
            timeframe=tf,
            startup_candle_count=startup_candle_count,
        )

        if "time" not in df_tf.columns:
            raise RuntimeError(
                f"Informative DF for TF={tf} has no 'time'. "
                f"Columns={list(df_tf.columns)}"
            )

        informative_results[tf] = df_tf


    for tf, methods in informatives.items():
        df_tf = informative_results[tf]
        for method in methods:
            df_tf = method(df_tf)
        informative_results[tf] = df_tf

    out = df.copy()

    for tf, df_tf in informative_results.items():
        suffix = f"_{tf}"

        cols_to_drop = [c for c in out.columns if c.endswith(suffix)]
        if cols_to_drop:
            out = out.drop(columns=cols_to_drop)

        df_tf_prefixed = df_tf.rename(
            columns={c: f"{c}_{tf}" for c in df_tf.columns if c != "time"}
        ).copy()

        df_tf_prefixed[f"time_{tf}"] = df_tf["time"]

        out = pd.merge_asof(
            out.sort_values("time"),
            df_tf_prefixed.sort_values(f"time_{tf}"),
            left_on="time",
            right_on=f"time_{tf}",
            direction="backward",
        )

        if "time_x" in out.columns:
            out = out.rename(columns={"time_x": "time"})
        if "time_y" in out.columns:
            out = out.drop(columns=["time_y"])

        out = out.drop(columns=[f"time_{tf}"])

    return out