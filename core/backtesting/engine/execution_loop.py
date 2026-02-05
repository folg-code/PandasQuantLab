import pandas as pd
from typing import Any

from config.backtest import INITIAL_BALANCE, MAX_RISK_PER_TRADE
from core.backtesting.exit.simulate_exit_numba import simulate_exit_numba
from core.backtesting.trade_factory import TradeFactory
from core.domain.cost.instrument_ctx import InstrumentCtx
from core.domain.execution.exit_processor import ExitProcessor
from core.domain.risk.sizing import position_size
from core.strategy.plan_builder import PlanBuildContext


def run_execution_loop(
    *,
    df: pd.DataFrame,
    symbol: str,
    plans: pd.DataFrame,
    instrument_ctx: InstrumentCtx,
) -> list[dict]:

    trades: list[dict] = []

    time_arr = df["time"].dt.tz_localize(None).values
    high_arr = df["high"].values
    low_arr = df["low"].values
    close_arr = df["close"].values

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

            sl = plan_sl[entry_pos]
            tp1 = plan_tp1[entry_pos]
            tp2 = plan_tp2[entry_pos]

            level_tags = {
                "SL": plan_sl_tag[entry_pos],
                "TP1": plan_tp1_tag[entry_pos],
                "TP2": plan_tp2_tag[entry_pos],
            }

            entry_price = float(close_arr[entry_pos])
            entry_price += (
                instrument_ctx.slippage_abs
                if direction == "long"
                else -instrument_ctx.slippage_abs
            )

            size = position_size(
                entry_price=entry_price,
                stop_price=sl,
                max_risk=MAX_RISK_PER_TRADE,
                account_size=INITIAL_BALANCE,
                point_size=instrument_ctx.point_size,
                pip_value=instrument_ctx.pip_value,
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
                instrument_ctx.slippage_abs,
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
                point_size=instrument_ctx.point_size,
                pip_value=instrument_ctx.pip_value,
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
                point_size=instrument_ctx.point_size,
                pip_value=instrument_ctx.pip_value,
                exit_result=exit_result,
                level_tags=level_tags,
            )

            trades.append(trade_dict)
            last_exit_by_tag[entry_tag] = exit_time

    return trades