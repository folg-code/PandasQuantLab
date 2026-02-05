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
    # PUBLIC API
    # ==================================================

    def run(
        self,
        *,
        df_signals: pd.DataFrame,
        symbol: str,
        window: str = "FULL",
        strategy_id: Optional[str] = None,
        strategy_name: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Run backtest for ONE (strategy, symbol, window).

        Returns:
            DataFrame with RAW trades.
        """

        if df_signals.empty:
            return pd.DataFrame()

        trades = self._run_single_symbol(
            df=df_signals,
            symbol=symbol,
        )

        if trades.empty:
            return trades

        # --------------------------------------------------
        # 🔑 ATTACH METADATA (CONTRACT)
        # --------------------------------------------------

        trades["symbol"] = symbol
        trades["window"] = window

        if strategy_id is not None:
            trades["strategy_id"] = strategy_id
        else:
            trades["strategy_id"] = type(self.strategy).__name__

        if strategy_name is not None:
            trades["strategy_name"] = strategy_name
        else:
            trades["strategy_name"] = type(self.strategy).__name__

        return trades.reset_index(drop=True)

    # ==================================================
    # INTERNAL
    # ==================================================

    def _run_single_symbol(
        self,
        *,
        df: pd.DataFrame,
        symbol: str,
    ) -> pd.DataFrame:

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
            self.cost_engine.enrich(
                trade_dict=trade,
                df=df,
                ctx=instrument_ctx,
            )

        return pd.DataFrame(trades)