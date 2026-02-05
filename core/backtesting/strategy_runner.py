from dataclasses import dataclass
from typing import Any

import pandas as pd

from core.strategy.orchestration.strategy_execution import execute_strategy
from core.strategy.plan_builder import PlanBuildContext
from core.utils.timeframe import tf_to_minutes



@dataclass(frozen=True)
class StrategyRunResult:
    """
    Immutable result of running ONE strategy on ONE symbol.
    """

    symbol: str
    strategy_id: str
    strategy_name: str

    df_signals: pd.DataFrame     # execution contract
    df_context: pd.DataFrame

    trade_plans: pd.DataFrame
    report_spec: Any

def run_strategy_single(
    *,
    symbol: str,
    data_by_tf: dict[str, pd.DataFrame],
    strategy_cls,
    startup_candle_count: int,
):
    """
    Run single strategy instance for one symbol.

    Returns:
        StrategyRunResult

    Multiprocessing-safe.
    """

    # ==================================================
    # 1️⃣ BASE TIMEFRAME
    # ==================================================

    base_tf = min(data_by_tf.keys(), key=tf_to_minutes)
    df_base = data_by_tf[base_tf].copy()

    # ==================================================
    # 2️⃣ STRATEGY INIT
    # ==================================================

    strategy = strategy_cls(
        df=df_base,
        symbol=symbol,
        startup_candle_count=startup_candle_count,
    )
    strategy.validate()

    # ==================================================
    # 3️⃣ EXECUTION PIPELINE
    # ==================================================

    df_context = execute_strategy(
        strategy=strategy,
        df=df_base,
        data_by_tf=data_by_tf,
    ).copy()

    # ==================================================
    # 4️⃣ BUILD df_signals (EXECUTION CONTRACT)
    # ==================================================

    REQUIRED_COLUMNS = ["time", "open", "high", "low", "close"]
    SIGNAL_COLUMNS = ["signal_entry", "signal_exit", "levels"]

    missing = [c for c in REQUIRED_COLUMNS if c not in df_context.columns]
    if missing:
        raise RuntimeError(
            f"Strategy context missing required columns: {missing}"
        )

    df_signals = df_context[
        REQUIRED_COLUMNS +
        [c for c in SIGNAL_COLUMNS if c in df_context.columns]
    ].copy()

    # --- HARD GUARANTEES ---
    if "signal_entry" not in df_signals:
        df_signals["signal_entry"] = None
    if "signal_exit" not in df_signals:
        df_signals["signal_exit"] = None
    if "levels" not in df_signals:
        df_signals["levels"] = None

    df_signals["symbol"] = symbol

    # ==================================================
    # BUILD TRADE PLANS (STRATEGY RESPONSIBILITY)
    # ==================================================

    ctx = PlanBuildContext(
        symbol=symbol,
        strategy_name=strategy.get_strategy_name(),
        strategy_config=strategy.strategy_config,
    )

    trade_plans = strategy.build_trade_plans_backtest(
        df=df_signals,
        ctx=ctx,
        allow_managed_in_backtest=False,
    )


    return StrategyRunResult(
        symbol=symbol,
        strategy_id=strategy.get_strategy_id(),
        strategy_name=strategy.get_strategy_name(),
        df_signals=df_signals,
        df_context=df_context,
        trade_plans=trade_plans,
        report_spec=strategy.build_report_spec(),
    )
