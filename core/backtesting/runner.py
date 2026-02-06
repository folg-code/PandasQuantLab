import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

from config.logger_config import RunLogger, profiling
from config.report_config import ReportConfig, StdoutMode
from core.backtesting.backend_factory import create_backtest_backend
from core.backtesting.engine.backtester import Backtester
from core.backtesting.engine.worker import run_backtest_worker, run_strategy_worker
from core.backtesting.results_logic.metadata import BacktestMetadata
from core.backtesting.results_logic.result import BacktestResult
from core.backtesting.results_logic.store import ResultStore
from core.backtesting.strategy_runner import strategy_orchestration
from core.data_provider import BacktestStrategyDataProvider, CsvMarketDataCache
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

        self.strategy = None
        self.strategies = []

        self.signals_df: pd.DataFrame | None = None
        self.trades_df: pd.DataFrame | None = None

        self.log_run = RunLogger(
            "Run",
            self.cfg.LOGGER_CONFIG,
            prefix="🚀 RUN |"
        )
        self.log_data = RunLogger(
            "Data",
            self.cfg.LOGGER_CONFIG,
            prefix="📈 DATA |"
        )
        self.log_strategy = RunLogger(
            "Strategy",
            self.cfg.LOGGER_CONFIG,
            prefix="📐 STRATEGY |"
        )
        self.log_backtest = RunLogger(
            "Backtest",
            self.cfg.LOGGER_CONFIG,
            prefix="📊 BACKTEST |"
        )
        self.log_report = RunLogger(
            "Report",
            self.cfg.LOGGER_CONFIG,
            prefix="📄 REPORT |"
        )

    # ==================================================
    # 1️⃣ DATA LOADING
    # ==================================================

    def load_data(self) -> dict[str, dict[str, pd.DataFrame]]:
        self.log_data.log("start")

        strategy_cls = load_strategy_class(self.cfg.STRATEGY_CLASS)
        informative_tfs = strategy_cls.get_required_informatives()
        base_tf = self.cfg.TIMEFRAME
        all_tfs = [base_tf] + informative_tfs

        backend = create_backtest_backend(self.cfg.BACKTEST_DATA_BACKEND)

        start = pd.Timestamp(self.cfg.TIMERANGE["start"], tz="UTC")
        end = pd.Timestamp(self.cfg.TIMERANGE["end"], tz="UTC")

        self.provider = BacktestStrategyDataProvider(
            backend=backend,
            cache=CsvMarketDataCache(self.cfg.MARKET_DATA_PATH),
            backtest_start=start,
            backtest_end=end,
            required_timeframes=all_tfs,
            startup_candle_count=self.cfg.STARTUP_CANDLE_COUNT,
            logger=self.log_data,
        )

        all_data: dict[str, dict[str, pd.DataFrame]] = {}

        with self.log_data.time("load_all"):
            for symbol in self.cfg.SYMBOLS:
                all_data[symbol] = self.provider.fetch(symbol)

        self.log_data.log(
            f"summary | symbols={len(all_data)} timeframes={len(all_tfs)}"
        )

        return all_data
    # ==================================================
    # 2️⃣ STRATEGY EXECUTION
    # ==================================================

    def run_strategies(self, all_data):
        if self.cfg.USE_MULTIPROCESSING_STRATEGIES:
            return self.run_strategies_parallel(all_data)
        else:
            return self.run_strategies_single(all_data)

    def run_strategies_single(self, all_data) -> pd.DataFrame:
        self.log_strategy.log(f"start | symbols={len(all_data)}")

        strategy_cls = load_strategy_class(self.cfg.STRATEGY_CLASS)
        self.strategy_runs = []

        with self.log_strategy.time("execution"):
            for symbol, data_by_tf in all_data.items():
                with self.log_strategy.time(f"{symbol}"):
                    result = strategy_orchestration(
                        symbol=symbol,
                        data_by_tf=data_by_tf,
                        strategy_cls=strategy_cls,
                        startup_candle_count=self.cfg.STARTUP_CANDLE_COUNT,
                        logger=self.log_strategy,
                    )

                    if hasattr(result, "timing"):
                        t = result.timing
                        self.log_strategy.log(
                            f"{symbol:<8} | "
                            f"exec={t.get('execute_strategy', 0):.2f}s "
                            f"ind={t.get('execute.indicators', 0):.2f}s "
                            f"entry={t.get('execute.entry', 0):.2f}s "
                            f"exit={t.get('execute.exit', 0):.2f}s"
                        )

                self.strategy_runs.append(result)

        with self.log_strategy.time("aggregate"):
            self.signals_df = (
                pd.concat([r.df_signals for r in self.strategy_runs])
                .sort_values(["time", "symbol"])
                .reset_index(drop=True)
            )

        self.log_strategy.log("finished")
        return self.signals_df

    def run_strategies_parallel(self, all_data) -> pd.DataFrame:
        self.log_strategy.log(f"start parallel | symbols={len(all_data)}")

        strategy_cls = load_strategy_class(self.cfg.STRATEGY_CLASS)
        self.strategy_runs = []

        with self.log_strategy.time("parallel_execution"):
            with ProcessPoolExecutor() as executor:
                futures = [
                    executor.submit(
                        run_strategy_worker,
                        symbol=symbol,
                        data_by_tf=data_by_tf,
                        strategy_cls=strategy_cls,
                        startup_candle_count=self.cfg.STARTUP_CANDLE_COUNT,
                    )
                    for symbol, data_by_tf in all_data.items()
                ]
                for f in as_completed(futures):
                    self.strategy_runs.append(f.result())

        with self.log_strategy.time("aggregate"):
            self.signals_df = (
                pd.concat([r.df_signals for r in self.strategy_runs])
                .sort_values(["time", "symbol"])
                .reset_index(drop=True)
            )

        self.log_strategy.log("finished parallel")
        return self.signals_df

    # ==================================================
    # 3️⃣ BACKTEST
    # ==================================================

    def run_backtests(self) -> pd.DataFrame:
        if self.cfg.USE_MULTIPROCESSING_BACKTESTS:
            return self.run_backtests_parallel()
        else:
            return self.run_backtests_single()

    def run_backtests_single(self) -> pd.DataFrame:
        self.log_backtest.log("start")

        self.trades_by_run = []

        with self.log_backtest.time("execution"):
            for run in self.strategy_runs:
                backtester = Backtester()
                trades = backtester.run(
                    signals_df=run.df_signals,
                    trade_plans=run.trade_plans,
                )
                self.trades_by_run.append(trades)
                self.log_backtest.log(
                    f"{run.symbol:<8} | trades={len(trades)}"
                )

        self.trades_df = (
            pd.concat(self.trades_by_run)
            .sort_values("exit_time")
            .reset_index(drop=True)
        )

        self.log_backtest.log(
            f"summary | total_trades={len(self.trades_df)}"
        )
        return self.trades_df

    def run_backtests_parallel(self) -> pd.DataFrame:
        if not self.strategy_runs:
            raise RuntimeError("No strategy runs to backtest")

        self.trades_by_run = []
        max_workers = self.cfg.MAX_WORKERS_BACKTESTS
        workers = max_workers or os.cpu_count()

        self.log_backtest.log(
            f"start parallel | runs={len(self.strategy_runs)} workers={workers}"
        )

        with self.log_backtest.time("parallel_execution"):
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                future_to_run = {
                    executor.submit(
                        run_backtest_worker,
                        signals_df=run.df_signals,
                        trade_plans=run.trade_plans,
                    ): run
                    for run in self.strategy_runs
                }

                for future in as_completed(future_to_run):
                    run = future_to_run[future]
                    trades = future.result()

                    self.trades_by_run.append(trades)

                    self.log_backtest.log(
                        f"{run.symbol:<8} | trades={len(trades)}"
                    )

        # -----------------------------
        # AGGREGATE
        # -----------------------------
        with self.log_backtest.time("aggregate"):
            self.trades_df = (
                pd.concat(self.trades_by_run)
                .sort_values("exit_time")
                .reset_index(drop=True)
            )

        self.log_backtest.log(
            f"summary | total_trades={len(self.trades_df)}"
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
        self.run_path = Path(
            f"results/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.run_path.mkdir(parents=True, exist_ok=True)

        self.log_run.log(f"run_path={self.run_path}")
        self.log_run.log("start")

        with self.log_run.time("data"):
            all_data = self.load_data()

        with self.log_run.time("strategy"):
            self.run_strategies(all_data)

        with profiling(self.cfg.PROFILING, self.run_path / "profile.prof"):
            with self.log_run.time("backtest"):
                self.run_backtests()

        with self.log_run.time("persist"):
            result = self._build_result()
            run_path = ResultStore().save(result)

        for run, trades in zip(self.strategy_runs, self.trades_by_run):
            with self.log_report.time(f"{run.symbol}"):
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

        with self.log_report.time("summary"):
            SummaryReportRunner(
                strategy_runs=self.strategy_runs,
                trades_by_run=self.trades_by_run,
                config=self.cfg,
                run_path=run_path,
            ).run()

        self.log_run.log("finished")
