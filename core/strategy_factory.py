from core.strategy_loader import load_strategy
from core.preprocessing import preprocess


def create_strategy(symbol, df, config):
    df = preprocess(df)
    return load_strategy(
        config.strategy,
        df,
        symbol,
        config.TIMEFRAME_MAP[config.TIMEFRAME]
    )