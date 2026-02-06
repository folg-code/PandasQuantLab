from __future__ import annotations

from datetime import datetime

import MetaTrader5 as mt5

from config.live import MAX_RISK_PER_TRADE
from core.live_trading.execution.live.exit_rules import LiveExitRules
from core.live_trading.execution.live.trade_state_service import TradeStateService
from core.live_trading.execution.mapping.mt5_order_mapper import trade_plan_to_mt5_order
from core.live_trading.execution.policy.exit_execution import ExitExecution
from core.live_trading.execution.risk.mt5_risk_params import Mt5RiskParams
from core.live_trading.execution.risk.sizing import LiveSizer
from core.live_trading.execution.mt5_adapter import MT5Adapter
from core.live_trading.trade_repo import TradeRepo
from core.strategy.trade_plan import TradePlan


class PositionManager:
    """
    Live trading orchestration.

    Responsibilities:
    - consume TradePlan and execute entry
    - monitor active positions and perform exits
    - keep repo in sync with broker
    """

    def __init__(self, repo: TradeRepo, adapter: MT5Adapter):
        self.repo = repo
        self.adapter = adapter
        self.state = TradeStateService(repo=repo, adapter=adapter)

    # ==================================================
    # Helpers
    # ==================================================

    def _is_dry_run(self) -> bool:
        return bool(getattr(self.adapter, "dry_run", False))

    # ==================================================
    # ENTRY
    # ==================================================

    def on_trade_plan(self, *, plan: TradePlan, market_state: dict) -> None:
        if self.state.has_active_position(plan.symbol):
            print("⚠️ Position already active – skipping TradePlan")
            return

        execution = ExitExecution.from_config(plan.strategy_config)

        volume = self._compute_volume(plan=plan)
        params = trade_plan_to_mt5_order(
            plan=plan,
            volume=volume,
            execution=execution,
        )

        print(
            f"📦 EXECUTING TRADE PLAN | {plan.symbol} {plan.direction} "
            f"raw_vol={volume:.6f} norm_vol={params.volume}"
        )

        result = self.adapter.open_position(
            symbol=params.symbol,
            direction=params.direction,
            volume=params.volume,
            sl=params.sl,
            tp=params.tp,
        )

        # ENTRY may be skipped (CLOSE-ONLY, DRY_RUN guard etc.)
        if result is None:
            print(f"⚠ ENTRY skipped for {plan.symbol}")
            return

        self.state.record_entry(
            plan=plan,
            exec_result=result,
            entry_time=market_state["time"],
        )

    def _compute_volume(self, *, plan: TradePlan) -> float:
        cfg = plan.strategy_config or {}
        max_risk = float(cfg.get("MAX_RISK", MAX_RISK_PER_TRADE))

        raw_volume = LiveSizer.calculate_volume(
            symbol=plan.symbol,
            entry_price=plan.entry_price,
            sl=plan.exit_plan.sl,
            max_risk=max_risk,
        )
        return Mt5RiskParams.normalize_volume(plan.symbol, raw_volume)

    # ==================================================
    # TICK LOOP
    # ==================================================

    def on_tick(self, *, market_state: dict) -> None:
        active = self.repo.load_active()
        if not active:
            return

        price = market_state["price"]
        now: datetime = market_state["time"]

        for trade_id, trade in list(active.items()):
            if self._handle_broker_sync(trade_id=trade_id, trade=trade, now=now):
                continue

            execution = self._get_execution(trade)

            if self._handle_managed_exit_signal(
                trade_id=trade_id,
                trade=trade,
                market_state=market_state,
                price=price,
                now=now,
            ):
                continue

            if self._handle_tp1_and_be(
                trade_id=trade_id,
                trade=trade,
                execution=execution,
                price=price,
                now=now,
            ):
                continue

            self._handle_trailing_sl(
                trade_id=trade_id,
                trade=trade,
                market_state=market_state,
            )

            self._handle_engine_exit(
                trade_id=trade_id,
                trade=trade,
                execution=execution,
                price=price,
                now=now,
            )

    # ==================================================
    # Tick handlers
    # ==================================================

    def _handle_broker_sync(self, *, trade_id: str, trade: dict, now: datetime) -> bool:
        if self._is_dry_run():
            return False

        positions = mt5.positions_get(ticket=int(trade["ticket"]))
        if positions:
            return False

        print(f"🧹 Broker closed position {trade_id}, syncing repo")
        self.state.record_exit(
            trade_id=trade_id,
            price=trade.get("tp2") or trade.get("sl"),
            time=now,
            reason="BROKER_CLOSED",
            exit_level_tag="TP2_live",
        )
        return True

    def _handle_managed_exit_signal(
        self,
        *,
        trade_id: str,
        trade: dict,
        market_state: dict,
        price: float,
        now: datetime,
    ) -> bool:
        signal_exit = market_state.get("signal_exit")
        if not isinstance(signal_exit, dict):
            return False

        if (
            signal_exit.get("entry_tag_to_close") == trade.get("entry_tag")
            and signal_exit.get("direction") == "close"
        ):
            print(f"🚪 MANAGED EXIT for {trade_id}")

            if not self._is_dry_run():
                self.adapter.close_position(
                    ticket=trade["ticket"],
                    price=price,
                )

            self.state.record_exit(
                trade_id=trade_id,
                price=price,
                time=now,
                reason="MANAGED_EXIT",
                exit_level_tag=signal_exit.get("exit_tag"),
            )
            return True

        return False

    def _handle_tp1_and_be(
        self,
        *,
        trade_id: str,
        trade: dict,
        execution: ExitExecution,
        price: float,
        now: datetime,
    ) -> bool:
        if trade.get("tp1_executed"):
            return False

        if execution.tp1 == "DISABLED":
            return False

        if not LiveExitRules.check_tp1_hit(trade=trade, price=price):
            return False

        if execution.tp1 == "ENGINE":
            self._execute_tp1_partial(
                trade_id=trade_id,
                trade=trade,
                price=price,
                now=now,
            )

        if execution.be_on_tp1:
            self._try_move_sl_to_be(trade_id=trade_id, trade=trade)

        return execution.tp1 == "ENGINE"

    def _execute_tp1_partial(
        self,
        *,
        trade_id: str,
        trade: dict,
        price: float,
        now: datetime,
    ) -> None:
        total_vol = float(trade["volume"])
        cfg = trade.get("strategy_config", {})
        close_ratio = float(cfg.get("TP1_CLOSE_RATIO", 0.5))

        close_vol = round(total_vol * close_ratio, 2)
        remain_vol = total_vol - close_vol
        if close_vol <= 0 or remain_vol <= 0:
            return

        print(f"🎯 TP1 PARTIAL CLOSE {trade_id}: {close_vol}/{total_vol}")

        if not self._is_dry_run():
            self.adapter.close_partial(
                ticket=trade["ticket"],
                volume=close_vol,
                price=price,
            )

        self.state.mark_tp1_executed(
            trade_id=trade_id,
            price=price,
            now=now,
            remain_volume=remain_vol,
        )

    def _try_move_sl_to_be(self, *, trade_id: str, trade: dict) -> None:
        entry = float(trade["entry_price"])
        current_sl = float(trade["sl"])
        direction = trade["direction"]

        already_be = (
            (direction == "long" and current_sl >= entry)
            or (direction == "short" and current_sl <= entry)
        )
        if already_be:
            return

        print(f"🔁 MOVE SL → BE for {trade_id}")
        self.state.update_sl(trade_id=trade_id, new_sl=entry)
        self.state.set_flag(trade_id=trade_id, key="be_moved", value=True)

    def _handle_trailing_sl(
        self,
        *,
        trade_id: str,
        trade: dict,
        market_state: dict,
    ) -> None:
        cfg = trade.get("strategy_config", {})
        if not cfg.get("USE_TRAILING"):
            return

        trail_from = cfg.get("TRAIL_FROM", "tp1")
        if trail_from == "tp1" and not trade.get("tp1_executed"):
            return

        new_sl = market_state.get("custom_stop_loss")
        if not isinstance(new_sl, dict):
            return

        candidate = new_sl.get("level")
        if candidate is None:
            return

        candidate = float(candidate)
        current_sl = float(trade["sl"])
        direction = trade["direction"]

        improved = (
            (direction == "long" and candidate > current_sl)
            or (direction == "short" and candidate < current_sl)
        )
        if not improved:
            return

        print(f"📈 TRAILING SL {trade_id}: {current_sl} → {candidate}")
        self.state.update_sl(trade_id=trade_id, new_sl=candidate)

    def _handle_engine_exit(
        self,
        *,
        trade_id: str,
        trade: dict,
        execution: ExitExecution,
        price: float,
        now: datetime,
    ) -> bool:
        exit_res = LiveExitRules.check_exit(trade=trade, price=price, now=now)
        if exit_res is None:
            return False

        if not self._is_dry_run():
            self.adapter.close_position(
                ticket=trade["ticket"],
                price=exit_res.exit_price,
            )

        self.state.record_exit(
            trade_id=trade_id,
            price=exit_res.exit_price,
            time=exit_res.exit_time,
            reason=exit_res.reason,
            exit_level_tag=self._map_exit_level_tag(exit_res.reason),
        )
        return True

    def _get_execution(self, trade: dict) -> ExitExecution:
        raw = trade.get("exit_execution")
        if isinstance(raw, dict):
            return ExitExecution.from_config({"EXIT_EXECUTION": raw})

        cfg = trade.get("strategy_config", {})
        return ExitExecution.from_config(cfg)

    @staticmethod
    def _map_exit_level_tag(reason: str) -> str | None:
        if reason == "SL":
            return "SL_live"
        if reason == "TP2":
            return "TP2_live"
        if reason == "TIMEOUT":
            return "TIMEOUT_live"
        return None