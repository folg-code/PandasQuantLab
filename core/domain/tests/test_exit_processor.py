from datetime import datetime

from core.domain.exit_processor import ExitProcessor
from core.domain.trade_exit import TradeExitReason
from core.backtesting.simulate_exit_numba import EXIT_SL, EXIT_TP2


def test_exit_processor_sl():
    result = ExitProcessor.process(
        direction="long",
        entry_price=1.0000,
        exit_price=0.9900,
        exit_time=datetime(2023, 1, 1),
        exit_code=EXIT_SL,
        tp1_executed=False,
        tp1_price=None,
        tp1_time=None,
        sl=0.9900,
        tp1=1.0100,
        tp2=1.0200,
        position_size=1.0,
        point_size=0.0001,
        pip_value=10.0,
    )

    assert result.reason is TradeExitReason.SL
    assert result.tp1_executed is False


def test_exit_processor_tp2():
    result = ExitProcessor.process(
        direction="long",
        entry_price=1.0000,
        exit_price=1.0200,
        exit_time=datetime(2023, 1, 1),
        exit_code=EXIT_TP2,
        tp1_executed=False,
        tp1_price=None,
        tp1_time=None,
        sl=0.9900,
        tp1=1.0100,
        tp2=1.0200,
        position_size=1.0,
        point_size=0.0001,
        pip_value=10.0,
    )

    assert result.reason is TradeExitReason.TP2