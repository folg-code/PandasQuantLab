import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from time import perf_counter
from uuid import uuid4

import pandas as pd

from config.report_config import ReportConfig, StdoutMode
from core.backtesting.backend_factory import create_backtest_backend
from core.backtesting.engine.backtester import Backtester
from core.backtesting.engine.worker import run_backtest_worker, run_strategy_worker
from core.backtesting.results_logic.metadata import BacktestMetadata
from core.backtesting.results_logic.result import BacktestResult
from core.backtesting.results_logic.store import ResultStore
from core.backtesting.strategy_runner import run_strategy_single, StrategyRunResult
from core.data_provider import DefaultOhlcvDataProvider, CsvMarketDataCache
from core.live_trading.strategy_loader import load_strategy_class
from core.reporting.runner import ReportRunner
from core.reporting.summary_runner import SummaryReportRunner


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

    def load_data(self) -> dict[str, dict[str, pd.DataFrame]]:
        strategy_cls = load_strategy_class(self.cfg.STRATEGY_CLASS)

        # --- informatives declared by strategy ---
        informative_tfs = strategy_cls.get_required_informatives()
        base_tf = self.cfg.TIMEFRAME

        all_tfs = [base_tf] + informative_tfs

        backend = create_backtest_backend(self.cfg.BACKTEST_DATA_BACKEND)

        start = pd.Timestamp(self.cfg.TIMERANGE["start"], tz="UTC")
        end = pd.Timestamp(self.cfg.TIMERANGE["end"], tz="UTC")

        self.provider = DefaultOhlcvDataProvider(
            backend=backend,
            cache=CsvMarketDataCache(self.cfg.MARKET_DATA_PATH),
            backtest_start=start,
            backtest_end=end,
        )

        all_data: dict[str, dict[str, pd.DataFrame]] = {}

        for symbol in self.cfg.SYMBOLS:
            per_symbol = {}

            for tf in all_tfs:
                per_symbol[tf] = self.provider.get_ohlcv(
                    symbol=symbol,
                    timeframe=tf,
                    start=start,
                    end=end,
                )

            all_data[symbol] = per_symbol

        return all_data
    # ==================================================
    # 2️⃣ STRATEGY EXECUTION
    # ==================================================

    def run_strategies(self, all_data: dict[str, dict[str, pd.DataFrame]]) -> pd.DataFrame:
        strategy_cls = load_strategy_class(self.cfg.STRATEGY_CLASS)

        self.strategy_runs: list[StrategyRunResult] = []

        # ---------- FAST PATH ----------
        if len(all_data) == 1:
            symbol, data_by_tf = next(iter(all_data.items()))
            result = run_strategy_single(
                symbol=symbol,
                data_by_tf=data_by_tf,
                strategy_cls=strategy_cls,
                startup_candle_count=self.cfg.STARTUP_CANDLE_COUNT,
            )
            self.strategy_runs = [result]
            self.signals_df = result.df_signals
            return self.signals_df

        # ---------- PARALLEL PATH ----------
        futures = []

        with ProcessPoolExecutor() as executor:
            for symbol, data_by_tf in all_data.items():
                futures.append(
                    executor.submit(
                        run_strategy_worker,
                        symbol=symbol,
                        data_by_tf=data_by_tf,
                        strategy_cls=strategy_cls,
                        startup_candle_count=self.cfg.STARTUP_CANDLE_COUNT,
                    )
                )

            for f in as_completed(futures):
                self.strategy_runs.append(f.result())

        # ==================================================
        # AGGREGATE SIGNALS
        # ==================================================

        self.signals_df = (
            pd.concat([r.df_signals for r in self.strategy_runs])
            .sort_values(["time", "symbol"])
            .reset_index(drop=True)
        )

        return self.signals_df

    # ==================================================
    # 3️⃣ BACKTEST
    # ==================================================

    def run_backtests(self) -> pd.DataFrame:
        if not self.strategy_runs:
            raise RuntimeError("No strategy runs to backtest")

        self.trades_by_run: list[pd.DataFrame] = []

        # -----------------------------
        # FAST PATH (single run)
        # -----------------------------
        if len(self.strategy_runs) == 1:
            run = self.strategy_runs[0]

            backtester = Backtester()
            trades = backtester.run(
                signals_df=run.df_signals,
                trade_plans=run.trade_plans,
            )

            self.trades_by_run = [trades]
            self.trades_df = trades
            return trades

        # -----------------------------
        # PARALLEL PATH (multi run)
        # -----------------------------
        futures = []

        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            for run in self.strategy_runs:
                futures.append(
                    executor.submit(
                        run_backtest_worker,
                        signals_df=run.df_signals,
                        trade_plans=run.trade_plans,
                    )
                )

            for future in as_completed(futures):
                trades = future.result()
                self.trades_by_run.append(trades)

        if not self.trades_by_run:
            raise RuntimeError("No trades generated")

        # -----------------------------
        # AGGREGATE (OPTIONAL GLOBAL VIEW)
        # -----------------------------
        self.trades_df = (
            pd.concat(self.trades_by_run)
            .sort_values("exit_time")
            .reset_index(drop=True)
        )

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
        t = t0

        def log(step: str):
            nonlocal t
            now = perf_counter()
            print(f"⏱️ {step:<30} +{now - t:6.2f}s | total {now - t0:6.2f}s")
            t = now

        print("🚀 BacktestRunner | start")

        # =====================
        # LOAD DATA
        # =====================
        all_data = self.load_data()
        log("load_data")

        # =====================
        # STRATEGY LOGIC
        # =====================
        self.run_strategies(all_data)
        log("run_strategies")

        # =====================
        # BACKTESTS
        # =====================
        self.run_backtests()
        log("run_backtests")

        # =====================
        # PERSIST RAW RESULTS
        # =====================
        result = self._build_result()
        run_path = ResultStore().save(result)
        log("persist_results")

        # =====================
        # PER SYMBOL REPORTS
        # =====================
        for run, trades in zip(self.strategy_runs, self.trades_by_run):
            t_sym = perf_counter()

            ReportRunner(
                trades=trades,
                df_context=run.df_context,
                report_spec=run.report_spec,
                metadata=result.metadata,
                config=self.cfg,
                report_config=ReportConfig(
                    stdout_mode=StdoutMode.OFF,
                    generate_dashboard=True,
                    persist_report=True,
                ),
                run_path=run_path / "per_symbol" / run.symbol,
            ).run()

            print(
                f"   📊 report[{run.symbol}]"
                f" +{perf_counter() - t_sym:5.2f}s"
            )

        log("per_symbol_reports")

        # =====================
        # SUMMARY REPORT
        # =====================
        SummaryReportRunner(
            strategy_runs=self.strategy_runs,
            trades_by_run=self.trades_by_run,
            config=self.cfg,
            run_path=run_path,
        ).run()

        log("summary_report")

        print(f"🏁 Finished in {perf_counter() - t0:.2f}s")