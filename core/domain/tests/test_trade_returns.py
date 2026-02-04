from datetime import datetime, timedelta

from core.domain.trade import Trade
from core.domain.trade_exit import TradeExitResult, TradeExitReason


def test_returns_are_normalized_by_risk():
    trade = Trade(
        symbol="EURUSD",
        direction="long",
        entry_time=datetime(2023, 1, 1),
        entry_price=1.0000,
        position_size=1.0,
        sl=0.9900,          # risk = 100 pips
        tp1=1.0100,
        tp2=1.0200,
        entry_tag="test",
        point_size=0.0001,
        pip_value=10.0,
    )

    trade.close_trade(
        TradeExitResult(
            exit_price=1.0100,   # +100 pips
            exit_time=trade.entry_time + timedelta(hours=1),
            reason=TradeExitReason.TP2,
        )
    )

    # zysk == risk → return = 1.0
    assert trade.returns == 1.0