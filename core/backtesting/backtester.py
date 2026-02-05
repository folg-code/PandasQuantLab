import traceback
from typing import Optional, Any
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

from config.backtest import INITIAL_BALANCE, SLIPPAGE, MAX_RISK_PER_TRADE
from config.instrument_meta import INSTRUMENT_META, get_spread_abs

from core.backtesting.execution_policy import ExecutionPolicy
from core.backtesting.simulate_exit_numba import simulate_exit_numba

from core.domain.execution.exit_processor import ExitProcessor
from core.domain.cost.cost_engine import TradeCostEngine, InstrumentCtx
from core.backtesting.trade_factory import TradeFactory
from core.domain.risk.sizing import position_size
from core.strategy.plan_builder import  PlanBuildContext


class Backtester:
    def __init__(self,
                 strategy,
                 execution_policy: Optional[ExecutionPolicy] = None,
                 cost_engine: Optional[TradeCostEngine] = None
                 ):
        self.strategy = strategy
        self.execution_policy = execution_policy or ExecutionPolicy()
        self.cost_engine = cost_engine or TradeCostEngine(self.execution_policy)

    def run_backtest(self, df: pd.DataFrame, symbol: Optional[str] = None) -> pd.DataFrame:
        if symbol:
            return self._backtest_single_symbol(df, symbol)

        all_trades = []
        for sym, group_df in df.groupby("symbol"):
            trades = self._backtest_single_symbol(group_df, sym)
            if not trades.empty:
                all_trades.append(trades)

        return pd.concat(all_trades).sort_values(by="exit_time") if all_trades else pd.DataFrame()

    @staticmethod
    def _instrument_ctx(symbol: str) -> InstrumentCtx:
        meta = INSTRUMENT_META[symbol]
        point_size = float(meta["point"])
        pip_value = float(meta["pip_value"])
        contract_size = float(meta.get("contract_size", 1.0))

        spread_abs = get_spread_abs(symbol, point_size)
        half_spread = 0.5 * spread_abs

        slippage_abs = float(SLIPPAGE) * point_size

        return InstrumentCtx(
            symbol=symbol,
            point_size=point_size,
            pip_value=pip_value,
            contract_size=contract_size,
            spread_abs=spread_abs,
            half_spread=half_spread,
            slippage_abs=slippage_abs,
        )

    # -----------------------------
    # Backtest per symbol
    # -----------------------------
    def _backtest_single_symbol(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        trades = []

        time_arr = df["time"].dt.tz_localize(None).values
        high_arr = df["high"].values
        low_arr = df["low"].values
        close_arr = df["close"].values

        # instrument ctx do slippage itp.
        ctx_inst = self._instrument_ctx(symbol)

        # 1) Build vector-friendly plans once (shared logic)
        ctx = PlanBuildContext(
            symbol=symbol,
            strategy_name=type(self.strategy).__name__,
            strategy_config=self.strategy.strategy_config,
        )
        plans = self.strategy.build_trade_plans_backtest(df=df, ctx=ctx, allow_managed_in_backtest=False)

        # 2) Precompute arrays used in the hot loop
        plan_valid = plans["plan_valid"].values
        plan_dir = plans["plan_direction"].values
        plan_tag = plans["plan_entry_tag"].values
        plan_sl = plans["plan_sl"].values.astype(float)
        plan_tp1 = plans["plan_tp1"].values.astype(float)
        plan_tp2 = plans["plan_tp2"].values.astype(float)

        plan_sl_tag = plans["plan_sl_tag"].values.astype(str)
        plan_tp1_tag = plans["plan_tp1_tag"].values.astype(str)
        plan_tp2_tag = plans["plan_tp2_tag"].values.astype(str)

        n = len(df)

        for direction in ("long", "short"):
            dir_flag = 1 if direction == "long" else -1
            last_exit_by_tag: dict[str, Any] = {}

            for entry_pos in range(n):
                if not plan_valid[entry_pos]:
                    continue
                if plan_dir[entry_pos] != direction:
                    continue

                entry_tag = str(plan_tag[entry_pos])
                entry_time = time_arr[entry_pos]

                last_exit = last_exit_by_tag.get(entry_tag)
                if last_exit is not None and last_exit > entry_time:
                    continue

                sl = float(plan_sl[entry_pos])
                tp1 = float(plan_tp1[entry_pos])
                tp2 = float(plan_tp2[entry_pos])

                level_tags = {"SL": plan_sl_tag[entry_pos], "TP1": plan_tp1_tag[entry_pos], "TP2": plan_tp2_tag[entry_pos]}

                entry_price = float(close_arr[entry_pos])

                entry_price += ctx_inst.slippage_abs if direction == "long" else -ctx_inst.slippage_abs

                size = position_size(
                    entry_price=entry_price,
                    stop_price=sl,
                    max_risk=MAX_RISK_PER_TRADE,
                    account_size=INITIAL_BALANCE,   # lub INITIAL_BALANCE
                    point_size=ctx_inst.point_size,
                    pip_value=ctx_inst.pip_value,
                )

                (
                    exit_price,
                    exit_time,
                    exit_code,
                    tp1_exec,
                    tp1_price,
                    tp1_time,
                ) = simulate_exit_numba(
                    dir_flag,
                    entry_pos,
                    entry_price,
                    sl,
                    tp1,
                    tp2,
                    high_arr,
                    low_arr,
                    close_arr,
                    time_arr,
                    ctx_inst.slippage_abs,
                )

                exit_result = ExitProcessor.process(
                    direction=direction,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    exit_time=exit_time,
                    exit_code=exit_code,
                    tp1_executed=tp1_exec,
                    tp1_price=tp1_price,
                    tp1_time=tp1_time,
                    sl=sl,
                    tp1=tp1,
                    tp2=tp2,
                    position_size=size,
                    point_size=ctx_inst.point_size,
                    pip_value=ctx_inst.pip_value,
                )



                trade_dict = TradeFactory.create_trade(
                    symbol=symbol,
                    direction=direction,
                    entry_time=entry_time,
                    entry_price=entry_price,
                    entry_tag=entry_tag,
                    position_size=size,
                    sl=sl,
                    tp1=tp1,
                    tp2=tp2,
                    point_size=ctx_inst.point_size,
                    pip_value=ctx_inst.pip_value,
                    exit_result=exit_result,
                    level_tags=level_tags,
                )

                self.cost_engine.enrich(trade_dict, df=df, ctx=ctx_inst)

                trades.append(trade_dict)
                last_exit_by_tag[entry_tag] = exit_time

        print(f"✅ Finished backtest for {symbol}, {len(trades)} trades.")
        return pd.DataFrame(trades)

    # -----------------------------
    # Parallel run (legacy)
    # -----------------------------
    def run(self) -> pd.DataFrame:
        if getattr(self, "symbol", None) is not None:
            return self._backtest_single_symbol(self.df, self.symbol)

        all_trades = []
        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = []
            for sym, group_df in self.df.groupby("symbol"):
                futures.append(executor.submit(self._backtest_single_symbol, group_df.copy(), sym))

            for future in as_completed(futures):
                try:
                    trades = future.result()
                    all_trades.append(trades)
                except Exception as e:
                    print(f"❌ Błąd w backteście: {e}")
                    traceback.print_exc()

        return pd.concat(all_trades).sort_values(by="exit_time") if all_trades else pd.DataFrame()
