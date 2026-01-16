# core/live_trading_refactoring/position_manager.py

import uuid
from datetime import datetime
from typing import Dict, Any

from core.live_trading_refactoring.trade_repo import TradeRepo
from core.live_trading_refactoring.mt5_adapter import MT5Adapter


class PositionManager:
    """
    Handles live trading decisions.
    ENTRY execution (no exits yet).
    """

    def __init__(self, repo: TradeRepo, adapter: MT5Adapter):
        self.repo = repo
        self.adapter = adapter

    # ==================================================
    # Public API
    # ==================================================

    def on_entry_signal(
        self,
        *,
        signal: Dict[str, Any],
        market_state: Dict[str, Any] | None = None,
    ) -> None:
        symbol = signal["symbol"]

        # 1️⃣ Guard: already active position on symbol
        if self._has_active_position(symbol):
            return

        # 2️⃣ Build trade_id
        trade_id = self._generate_trade_id(signal)

        # 3️⃣ Execute via adapter
        exec_result = self.adapter.open_position(
            symbol=symbol,
            direction=signal["direction"],
            volume=signal["volume"],
            price=signal["entry_price"],
            sl=signal["sl"],
            tp=signal.get("tp2"),
        )

        ticket = exec_result.get("ticket")

        # 4️⃣ Persist entry decision + execution info
        self.repo.record_entry(
            trade_id=trade_id,
            symbol=symbol,
            direction=signal["direction"],
            entry_price=signal["entry_price"],
            volume=signal["volume"],
            sl=signal["sl"],
            tp1=signal["tp1"],
            tp2=signal["tp2"],
            entry_time=signal.get("entry_time") or datetime.utcnow(),
            entry_tag=signal.get("entry_tag", ""),
            ticket=ticket,
        )

    # ==================================================
    # Internal helpers
    # ==================================================

    def _has_active_position(self, symbol: str) -> bool:
        active = self.repo.load_active()
        return any(trade["symbol"] == symbol for trade in active.values())

    def _generate_trade_id(self, signal: Dict[str, Any]) -> str:
        return f"LIVE_{signal['symbol']}_{uuid.uuid4().hex[:8]}"