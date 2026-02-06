import pytest
from core.backtesting.exit.exit_mapping import map_exit_code_to_reason
from core.domain.trade.trade_exit import TradeExitReason
from core.backtesting.exit.simulate_exit_numba import (
    EXIT_SL,
    EXIT_TP1_BE,
    EXIT_TP2,
    EXIT_EOD,
)


def test_exit_code_mapping():
    assert map_exit_code_to_reason(EXIT_SL) is TradeExitReason.SL
    assert map_exit_code_to_reason(EXIT_TP1_BE) is TradeExitReason.BE
    assert map_exit_code_to_reason(EXIT_TP2) is TradeExitReason.TP2
    assert map_exit_code_to_reason(EXIT_EOD) is TradeExitReason.TIMEOUT


def test_unknown_exit_code_raises():
    with pytest.raises(ValueError):
        map_exit_code_to_reason(999)