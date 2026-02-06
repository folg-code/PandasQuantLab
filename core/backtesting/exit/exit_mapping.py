from core.domain.trade.trade_exit import TradeExitReason
from core.backtesting.exit.simulate_exit_numba import (
    EXIT_SL,
    EXIT_TP1_BE,
    EXIT_TP2,
    EXIT_EOD,
)


def map_exit_code_to_reason(exit_code: int) -> TradeExitReason:
    if exit_code == EXIT_SL:
        return TradeExitReason.SL
    if exit_code == EXIT_TP1_BE:
        return TradeExitReason.BE
    if exit_code == EXIT_TP2:
        return TradeExitReason.TP2
    if exit_code == EXIT_EOD:
        return TradeExitReason.TIMEOUT

    raise ValueError(f"Unknown exit_code: {exit_code}")
