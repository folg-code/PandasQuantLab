import pytest

from core.domain.execution.execution_mapping import map_exit_code_to_reason
from core.domain.trade.trade_exit import TradeExitReason
from core.backtesting.simulate_exit_numba import (
    EXIT_SL,
    EXIT_TP1_BE,
    EXIT_TP2,
    EXIT_EOD,
)


@pytest.mark.parametrize(
    "exit_code, expected",
    [
        (EXIT_SL, TradeExitReason.SL),
        (EXIT_TP1_BE, TradeExitReason.BE),
        (EXIT_TP2, TradeExitReason.TP2),
        (EXIT_EOD, TradeExitReason.TIMEOUT),
        (999, TradeExitReason.UNKNOWN),
    ],
)
def test_map_exit_code_to_reason(exit_code, expected):
    reason = map_exit_code_to_reason(
        exit_code=exit_code,
        tp1_executed=False,
        exit_price=1.0,
        entry_price=1.0,
    )
    assert reason is expected