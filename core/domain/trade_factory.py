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

        trade.close_trade(exit_result)

        return trade.to_dict()