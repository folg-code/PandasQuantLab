import pandas as pd
from typing import Optional

from core.backtesting.engine.execution_loop import run_execution_loop
from core.domain.cost.cost_engine import TradeCostEngine
from core.backtesting.execution_policy import ExecutionPolicy
from core.domain.cost.instrument_ctx import build_instrument_ctx
from core.strategy.plan_builder import PlanBuildContext


class Backtester:
    """
    Pure backtesting engine.

    Responsibilities:
    - execute ONE strategy
    - on ONE symbol
    - over ONE dataframe slice
    - return RAW trades (no equity, no analytics)

    Does NOT:
    - aggregate symbols
    - handle windows
    - compute equity
    - know about reports
    """

    def __init__(
        self,
        *,
        strategy,
        execution_policy: Optional[ExecutionPolicy] = None,
        cost_engine: Optional[TradeCostEngine] = None,
    ):
        self.strategy = strategy
        self.execution_policy = execution_policy or ExecutionPolicy()
        self.cost_engine = cost_engine or TradeCostEngine(self.execution_policy)

    # ==================================================
    # MAIN API
    # ==================================================

    def run(self, signals_df: pd.DataFrame) -> pd.DataFrame:
        """
        Execute backtest on provided signals dataframe.

        Returns:
            pd.DataFrame with RAW trades (no equity, no analytics)
        """
        if signals_df.empty:
            return pd.DataFrame()

        # --- validate ---
        self._validate_signals(signals_df)

        # --- core execution ---
        trades = self._simulate_trades(signals_df)

        if trades.empty:
            return trades


        return trades

    # ==================================================
    # INTERNAL
    # ==================================================

    def _validate_signals(self, df: pd.DataFrame):
        required = {"time", "symbol", "signal_entry"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing signal columns: {missing}")

    def _simulate_trades(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:

        symbol = df["symbol"].iloc[0] if "symbol" in df.columns else self.strategy.symbol

        # -----------------------------
        # 1️⃣ Instrument context
        # -----------------------------
        instrument_ctx = build_instrument_ctx(symbol)

        # -----------------------------
        # 2️⃣ Strategy → trade plans
        # -----------------------------
        ctx = PlanBuildContext(
            symbol=symbol,
            strategy_name=type(self.strategy).__name__,
            strategy_config=self.strategy.strategy_config,
        )

        plans = self.strategy.build_trade_plans_backtest(
            df=df,
            ctx=ctx,
            allow_managed_in_backtest=False,
        )

        if plans.empty:
            return pd.DataFrame()

        # -----------------------------
        # 3️⃣ Execution loop (HOT PATH)
        # -----------------------------
        trades = run_execution_loop(
            df=df,
            symbol=symbol,
            strategy=self.strategy,
            plans=plans,
            instrument_ctx=instrument_ctx,
        )

        if not trades:
            return pd.DataFrame()

        # -----------------------------
        # 4️⃣ Cost enrichment (still RAW)
        # -----------------------------
        for trade in trades:
            self.cost_engine.apply(
                trade_dict=trade,
                df=df,
                ctx=instrument_ctx,
            )

        return pd.DataFrame(trades)