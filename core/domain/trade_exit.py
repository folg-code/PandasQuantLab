# core/domain/trade_exit.py
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class TradeExitReason(Enum):
    SL = "SL"
    TP1 = "TP1"
    TP2 = "TP2"
    BE = "BE"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TradeExitResult:
    exit_price: float
    exit_time: datetime
    reason: TradeExitReason

    tp1_executed: bool = False
    tp1_price: Optional[float] = None
    tp1_time: Optional[datetime] = None

    pnl_usd: Optional[float] = None
    returns: Optional[float] = None