from __future__ import annotations

from time import perf_counter

import pandas as pd


def run_strategy_single(
    symbol: str,
    df: pd.DataFrame,
    provider,
    strategy_cls,
    startup_candle_count: int,
):
    """
    Run single strategy instance for one symbol.
    Must be top-level for multiprocessing.
    """

    # -------------------------------------------------
    # INIT STRATEGY
    # -------------------------------------------------
    t0 = perf_counter()
    strategy = strategy_cls(
        df=df,
        symbol=symbol,
        provider=provider,
        startup_candle_count=startup_candle_count,
    )

    # -------------------------------------------------
    # RUN STRATEGY PIPELINE
    # -------------------------------------------------
    df_signals = strategy.run()

    # -------------------------------------------------
    # FINALIZE
    # -------------------------------------------------
    if "symbol" not in df_signals.columns:
        df_signals["symbol"] = symbol

    # -------------------------------------------------
    # TOTAL
    # -------------------------------------------------

    return df_signals, strategy
