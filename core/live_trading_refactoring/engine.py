# core/live_trading_refactoring/engine.py

import time
from datetime import datetime
from typing import Callable, Iterable, Dict, Any

from core.live_trading_refactoring.position_manager import PositionManager


class LiveEngine:
    """
    Live trading engine.
    Orchestrates lifecycle and delegates logic.
    """

    def __init__(
        self,
        *,
        position_manager: PositionManager,
        market_data_provider: Callable[[], Dict[str, Any]],
        signal_provider: Callable[[], Iterable[Dict[str, Any]]],
        tick_interval_sec: float = 1.0,
    ):
        self.position_manager = position_manager
        self.market_data_provider = market_data_provider
        self.signal_provider = signal_provider
        self.tick_interval_sec = tick_interval_sec

        self._running = False

    # ==================================================
    # Lifecycle
    # ==================================================

    def start(self):
        self._running = True
        print("🟢 LiveEngine started")
        self._run_loop()

    def stop(self):
        self._running = False
        print("🔴 LiveEngine stopped")

    # ==================================================
    # Main loop
    # ==================================================

    def _run_loop(self):
        while self._running:
            try:
                self._tick()
            except Exception as e:
                # fail-safe: engine never dies silently
                print(f"❌ Engine error: {e}")
            time.sleep(self.tick_interval_sec)

    def _tick(self):
        """
        Single engine tick.
        """

        # 1️⃣ Market state (price, time, etc.)
        market_state = self.market_data_provider()
        if market_state is None:
            return

        # enforce time presence
        market_state.setdefault("time", datetime.utcnow())

        # 2️⃣ Exit logic (on every tick)
        self.position_manager.on_tick(market_state=market_state)

        # 3️⃣ Entry signals
        signals = self.signal_provider() or []
        for signal in signals:
            self.position_manager.on_entry_signal(
                signal=signal,
                market_state=market_state,
            )