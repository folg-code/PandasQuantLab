import pandas as pd
from core.strategy.orchestration.informatives import apply_informatives


def execute_strategy(
    *,
    strategy,
    df: pd.DataFrame,
    provider,
    symbol: str,
    startup_candle_count: int,
) -> pd.DataFrame:
    """
    Shared strategy execution pipeline.
    Used by backtest and live.
    """

    # Informatives
    df = apply_informatives(
        df=df,
        strategy=strategy,
        provider=provider,
        symbol=symbol,
        startup_candle_count=startup_candle_count,
    )

    strategy.df = df

    # Core strategy logic
    strategy.populate_indicators()
    strategy.populate_entry_trend()
    strategy.populate_exit_trend()

    return strategy.df