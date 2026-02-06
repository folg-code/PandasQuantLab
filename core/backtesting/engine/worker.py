
import pandas as pd

from config.logger_config import RunLogger, LoggerConfig
from core.backtesting.engine.backtester import Backtester
from core.backtesting.strategy_runner import strategy_orchestration


def run_backtest_worker(
    *,
    signals_df: pd.DataFrame,
    trade_plans: pd.DataFrame,
) -> pd.DataFrame:
    """
    Run backtest for ONE strategy on ONE symbol.
    Multiprocessing-safe.
    """

    backtester = Backtester()

    return backtester.run(
        signals_df=signals_df,
        trade_plans=trade_plans,
    )


def run_strategy_worker(
    *,
    symbol: str,
    data_by_tf: dict[str, pd.DataFrame],
    strategy_cls,
    startup_candle_count: int,
):
    logger = RunLogger(
        name=f"StrategyWorker[{symbol}]",
        cfg=LoggerConfig(stdout=False, file=False, timing=True),
        prefix=f"📐 STRATEGY[{symbol}] |",
    )

    result = strategy_orchestration(
        symbol=symbol,
        data_by_tf=data_by_tf,
        strategy_cls=strategy_cls,
        startup_candle_count=startup_candle_count,
        logger=logger,
    )
    return result
