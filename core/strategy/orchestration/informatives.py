from __future__ import annotations

from collections import defaultdict
from typing import Dict

import pandas as pd


def apply_informatives(
    *,
    df: pd.DataFrame,
    strategy,
    data_by_tf: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Apply strategy informatives (HTF data) to main dataframe.

    NO IO.
    Uses preloaded data_by_tf.
    """

    if "time" not in df.columns:
        raise ValueError("Main dataframe must contain 'time' column")

    # ==================================================
    # 1️⃣ Collect informative methods
    # ==================================================

    informatives: dict[str, list] = defaultdict(list)

    for attr in dir(strategy):
        fn = getattr(strategy, attr)
        if callable(fn) and getattr(fn, "_informative", False):
            tf = fn._informative_timeframe
            informatives[tf].append(fn)

    if not informatives:
        return df

    out = df.copy()

    # ==================================================
    # 2️⃣ Apply informatives per TF
    # ==================================================

    for tf, methods in informatives.items():
        if tf not in data_by_tf:
            raise RuntimeError(
                f"Strategy requires informative TF={tf} "
                f"but it was not preloaded"
            )

        df_tf = data_by_tf[tf].copy()

        if "time" not in df_tf.columns:
            raise RuntimeError(
                f"Informative DF for TF={tf} has no 'time' column"
            )

        # apply strategy methods
        for method in methods:
            df_tf = method(df_tf)

        # merge-asof
        suffix = f"_{tf}"

        df_tf_prefixed = df_tf.rename(
            columns={
                c: f"{c}{suffix}"
                for c in df_tf.columns
                if c != "time"
            }
        )

        out = pd.merge_asof(
            out.sort_values("time"),
            df_tf_prefixed.sort_values("time"),
            on="time",
            direction="backward",
        )

    return out