import pandas as pd
from typing import Optional

from core.backtesting.engine.execution_loop import run_execution_loop
from core.domain.cost.cost_engine import TradeCostEngine
from core.backtesting.execution_policy import ExecutionPolicy
from core.domain.cost.instrument_ctx import build_instrument_ctx


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
        execution_policy: Optional[ExecutionPolicy] = None,
        cost_engine: Optional[TradeCostEngine] = None,
    ):
        self.execution_policy = execution_policy or ExecutionPolicy()
        self.cost_engine = cost_engine or TradeCostEngine(self.execution_policy)

    # ==================================================
    # MAIN API
    # ==================================================

    def run(
        self,
        *,
        signals_df: pd.DataFrame,
        trade_plans: pd.DataFrame,
    ) -> pd.DataFrame:

        if signals_df.empty or trade_plans.empty:
            return pd.DataFrame()

        self._validate_signals(signals_df)

        symbol = signals_df["symbol"].iloc[0]

        trades = self._simulate_trades(
            df=signals_df,
            plans=trade_plans,
            symbol=symbol,
        )

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
        *,
        df: pd.DataFrame,
        plans: pd.DataFrame,
        symbol: str,
    ) -> pd.DataFrame:

        instrument_ctx = build_instrument_ctx(symbol)

        trades = run_execution_loop(
            df=df,
            symbol=symbol,
            plans=plans,
            instrument_ctx=instrument_ctx,
        )

        if not trades:
            return pd.DataFrame()

        for trade in trades:
            self.cost_engine.apply(
                trade_dict=trade,
                df=df,
                ctx=instrument_ctx,
            )

        return pd.DataFrame(trades)
