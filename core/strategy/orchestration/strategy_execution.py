import pandas as pd
from core.strategy.orchestration.informatives import apply_informatives


def execute_strategy(*, strategy, df, **kwargs):
    if kwargs:
        raise TypeError(
            f"execute_strategy does not accept extra args: {list(kwargs)}"
        )

    
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


