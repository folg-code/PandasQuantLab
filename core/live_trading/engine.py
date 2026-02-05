from __future__ import annotations

from datetime import datetime
import time

from core.live_trading.strategy_adapter import LiveStrategyAdapter


class LiveEngine:
    """
    Live trading engine.
    Tick loop:
    - always run exit logic
    - on new candle: update strategy and maybe execute entry
    """

    def __init__(
        self,
        *,
        position_manager,
        market_data_provider,
        strategy_adapter: LiveStrategyAdapter,
        tick_interval_sec: float = 1.0,
    ):
        self.position_manager = position_manager
        self.market_data_provider = market_data_provider
        self.strategy_adapter = strategy_adapter
        self.tick_interval_sec = tick_interval_sec

        self._running = False
        self._last_candle_time = None

        # keep last candle-derived state for tick-based management
        self._last_strategy_row = None

    def start(self):
        self._running = True
        print("🟢 LiveEngine started")
        self._run_loop()

    def stop(self):
        self._running = False
        print("🔴 LiveEngine stopped")

    def _run_loop(self):
        last_heartbeat = time.time()

        while self._running:
            try:
                self._tick()
            except Exception as e:
                print(f"❌ Engine error: {type(e).__name__}: {e}")

            if time.time() - last_heartbeat > 30:
                print("💓 Engine alive")
                last_heartbeat = time.time()

            time.sleep(self.tick_interval_sec)

    def _tick(self):
        market_state = self.market_data_provider()
        if market_state is None:
            return

        market_state.setdefault("time", datetime.utcnow())

        # -----------------------------------------
        # Inject last strategy management signals
        # -----------------------------------------
        if self._last_strategy_row is not None:
            # these keys are optional in your DF
            se = self._last_strategy_row.get("signal_exit")
            csl = self._last_strategy_row.get("custom_stop_loss")

            if isinstance(se, dict):
                market_state["signal_exit"] = se
            if isinstance(csl, dict):
                market_state["custom_stop_loss"] = csl

        # -----------------------------------------
        # EXIT LOGIC (tick-based)
        # -----------------------------------------
        self.position_manager.on_tick(market_state=market_state)

        # -----------------------------------------
        # ENTRY LOGIC (candle-based)
        # -----------------------------------------
        candle_time = market_state.get("candle_time")
        if candle_time is None:
            return

        if self._last_candle_time == candle_time:
            return

        self._last_candle_time = candle_time

        result = self.strategy_adapter.on_new_candle()
        self._last_strategy_row = result.last_row

        if result.plan is not None:
            self.position_manager.on_trade_plan(
                plan=result.plan,
                market_state=market_state,
            )