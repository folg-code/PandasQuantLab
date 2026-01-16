# core/domain/exit_processor.py

from core.domain.trade_exit import TradeExitResult
from core.domain.execution import map_exit_code_to_reason


class ExitProcessor:
    """
    Centralized exit interpretation & post-processing.
    Backtester must not know exit semantics.
    """

    @staticmethod
    def process(
        *,
        direction: str,
        entry_price: float,
        exit_price: float,
        exit_time,
        exit_code: int,
        tp1_executed: bool,
        tp1_price,
        tp1_time,
        sl: float,
        sl_tag: str,
        tp1: float,
        tp1_tag: str,
        tp2: float,
        tp2_tag: str,
        position_size: float,
        point_size: float,
        pip_value: float,
    ) -> tuple[TradeExitResult, dict]:
        """
        Returns:
            TradeExitResult   (domain fact)
            legacy dict      (exit_reason, tp1_pnl, tp1_time)
        """

        # -----------------------------
        # DOMAIN EXIT RESULT
        # -----------------------------
        reason = map_exit_code_to_reason(
            exit_code=exit_code,
            tp1_executed=tp1_executed,
            exit_price=exit_price,
            entry_price=entry_price,
        )

        exit_result = TradeExitResult(
            exit_price=exit_price,
            exit_time=exit_time,
            reason=reason,
            tp1_executed=tp1_executed,
            tp1_price=tp1_price if tp1_executed else None,
            tp1_time=tp1_time if tp1_executed else None,
        )

        # -----------------------------
        # LEGACY BRIDGE (UNCHANGED)
        # -----------------------------
        exit_reason = None
        if exit_price == sl:
            exit_reason = sl_tag
        elif tp1_executed and exit_price == entry_price:
            exit_reason = tp1_tag
        elif exit_price == tp2:
            exit_reason = tp2_tag
        else:
            exit_reason = tp2_tag

        tp1_pnl = 0.0
        if tp1_executed:
            if direction == "long":
                price_gain = tp1 - entry_price
            else:
                price_gain = entry_price - tp1

            tp1_pnl = (
                price_gain / point_size
                * pip_value
                * position_size
                * 0.5
            )

        legacy = {
            "exit_reason": exit_reason,
            "tp1_pnl": tp1_pnl,
            "tp1_time": tp1_time if tp1_executed else None,
        }

        return exit_result, legacy