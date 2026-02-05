from time import perf_counter
from uuid import uuid4

import pandas as pd

from config.report_config import ReportConfig, StdoutMode
from core.backtesting.backend_factory import create_backtest_backend
from core.backtesting.engine.backtester import Backtester
from core.backtesting.results.metadata import BacktestMetadata
from core.backtesting.results.result import BacktestResult
from core.backtesting.results.store import ResultStore
from core.backtesting.strategy_runner import run_strategy_single
from core.data_provider import DefaultOhlcvDataProvider, CsvMarketDataCache
from core.live_trading.strategy_loader import load_strategy_class
from core.reporting.runner import ReportRunner


class BacktestRunner:
    """
    Application-layer orchestrator.

    Responsibilities:
    - load market data
    - execute strategies
    - run backtests
    - build BacktestResult
    - trigger reporting
    """

    def __init__(self, cfg):
        self.cfg = cfg

        self.provider = None

        self.strategy = None        # reference strategy
        self.strategies = []        # all instantiated strategies

        self.signals_df: pd.DataFrame | None = None
        self.trades_df: pd.DataFrame | None = None

    # ==================================================
    # 1️⃣ DATA LOADING
    # ==================================================

    def load_data(self) -> dict[str, pd.DataFrame]:
        backend = create_backtest_backend(self.cfg.BACKTEST_DATA_BACKEND)

        start = pd.Timestamp(self.cfg.TIMERANGE["start"], tz="UTC")
        end = pd.Timestamp(self.cfg.TIMERANGE["end"], tz="UTC")

        self.provider = DefaultOhlcvDataProvider(
            backend=backend,
            cache=CsvMarketDataCache(self.cfg.MARKET_DATA_PATH),
            backtest_start=start,
            backtest_end=end,
        )

        all_data = {}

        for symbol in self.cfg.SYMBOLS:
            df = self.provider.get_ohlcv(
                symbol=symbol,
                timeframe=self.cfg.TIMEFRAME,
                start=start,
                end=end,
            )
            all_data[symbol] = df

        return all_data

    # ==================================================
    # 2️⃣ STRATEGY EXECUTION
    # ==================================================

    def run_strategies(self, all_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        all_signals = []
        self.strategies = []
        self.strategy = None

        strategy_cls = load_strategy_class(self.cfg.STRATEGY_CLASS)

        for symbol, df in all_data.items():
            df_signals, strategy = run_strategy_single(
                symbol=symbol,
                df=df,
                provider=self.provider,
                strategy_cls=strategy_cls,
                startup_candle_count=self.cfg.STARTUP_CANDLE_COUNT,
            )

            all_signals.append(df_signals)
            self.strategies.append(strategy)

            if self.strategy is None:
                self.strategy = strategy

        if not all_signals:
            raise RuntimeError("No signals generated")

        self.signals_df = (
            pd.concat(all_signals)
            .sort_values(["time", "symbol"])
            .reset_index(drop=True)
        )

        return self.signals_df

    # ==================================================
    # 3️⃣ BACKTEST
    # ==================================================

    def run_backtests(self) -> pd.DataFrame:
        if self.signals_df is None:
            raise RuntimeError("Signals not generated")

        backtester = Backtester(strategy=self.strategy)
        self.trades_df = backtester.run(self.signals_df)

        if self.trades_df.empty:
            raise RuntimeError("No trades generated")

        return self.trades_df

    # ==================================================
    # 4️⃣ RESULT BUILDING
    # ==================================================

    def _build_result(self) -> BacktestResult:
        if self.trades_df is None:
            raise RuntimeError("No trades to build result")

        run_id = f"bt_{uuid4().hex[:8]}"

        metadata = BacktestMetadata.now(
            run_id=run_id,
            backtest_mode=self.cfg.BACKTEST_MODE,
            windows=(
                self.cfg.BACKTEST_WINDOWS
                if self.cfg.BACKTEST_MODE == "split"
                else None
            ),
            strategies=[s.get_strategy_id() for s in self.strategies],
            strategy_names={
                s.get_strategy_id(): s.get_strategy_name()
                for s in self.strategies
            },
            symbols=self.cfg.SYMBOLS,
            timeframe=self.cfg.TIMEFRAME,
            initial_balance=self.cfg.INITIAL_BALANCE,
            slippage=self.cfg.SLIPPAGE,
            max_risk_per_trade=self.cfg.MAX_RISK_PER_TRADE,
        )

        return BacktestResult(
            metadata=metadata,
            trades=self.trades_df,
        )

    # ==================================================
    # 5️⃣ MAIN ENTRYPOINT
    # ==================================================

    def run(self):
        t0 = perf_counter()
        print("🚀 BacktestRunner | start")

        all_data = self.load_data()
        self.run_strategies(all_data)
        self.run_backtests()

        # --- build & save result ---
        result = self._build_result()
        store = ResultStore()
        run_path = store.save(result)

        # --- report config ---
        report_cfg = ReportConfig(
            stdout_mode=StdoutMode.CONSOLE,
            generate_dashboard=True,
            persist_report=True,
        )

        # --- reporting ---
        ReportRunner(
            result=result,
            config=self.cfg,
            report_config=report_cfg,
            run_path=run_path,
            plot_context=self.strategy.df_plot,
        ).run()

        print(f"🏁 Finished in {perf_counter() - t0:.2f}s")
