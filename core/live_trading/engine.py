from __future__ import annotations

from datetime import datetime
import time

from core.live_trading.strategy_runner import LiveStrategyRunner


class LiveEngine:
    """
    Live trading engine.
    """

    def __init__(
        self,
        *,
        position_manager,
        market_state_provider,
        strategy_runner,
        tick_interval_sec: float = 1.0,
    ):
        self.position_manager = position_manager
        self.market_state_provider = market_state_provider
        self.strategy_runner = strategy_runner
        self.tick_interval_sec = tick_interval_sec

        self._running = False
        self._last_strategy_state = None

    def start(self):
        self._running = True
        print("🟢 LiveEngine started")

        while self._running:
            try:
                self._tick()
            except Exception as e:
                print(f"❌ Engine error: {type(e).__name__}: {e}")

            time.sleep(self.tick_interval_sec)

    def stop(self):
        self._running = False
        print("🔴 LiveEngine stopped")

    def _tick(self):
        market_state = self.market_state_provider.poll()
        if market_state is None:
            return

        # ---------------------------
        # EXIT LOGIC (tick-based)
        # ---------------------------
        self.position_manager.on_tick(market_state=market_state)

        # ---------------------------
        # ENTRY LOGIC (candle-based)
        # ---------------------------
        if market_state.get("candle_time") is None:
            return

        result = self.strategy_runner.run()
        self._last_strategy_state = result.last_row

        if result.plan is not None:
            self.position_manager.on_trade_plan(
                plan=result.plan,
                market_state=market_state,
            )