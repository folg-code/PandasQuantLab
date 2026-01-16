# core/domain/strategy.py

from dataclasses import dataclass
from typing import Optional, Literal


# ==================================================
# Trade plan (strategy → engine)
# ==================================================

@dataclass(frozen=True)
class TradePlan:
    """
    Immutable description of a trade intent produced by a strategy.
    """

    symbol: str
    direction: Literal["long", "short"]

    entry_price: float
    sl: float

    # optional targets
    tp1: Optional[float] = None
    tp2: Optional[float] = None

    volume: float = 0.0
    entry_tag: str = ""

    # 🔑 who controls exits after entry
    exit_mode: Literal["fixed", "managed"] = "fixed"


# ==================================================
# Trade action (strategy → manager, post-entry)
# ==================================================

@dataclass(frozen=True)
class TradeAction:
    """
    Action decided by a managed-exit strategy.
    """

    action: Literal["move_sl", "close"]
    price: float
    reason: str