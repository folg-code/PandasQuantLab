from typing import Optional

from core.utils.position_sizer import get_pip_value, get_point_size


class Trade:
    """Reprezentuje pojedynczy trade."""

    def __init__(self, symbol: str, direction: str, entry_time, entry_price: float,
                 position_size: float, sl: float, tp1: Optional[float] = None,
                 tp2: Optional[float] = None, entry_tag: str = None):
        self.symbol = symbol
        self.direction = direction
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.position_size = position_size
        self.sl = sl
        self.tp1 = tp1
        self.tp2 = tp2
        self.entry_tag = entry_tag

        # Wyniki trade'u
        self.exit_time = None
        self.exit_price = None
        self.exit_reason = None
        self.tp1_executed = False
        self.tp1_price = None
        self.tp1_time = None
        self.tp1_exit_reason = None
        self.tp1_pnl = None
        self.pnl = 0
        self.pnl_usd = 0
        self.returns = None
        self.duration_sec = None

    def close_trade(self, exit_price: float, exit_time, exit_reason: str):
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_reason = exit_reason
        self.compute_pnl()
        self.compute_returns()
        self.compute_duration()

    def compute_pnl(self):
        pnl_total = 0.0

        if self.tp1_executed and self.tp1_price is not None:
            # PnL za 50% pozycji zrealizowanej na TP1
            pnl_total += (self.tp1_price - self.entry_price) * (
                        self.position_size / 2) if self.direction == "long" else (self.entry_price - self.tp1_price) * (
                        self.position_size / 2)

        # Pozostała część pozycji zamknięta na exit_price
        remaining_size = self.position_size / 2 if self.tp1_executed else self.position_size
        pnl_total += (self.exit_price - self.entry_price) * remaining_size if self.direction == "long" else (self.entry_price - self.exit_price) * remaining_size

        self.pnl = pnl_total

        # PnL w USD
        pip_value = get_pip_value(self.symbol)
        point_size = get_point_size(self.symbol)
        self.pnl_usd = self.pnl * (pip_value / point_size)

    def compute_returns(self):
        # returns liczymy względem pełnej pozycji wejściowej
        self.returns = self.pnl / (self.entry_price * self.position_size)

    def compute_duration(self):
        self.duration_sec = (self.exit_time - self.entry_time).total_seconds()

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_time": self.entry_time,
            "exit_time": self.exit_time,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "position_size": self.position_size,
            "pnl": self.pnl,
            "pnl_usd": self.pnl_usd,
            "returns": self.returns,
            "exit_tag": self.exit_reason,
            "entry_tag": self.entry_tag,
            "tp1_price": self.tp1_price,
            "tp1_time": self.tp1_time,
            "tp1_exit_reason": self.tp1_exit_reason,
            "tp1_pnl": self.tp1_pnl,
            "duration": self.duration_sec,
        }