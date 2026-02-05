from __future__ import annotations

from datetime import datetime
from typing import Any

from core.live_trading.execution.mt5_adapter import MT5Adapter
from core.live_trading.trade_repo import TradeRepo


class TradeStateService:
    def __init__(self, repo: TradeRepo, adapter: MT5Adapter):
        self.repo = repo
        self.adapter = adapter

    def has_active_position(self, symbol: str) -> bool:
        active = self.repo.load_active()
        return any(trade["symbol"] == symbol for trade in active.values())

    def record_entry(self, *, plan, exec_result: dict, entry_time: datetime) -> None:
        self.repo.record_entry_from_plan(plan=plan, exec_result=exec_result, entry_time=entry_time)

    def record_exit(self, *, trade_id: str, price: float, time: datetime, reason: str, exit_level_tag: str | None) -> None:
        self.repo.record_exit(
            trade_id=trade_id,
            exit_price=price,
            exit_time=time,
            exit_reason=reason,
            exit_level_tag=exit_level_tag,
        )

    def mark_tp1_executed(self, *, trade_id: str, price: float, now: datetime, remain_volume: float) -> None:
        active = self.repo.load_active()
        trade = active.get(trade_id)
        if not trade:
            return
        trade["tp1_executed"] = True
        trade["tp1_price"] = price
        trade["tp1_time"] = now
        trade["volume"] = remain_volume
        active[trade_id] = trade
        self.repo.save_active(active)

    def update_sl(self, *, trade_id: str, new_sl: float) -> None:
        active = self.repo.load_active()
        trade = active.get(trade_id)
        if not trade:
            return
        self.adapter.modify_sl(ticket=trade["ticket"], new_sl=new_sl)
        trade["sl"] = new_sl
        active[trade_id] = trade
        self.repo.save_active(active)

    def set_flag(self, *, trade_id: str, key: str, value: Any) -> None:
        active = self.repo.load_active()
        trade = active.get(trade_id)
        if not trade:
            return
        trade[key] = value
        active[trade_id] = trade
        self.repo.save_active(active)