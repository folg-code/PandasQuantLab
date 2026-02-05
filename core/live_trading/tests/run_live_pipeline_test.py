# core/live_trading/strategy_runner.py

from dataclasses import dataclass
from typing import Dict

import pandas as pd
import MetaTrader5 as mt5

from core.data_provider.clients.mt5_client import (
    lookback_to_bars,
    MT5Client,
)
from core.live_trading.engine import LiveEngine
from core.live_trading.strategy_adapter import LiveStrategyAdapter
from core.live_trading.execution import PositionManager
from core.live_trading.execution import MT5Adapter
from core.live_trading.trade_repo import TradeRepo
from core.live_trading.strategy_loader import load_strategy, load_strategy_class
from core.utils.lookback import LOOKBACK_CONFIG, MIN_HTF_BARS
from core.utils.timeframe import MT5_TIMEFRAME_MAP


@dataclass
class LiveTradingConfig:
    symbol: str
    timeframe: str
    strategy_class: str

    startup_candle_count: int
    tick_interval_sec: float

    volume: float
    dry_run: bool


class LiveTradingRunner:
    """
    Production-grade MT5 live trading runner.
    Symmetric to BacktestRunner.
    """

    def __init__(self, cfg: LiveTradingConfig):
        self.cfg = cfg

        self.engine: LiveEngine | None = None
        self.strategy = None
        self.provider: MT5Client | None = None

    # ==================================================
    # 1️⃣ MT5 BOOTSTRAP
    # ==================================================

    def init_mt5(self):
        if not mt5.initialize():
            raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")

        if not mt5.symbol_select(self.cfg.symbol, True):
            raise RuntimeError(f"Symbol not available: {self.cfg.symbol}")

        info = mt5.account_info()
        print(
            f"🟢 MT5 connected | "
            f"Account={info.login} "
            f"Balance={info.balance}"
        )

    # ==================================================
    # 2️⃣ INITIAL DATA SNAPSHOT (WARMUP)
    # ==================================================

    def load_initial_data(self) -> pd.DataFrame:
        tf = MT5_TIMEFRAME_MAP[self.cfg.timeframe]
        lookback = LOOKBACK_CONFIG[self.cfg.timeframe]
        bars = lookback_to_bars(self.cfg.timeframe, lookback)

        rates = mt5.copy_rates_from_pos(
            self.cfg.symbol, tf, 0, bars
        )

        if rates is None or len(rates) == 0:
            raise RuntimeError("Initial MT5 data fetch failed")

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)

        print(
            f"📦 Warmup data loaded | "
            f"{len(df)} candles ({self.cfg.timeframe})"
        )

        return df

    # ==================================================
    # 3️⃣ INFORMATIVE PROVIDER (HTF)
    # ==================================================

    def build_provider(self) -> MT5Client:
        StrategyClass = load_strategy_class(self.cfg.strategy_class)

        bars_per_tf: Dict[str, int] = {}
        for tf in StrategyClass.get_required_informatives():
            lookback = LOOKBACK_CONFIG[tf]
            bars_per_tf[tf] = max(
                lookback_to_bars(tf, lookback),
                MIN_HTF_BARS.get(tf, 0),
            )

        provider = MT5Client(bars_per_tf=bars_per_tf)
        print(f"📡 Informative provider ready: {bars_per_tf}")

        return provider

    # ==================================================
    # 4️⃣ STRATEGY BOOTSTRAP
    # ==================================================

    def build_strategy(self, df_execution: pd.DataFrame):
        self.provider = self.build_provider()

        self.strategy = load_strategy(
            name=self.cfg.strategy_class,
            df=df_execution,
            symbol=self.cfg.symbol,
            startup_candle_count=self.cfg.startup_candle_count,
            provider=self.provider,
        )

        print(f"🧠 Strategy loaded: {self.cfg.strategy_class}")
        return self.strategy

    # ==================================================
    # 5️⃣ ENGINE
    # ==================================================

    def build_engine(self):

        adapter = MT5Adapter(dry_run=self.cfg.dry_run)
        repo = TradeRepo()
        pm = PositionManager(repo=repo, adapter=adapter)

        strategy_adapter = LiveStrategyAdapter(
            strategy=self.strategy,
            volume=self.cfg.volume,
        )

        tf = MT5_TIMEFRAME_MAP[self.cfg.timeframe]

        def market_data_provider():
            rates = mt5.copy_rates_from_pos(
                self.cfg.symbol, tf, 0, 2
            )
            if rates is None or len(rates) < 2:
                return None

            last_closed = rates[-2]
            return {
                "price": last_closed["close"],
                "time": pd.to_datetime(
                    last_closed["time"], unit="s", utc=True
                ),
                "candle_time": last_closed["time"],
            }

        self.engine = LiveEngine(
            position_manager=pm,
            market_data_provider=market_data_provider,
            strategy_adapter=strategy_adapter,
            tick_interval_sec=self.cfg.tick_interval_sec,
        )

        print("⚙️ LiveEngine ready")

    # ==================================================
    # 6️⃣ RUN
    # ==================================================

    def run(self):
        print("🚀 LiveTradingRunner start")

        self.init_mt5()
        df_execution = self.load_initial_data()
        self.build_strategy(df_execution)
        self.build_engine()

        print(
            f"🚀 LIVE TRADING STARTED | "
            f"{self.cfg.symbol} {self.cfg.timeframe} "
            f"DRY_RUN={self.cfg.dry_run}"
        )

        self.engine.start()

    # ==================================================
    # 7️⃣ SHUTDOWN
    # ==================================================

    def shutdown(self):
        mt5.shutdown()
        print("🔴 MT5 shutdown")