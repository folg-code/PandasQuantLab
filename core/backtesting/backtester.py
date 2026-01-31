import traceback
from dataclasses import dataclass
from typing import  Optional
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

from config.backtest import INITIAL_BALANCE, SLIPPAGE, MAX_RISK_PER_TRADE
from config.instrument_meta import INSTRUMENT_META, get_spread_abs, price_abs_to_usd

from core.backtesting.execution_policy import ExecutionPolicy, EXEC_MARKET, EXEC_LIMIT
from core.backtesting.simulate_exit_numba import simulate_exit_numba
from core.domain.risk import position_sizer_fast
from core.domain.exit_processor import ExitProcessor
from core.domain.trade_cost_engine import TradeCostEngine, InstrumentCtx
from core.domain.trade_factory import TradeFactory


class Backtester:
    def __init__(self,
                 slippage: float = 0.0,
                 execution_policy: Optional[ExecutionPolicy] = None,
                 cost_engine: Optional[TradeCostEngine] = None
                 ):
        self.slippage = slippage
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

        df = df.copy()
        df["time"] = df["time"].dt.tz_localize(None)

        high_arr = df["high"].values
        low_arr = df["low"].values
        close_arr = df["close"].values
        time_arr = df["time"].values

        signal_arr = df["signal_entry"].values
        levels_arr = df["levels"].values

        ctx = self._instrument_ctx(symbol)
        point_size = ctx.point_size
        pip_value = ctx.pip_value

        n = len(df)

        for direction in ("long", "short"):
            dir_flag = 1 if direction == "long" else -1
            last_exit_by_tag = {}

            for entry_pos in range(n):
                sig = signal_arr[entry_pos]
                if not isinstance(sig, dict) or sig.get("direction") != direction:
                    continue

                entry_tag = sig["tag"]
                entry_time = time_arr[entry_pos]

                last_exit = last_exit_by_tag.get(entry_tag)
                if last_exit is not None and last_exit > entry_time:
                    continue

                levels = levels_arr[entry_pos]
                if not isinstance(levels, dict):
                    continue

                sl = (levels.get("SL") or levels.get(0))["level"]
                tp1 = (levels.get("TP1") or levels.get(1))["level"]
                tp2 = (levels.get("TP2") or levels.get(2))["level"]

                level_tags = {
                    "SL": (levels.get("SL") or levels.get(0))["tag"],
                    "TP1": (levels.get("TP1") or levels.get(1))["tag"],
                    "TP2": (levels.get("TP2") or levels.get(2))["tag"],
                }

                entry_price = float(close_arr[entry_pos])

                # legacy behavior: entry slippage on exec price (kept as-is)
                entry_price += ctx.slippage_abs if direction == "long" else -ctx.slippage_abs

                position_size = position_sizer_fast(
                    entry_price,
                    sl,
                    max_risk=MAX_RISK_PER_TRADE,
                    account_size=INITIAL_BALANCE,
                    point_size=point_size,
                    pip_value=pip_value,
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
                    ctx.slippage_abs,
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
                    position_size=position_size,
                    point_size=point_size,
                    pip_value=pip_value,
                )

                trade_dict = TradeFactory.create_trade(
                    symbol=symbol,
                    direction=direction,
                    entry_time=entry_time,
                    entry_price=entry_price,
                    entry_tag=entry_tag,
                    position_size=position_size,
                    sl=sl,
                    tp1=tp1,
                    tp2=tp2,
                    point_size=point_size,
                    pip_value=pip_value,
                    exit_result=exit_result,
                    level_tags=level_tags,
                )

                self.cost_engine.enrich(trade_dict, df=df, ctx=ctx)

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
