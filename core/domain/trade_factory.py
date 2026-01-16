# core/domain/trade_factory.py

from core.domain.trade_exit import TradeExitResult
from core.domain.trade import Trade


class TradeFactory:

    @staticmethod
    def create_trade(
        *,
        symbol: str,
        direction: str,
        entry_time,
        entry_price: float,
        entry_tag: str,
        position_size: float,
        sl: float,
        tp1: float,
        tp2: float,
        point_size: float,
        pip_value: float,
        exit_result: TradeExitResult,
        legacy_exit_reason: str,
        tp1_pnl: float,
    ) -> dict:
        """
        Build Trade, apply exit result and return serialized dict.
        Backtester must not touch Trade internals.
        """

        trade = Trade(
            symbol=symbol,
            direction=direction,
            entry_time=entry_time,
            entry_price=entry_price,
            position_size=position_size,
            sl=sl,
            tp1=tp1,
            tp2=tp2,
            entry_tag=entry_tag,
            point_size=point_size,
            pip_value=pip_value,
        )

        # apply TP1 facts
        trade.tp1_executed = exit_result.tp1_executed
        trade.tp1_price = exit_result.tp1_price
        trade.tp1_time = exit_result.tp1_time
        trade.tp1_pnl = tp1_pnl

        # close trade (still legacy exit reason for now)
        trade.close_trade(
            exit_result.exit_price,
            exit_result.exit_time,
            legacy_exit_reason,
        )

        return trade.to_dict()