from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass(frozen=True)
class ExitResult:
    exit_price: float
    exit_time: datetime
    reason: str  # "SL" | "TP2" | "TIMEOUT"


class LiveExitRules:
    @staticmethod
    def check_exit(*, trade: dict, price: float, now: datetime) -> Optional[ExitResult]:
        direction = trade["direction"]
        sl = trade["sl"]
        tp2 = trade.get("tp2")

        # SL
        if direction == "long" and price <= sl:
            return ExitResult(price, now, "SL")
        if direction == "short" and price >= sl:
            return ExitResult(price, now, "SL")

        # TP2
        if tp2 is not None:
            if direction == "long" and price >= tp2:
                return ExitResult(price, now, "TP2")
            if direction == "short" and price <= tp2:
                return ExitResult(price, now, "TP2")

        # TIMEOUT
        entry_time = trade["entry_time"]
        if isinstance(entry_time, str):
            entry_time = datetime.fromisoformat(entry_time)
        if now - entry_time > timedelta(hours=24):
            return ExitResult(price, now, "TIMEOUT")

        return None

    @staticmethod
    def check_tp1_hit(*, trade: dict, price: float) -> bool:
        tp1 = trade.get("tp1")
        if tp1 is None:
            return False
        if trade["direction"] == "long":
            return price >= tp1
        return price <= tp1