import pandas as pd

from core.orchestration.strategy_execution import execute_strategy


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

    strategy = strategy_cls(
        df=df.copy(),
        symbol=symbol,
        startup_candle_count=startup_candle_count,
    )
    strategy.validate()

    df_plot = execute_strategy(
        strategy=strategy,
        df=df,
        provider=provider,
        symbol=symbol,
        startup_candle_count=startup_candle_count,
    )

    report_config = strategy.build_report_config()
    strategy.report_config = report_config

    # -------------------------------------------------
    # FINALIZE DATAFRAMES (EXPLICIT CONTRACT)
    # -------------------------------------------------

    df_plot = df_plot.copy()

    # --- LEGACY BACKTEST CONTRACT ---

    REQUIRED_COLUMNS = [
        "time",
        "open",
        "high",
        "low",
        "close",
    ]


    SIGNAL_COLUMNS = [
        "signal_entry",
        "signal_exit",
        "levels",
    ]

    # build clean df for backtester
    df_signals = df_plot[
        REQUIRED_COLUMNS + [
            c for c in SIGNAL_COLUMNS if c in df_plot.columns
        ]
        ].copy()

    # --- HARD GUARANTEES ---
    if "signal_entry" not in df_signals.columns:
        df_signals["signal_entry"] = None

    if "signal_exit" not in df_signals.columns:
        df_signals["signal_exit"] = None

    if "levels" not in df_signals.columns:
        df_signals["levels"] = None

    if "symbol" not in df_signals.columns:
        df_signals["symbol"] = symbol

    # attach explicitly for downstream consumers
    strategy.df_plot = df_plot
    strategy.df_signals = df_signals

    # report configuration (strategy declaration → runtime state)
    strategy.report_config = strategy.build_report_config()

    return df_signals, strategy