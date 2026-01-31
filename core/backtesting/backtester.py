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
from core.domain.trade_factory import TradeFactory


@dataclass(frozen=True)
class InstrumentCtx:
    symbol: str
    point_size: float
    pip_value: float
    contract_size: float
    spread_abs: float
    half_spread: float
    slippage_abs: float


class Backtester:

    def __init__(self, slippage: float = 0.0, execution_policy: Optional[ExecutionPolicy] = None):
        self.slippage = slippage
        self.execution_policy = execution_policy or ExecutionPolicy()

    def run_backtest(self, df: pd.DataFrame, symbol: Optional[str] = None) -> pd.DataFrame:
        if symbol:
            return self._backtest_single_symbol(df, symbol)

        all_trades = []
        for sym, group_df in df.groupby("symbol"):
            trades = self._backtest_single_symbol(group_df, sym)
            if not trades.empty:
                all_trades.append(trades)

        return pd.concat(all_trades).sort_values(by="exit_time") if all_trades else pd.DataFrame()

    # -----------------------------
    # Context / Config
    # -----------------------------
    def _instrument_ctx(self, symbol: str) -> InstrumentCtx:
        meta = INSTRUMENT_META[symbol]
        point_size = float(meta["point"])
        pip_value = float(meta["pip_value"])
        contract_size = float(meta.get("contract_size", 1.0))

        spread_abs = get_spread_abs(symbol, point_size)
        half_spread = 0.5 * spread_abs

        # slippage in abs price units (kept consistent with your prior approach)
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
    # Dashboard fields helpers
    # -----------------------------
    def _attach_execution_types(self, trade_dict: dict, df: pd.DataFrame) -> None:
        exit_reason = trade_dict.get("exit_tag")
        has_exit_signal = "exit_signal" in df.columns

        # Hook: will be wired once exit_pos is available or time->index mapping is added
        exit_signal_value = False

        trade_dict.update({
            "exec_type_entry": self.execution_policy.entry_type,
            "exec_type_tp1": self.execution_policy.tp_type if trade_dict.get("tp1_time") is not None else None,
            "exec_type_exit": self.execution_policy.classify_exit_type(
                exit_reason=exit_reason,
                has_exit_signal=has_exit_signal,
                exit_signal_value=exit_signal_value,
            ),
        })

    def _attach_traded_volume(self, trade_dict: dict, ctx: InstrumentCtx) -> None:
        position_size = float(trade_dict["position_size"])

        entry_notional = float(trade_dict["entry_price"]) * position_size * ctx.contract_size

        tp1_executed = trade_dict.get("tp1_time") is not None
        exit_fraction = 0.5 if tp1_executed else 1.0

        exit_notional = float(trade_dict["exit_price"]) * position_size * ctx.contract_size * exit_fraction

        tp1_notional = 0.0
        if tp1_executed and trade_dict.get("tp1_price") is not None:
            tp1_notional = float(trade_dict["tp1_price"]) * position_size * ctx.contract_size * 0.5

        trade_dict.update({
            "traded_volume_usd_entry": entry_notional,
            "traded_volume_usd_tp1": tp1_notional,
            "traded_volume_usd_exit": exit_notional,
            "traded_volume_usd_total": entry_notional + tp1_notional + exit_notional,
        })

    def _attach_costs(self, trade_dict: dict, ctx: InstrumentCtx) -> None:
        position_size = float(trade_dict["position_size"])

        tp1_executed = trade_dict.get("tp1_time") is not None
        entry_fraction = 1.0
        tp1_fraction = 0.5 if tp1_executed else 0.0
        exit_fraction = 0.5 if tp1_executed else 1.0

        exec_entry = trade_dict.get("exec_type_entry") or EXEC_MARKET
        exec_exit = trade_dict.get("exec_type_exit") or EXEC_LIMIT

        # Spread costs: half spread per fill
        spread_usd_entry = price_abs_to_usd(ctx.half_spread, ctx.point_size, ctx.pip_value, position_size, entry_fraction)
        spread_usd_tp1 = price_abs_to_usd(ctx.half_spread, ctx.point_size, ctx.pip_value, position_size, tp1_fraction) if tp1_executed else 0.0
        spread_usd_exit = price_abs_to_usd(ctx.half_spread, ctx.point_size, ctx.pip_value, position_size, exit_fraction)

        # Slippage costs: only if market
        slip_usd_entry = price_abs_to_usd(ctx.slippage_abs, ctx.point_size, ctx.pip_value, position_size, entry_fraction) if exec_entry == EXEC_MARKET else 0.0
        slip_usd_tp1 = 0.0
        slip_usd_exit = price_abs_to_usd(ctx.slippage_abs, ctx.point_size, ctx.pip_value, position_size, exit_fraction) if exec_exit == EXEC_MARKET else 0.0

        trade_dict.update({
            "spread_usd_entry": spread_usd_entry,
            "spread_usd_tp1": spread_usd_tp1,
            "spread_usd_exit": spread_usd_exit,
            "spread_usd_total": spread_usd_entry + spread_usd_tp1 + spread_usd_exit,

            "slippage_usd_entry": slip_usd_entry,
            "slippage_usd_tp1": slip_usd_tp1,
            "slippage_usd_exit": slip_usd_exit,
            "slippage_usd_total": slip_usd_entry + slip_usd_tp1 + slip_usd_exit,

            "costs_usd_total": (spread_usd_entry + spread_usd_tp1 + spread_usd_exit) + (slip_usd_entry + slip_usd_tp1 + slip_usd_exit),
        })

    def _attach_net_pnl(self, trade_dict: dict) -> None:
        trade_dict["pnl_net_usd"] = float(trade_dict.get("pnl_usd", 0.0)) - float(trade_dict.get("costs_usd_total", 0.0))

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

                # dashboard fields
                self._attach_execution_types(trade_dict, df)
                self._attach_traded_volume(trade_dict, ctx)
                self._attach_costs(trade_dict, ctx)
                self._attach_net_pnl(trade_dict)

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
