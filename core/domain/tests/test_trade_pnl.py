from datetime import datetime, timedelta

import pytest

from core.domain.trade.trade import Trade
from core.domain.trade.trade_exit import TradeExitResult, TradeExitReason


def make_trade(direction="long"):
    return Trade(
        symbol="EURUSD",
        direction=direction,
        entry_time=datetime(2023, 1, 1),
        entry_price=1.0000,
        position_size=1.0,
        sl=0.9900,
        tp1=1.0100,
        tp2=1.0200,
        entry_tag="test",
        point_size=0.0001,
        pip_value=10.0,
    )


def test_pnl_long_no_tp1():
    trade = make_trade("long")

    trade.close_trade(
        TradeExitResult(
            exit_price=1.0100,
            exit_time=trade.entry_time + timedelta(hours=1),
            reason=TradeExitReason.TP2,
        )
    )

    assert trade.pnl_usd == pytest.approx(1000.0, rel=1e-9)


def test_pnl_short_no_tp1():
    trade = make_trade("short")

    trade.close_trade(
        TradeExitResult(
            exit_price=0.9900,
            exit_time=trade.entry_time + timedelta(hours=1),
            reason=TradeExitReason.TP2,
        )
    )

    assert trade.pnl_usd == pytest.approx(1000.0, rel=1e-9)


def test_pnl_with_tp1_partial():
    trade = make_trade("long")

    trade.close_trade(
        TradeExitResult(
            exit_price=1.0200,
            exit_time=trade.entry_time + timedelta(hours=2),
            reason=TradeExitReason.TP2,
            tp1_executed=True,
            tp1_price=1.0100,
            tp1_time=trade.entry_time + timedelta(hours=1),
        )
    )

    # 50% @ +100 pips, 50% @ +200 pips
    expected = (100 * 10 * 0.5) + (200 * 10 * 0.5)
    assert trade.pnl_usd == pytest.approx(expected, rel=1e-9)