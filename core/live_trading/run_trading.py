import MetaTrader5 as mt5
import pandas as pd

from core.data_provider.clients.mt5_client import (
    lookback_to_bars,
    MT5Client,
)
from core.data_provider.providers.live_provider import LiveStrategyDataProvider
from core.live_trading.engine import LiveEngine
from core.live_trading.execution.mt5_adapter import MT5Adapter
from core.live_trading.execution.position_manager import PositionManager
from core.live_trading.logging import create_live_logger
from core.live_trading.mt5_market_state import MT5MarketStateProvider
from core.live_trading.strategy_runner  import LiveStrategyRunner

from core.live_trading.trade_repo import TradeRepo
from core.live_trading.strategy_loader import  load_strategy_class
from core.logging.config import LoggerConfig
from core.logging.prefix import LOG_PREFIX
from core.logging.run_logger import RunLogger
from core.utils.lookback import LOOKBACK_CONFIG


class LiveTradingRunner:
    """
    Live trading application runner.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.log = create_live_logger(cfg.SYMBOLS)

    def run(self):
        self.log.info("starting live trading runner")

        if not mt5.initialize():
            self.log.error("MT5 init failed")
            raise RuntimeError("MT5 init failed")

        mt5.symbol_select(self.cfg.SYMBOLS, True)
        self.log.info(
            "MT5 initialized",
        )

        StrategyClass = load_strategy_class(self.cfg.STRATEGY_CLASS)

        bars_per_tf = {}
        for tf in [self.cfg.TIMEFRAME] + StrategyClass.get_required_informatives():
            lookback = LOOKBACK_CONFIG[tf]
            bars_per_tf[tf] = lookback_to_bars(tf, lookback)

        self.log.debug(
            "bars_per_tf built",
            # jeśli chcesz, możesz to dać do contextu
        )

        client = MT5Client()
        data_provider = LiveStrategyDataProvider(
            client=client,
            bars_per_tf=bars_per_tf,
        )

        strategy = StrategyClass(
            df=None,
            symbol=self.cfg.SYMBOLS,
            startup_candle_count=self.cfg.STARTUP_CANDLE_COUNT,
        )

        strategy_runner = LiveStrategyRunner(
            strategy=strategy,
            data_provider=data_provider,
            symbol=self.cfg.SYMBOLS,
        )

        market_state_provider = MT5MarketStateProvider(
            symbol=self.cfg.SYMBOLS,
            timeframe=self.cfg.TIMEFRAME,
        )

        adapter = MT5Adapter(
            dry_run=self.cfg.DRY_RUN,
            log=self.log.with_context(component="adapter"),
        )
        repo = TradeRepo()
        pm = PositionManager(repo=repo, adapter=adapter)

        engine = LiveEngine(
            position_manager=pm,
            market_state_provider=market_state_provider,
            strategy_runner=strategy_runner,
            tick_interval_sec=self.cfg.TICK_INTERVAL_SEC,
        )

        self.log.with_context(
            timeframe=self.cfg.TIMEFRAME,
            dry_run=self.cfg.DRY_RUN,
        ).info("LIVE STARTED")

        engine.start()