import pandas as pd
from core.strategy.orchestration.informatives import apply_informatives


def execute_strategy(
    *,
    strategy,
    df: pd.DataFrame,
    data_by_tf: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Shared strategy execution pipeline.
    Used by backtest and live.
    """

    df = apply_informatives(
        df=df,
        strategy=strategy,
        data_by_tf=data_by_tf,
    )

    strategy.df = df

    strategy.populate_indicators()
    strategy.populate_entry_trend()
    strategy.populate_exit_trend()

    return strategy.df
