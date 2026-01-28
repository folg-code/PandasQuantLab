import os
from time import perf_counter

import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed


from core.data_provider.backend_factory import create_backtest_backend
from core.data_provider.default_provider import DefaultOhlcvDataProvider
from core.data_provider.cache import MarketDataCache

from core.backtesting.backtester import Backtester
from core.backtesting.raporter import BacktestReporter
from core.backtesting.plotting.plot import TradePlotter
from core.strategy.runner import run_strategy_single
from core.strategy.strategy_loader import load_strategy_class


class BacktestRunner:

    def __init__(self, cfg):
        self.config = cfg
        self.provider = None
        self.strategies = []
        self.signals_df = None
        self.trades_df = None

    # ==================================================
    # 1️⃣ LOAD DATA ONCE (FULL RANGE, MAIN TF)
    # ==================================================

    def load_data(self):

        t_start = perf_counter()
        print("⏱️ load_data | start")

        # -------------------------------------------------
        # BACKEND
        # -------------------------------------------------
        t0 = perf_counter()
        backend = create_backtest_backend(self.config.BACKTEST_DATA_BACKEND)
        print(f"⏱️ load_data | create_backend        {perf_counter() - t0:8.3f}s")

        # -------------------------------------------------
        # TIME RANGE
        # -------------------------------------------------
        t0 = perf_counter()
        start = pd.Timestamp(self.config.TIMERANGE["start"], tz="UTC")
        end = pd.Timestamp(self.config.TIMERANGE["end"], tz="UTC")
        print(f"⏱️ load_data | build_timerange       {perf_counter() - t0:8.3f}s")

        # -------------------------------------------------
        # PROVIDER
        # -------------------------------------------------
        t0 = perf_counter()
        self.provider = DefaultOhlcvDataProvider(
            backend=backend,
            cache=MarketDataCache(self.config.MARKET_DATA_PATH),
            backtest_start=start,
            backtest_end=end,
        )
        print(f"⏱️ load_data | init_provider         {perf_counter() - t0:8.3f}s")

        # -------------------------------------------------
        # LOAD SYMBOLS
        # -------------------------------------------------
        all_data = {}

        for symbol in self.config.SYMBOLS:
            t_sym = perf_counter()

            df = self.provider.get_ohlcv(
                symbol=symbol,
                timeframe=self.config.TIMEFRAME,
                start=start,
                end=end,
            )

            dt = perf_counter() - t_sym
            print(
                f"⏱️ load_data | get_ohlcv {symbol:<10} "
                f"{dt:8.3f}s  ({len(df)} rows)"
            )

            all_data[symbol] = df

        # -------------------------------------------------
        # TOTAL
        # -------------------------------------------------
        total = perf_counter() - t_start
        print(f"⏱️ load_data | TOTAL                  {total:8.3f}s")

        return all_data

    # ==================================================
    # 2️⃣ RUN STRATEGIES (PARALLEL)
    # ==================================================
    def run_strategies_parallel(self, all_data: dict):

        t_start = perf_counter()
        n_symbols = len(all_data)

        print(f"📈 STRATEGIES | start ({n_symbols} symbols)")


        all_signals = []
        self.strategies = []

        # =================================================
        # 🔥 OPCJA A — JEDEN SYMBOL → BEZ MULTIPROCESSING
        # =================================================
        if n_symbols == 1:
            symbol, df = next(iter(all_data.items()))

            print("📈 STRATEGIES | single-symbol mode (no multiprocessing)"
                    f"{perf_counter() - t_start:8.3f}s ")

            t0 = perf_counter()
            df_signals, strategy = run_strategy_single(
                symbol,
                df,
                self.provider,
                load_strategy_class(self.config.STRATEGY_CLASS),
                self.config.STARTUP_CANDLE_COUNT,
            )
            print(
                f"📈 STRATEGIES | finished job         "
                f"{perf_counter() - t0:8.3f}s  ({symbol})"
            )

            all_signals.append(df_signals)
            self.strategies.append(strategy)

        # =================================================
        # 🚀 MULTI-SYMBOL → MULTIPROCESSING
        # =================================================
        else:
            t_submit = perf_counter()

            with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
                futures = [
                    executor.submit(
                        run_strategy_single,
                        symbol,
                        df,
                        self.provider,
                        load_strategy_class(self.config.STRATEGY_CLASS),
                        self.config.STARTUP_CANDLE_COUNT,
                    )
                    for symbol, df in all_data.items()
                ]

                print(
                    f"📈 STRATEGIES | submit_jobs           "
                    f"{perf_counter() - t_submit:8.3f}s  "
                    f"({len(futures)} symbols)"
                )

                for future in as_completed(futures):
                    df_signals, strategy = future.result()

                    print(
                        f"📈 STRATEGIES | job collected         "
                        f"(symbol={strategy.symbol})"
                    )

                    all_signals.append(df_signals)
                    self.strategies.append(strategy)

        # =================================================
        # MERGE RESULTS
        # =================================================
        if not all_signals:
            raise RuntimeError("Brak sygnałów ze strategii")

        t_merge = perf_counter()
        self.signals_df = (
            pd.concat(all_signals)
            .sort_values(by=["time", "symbol"])
            .reset_index(drop=True)
        )

        print(
            f"📈 STRATEGIES | merge_results         "
            f"{perf_counter() - t_merge:8.3f}s"
        )

        # =================================================
        # TOTAL
        # =================================================
        total = perf_counter() - t_start
        print(f"📈 STRATEGIES | TOTAL                 {total:8.3f}s")

        return self.signals_df

    # ==================================================
    # 3️⃣ BACKTEST SINGLE WINDOW
    # ==================================================
    def _run_backtest_window(self, start, end, label):

        df_slice = self.signals_df[
            (self.signals_df["time"] >= start) &
            (self.signals_df["time"] <= end)
        ].copy()

        if df_slice.empty:
            raise RuntimeError(f"No signals in window: {label}")

        backtester = Backtester(slippage=self.config.SLIPPAGE)
        trades = backtester.run_backtest(df_slice)

        trades["window"] = label
        return trades

    # ==================================================
    # 4️⃣ RUN BACKTEST(S)
    # ==================================================
    def run_backtests(self):

        if self.config.BACKTEST_MODE == "single":

            start = pd.Timestamp(self.config.TIMERANGE["start"], tz="UTC")
            end = pd.Timestamp(self.config.TIMERANGE["end"], tz="UTC")

            self.trades_df = self._run_backtest_window(
                start, end, label="FULL"
            )

        elif self.config.BACKTEST_MODE == "split":

            all_trades = []

            for name, (start, end) in self.config.BACKTEST_WINDOWS.items():
                trades = self._run_backtest_window(
                    pd.Timestamp(start, tz="UTC"),
                    pd.Timestamp(end, tz="UTC"),
                    label=name
                )
                all_trades.append(trades)

            self.trades_df = (
                pd.concat(all_trades)
                  .sort_values(by=["exit_time", "symbol"])
                  .reset_index(drop=True)
            )

        else:
            raise ValueError(
                f"Unknown BACKTEST_MODE: {self.config.BACKTEST_MODE}"
            )

        if self.trades_df.empty:
            raise RuntimeError("Brak transakcji po backteście")

        return self.trades_df

    # ==================================================
    # 5️⃣ REPORTING
    # ==================================================
    def run_report(self):

        reporter = BacktestReporter(
            trades=self.trades_df,
            signals=self.signals_df,
            initial_balance=self.config.INITIAL_BALANCE,
        )

        reporter.run()

    # ==================================================
    # 6️⃣ PLOTTING
    # ==================================================
    def plot_results(self):

        plots_folder = "results/plots"
        os.makedirs(plots_folder, exist_ok=True)

        for strategy in self.strategies:
            symbol = strategy.symbol

            # ==========================
            # PLOT-ONLY MODE
            # ==========================
            if self.trades_df is None:
                trades_symbol = None
            else:
                trades_symbol = self.trades_df[
                    self.trades_df["symbol"] == symbol
                    ]

                if trades_symbol.empty:
                    trades_symbol = None

            plotter = TradePlotter(
                df=strategy.df_plot,
                trades=trades_symbol,
                bullish_zones=strategy.get_bullish_zones(),
                bearish_zones=strategy.get_bearish_zones(),
                extra_series=strategy.get_extra_values_to_plot(),
                bool_series=strategy.bool_series(),
                title=f"{symbol} chart",
            )

            plotter.plot()
            plotter.save(f"{plots_folder}/{symbol}.png")

    # ==================================================
    # 7️⃣ MAIN RUN
    # ==================================================
    def run(self):

        t_start = perf_counter()
        print("🚀 Runner start")

        # ============================
        # LOAD DATA
        # ============================
        all_data = self.load_data()

        # ============================📈🎯
        # STRATEGIES (PARALLEL)
        # ============================
        self.run_strategies_parallel(all_data)

        # ============================
        # PLOT ONLY
        # ============================
        if self.config.PLOT_ONLY:
            t = perf_counter()
            self.plot_results()
            print(f"⏱ plot_results         {perf_counter() - t:.3f}s")
            print(f"📊 Plot-only finished   TOTAL {perf_counter() - t_start:.3f}s")
            return

        # ============================
        # BACKTEST
        # ============================
        t = perf_counter()
        print(f"⏱ START BACKTEST  ")
        self.run_backtests()
        print(f"⏱ BACKTEST CALCULATION TIME        {perf_counter() - t:.3f}s")

        if self.config.BACKTEST_MODE == "backtest":
            print(f"🧪 Backtest finished    TOTAL {perf_counter() - t_start:.3f}s")
            return

        # ============================
        # REPORT
        # ============================
        #t = perf_counter()
        #self.run_report()
        #print(f"⏱ run_report           {perf_counter() - t:.3f}s")

        print(f"🏁 Full run finished    TOTAL {perf_counter() - t_start:.3f}s")
        # ============================
        # FINAL PLOT
        # ============================
       # t = perf_counter()
       # self.plot_results()
        #print(f"⏱ plot_results         {perf_counter() - t:.3f}s")

        # ============================
        # TOTAL
        # ============================
        #print(f"🏁 Full run finished    TOTAL {perf_counter() - t_start:.3f}s")
