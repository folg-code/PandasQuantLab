from core.backtesting.execution_policy import EXEC_MARKET, EXEC_LIMIT
from core.domain.cost.pricing import price_abs_to_usd
from core.domain.cost.instrument_ctx import InstrumentCtx


def attach_execution_costs(trade: dict, ctx: InstrumentCtx) -> None:
    size = float(trade["position_size"])
    tp1_exec = trade.get("tp1_time") is not None

    entry_frac = 1.0
    tp1_frac = 0.5 if tp1_exec else 0.0
    exit_frac = 0.5 if tp1_exec else 1.0

    exec_entry = trade.get("exec_type_entry") or EXEC_MARKET
    exec_exit = trade.get("exec_type_exit") or EXEC_LIMIT

    spread_entry = price_abs_to_usd(ctx.half_spread, ctx.point_size, ctx.pip_value, size, entry_frac)
    spread_tp1 = price_abs_to_usd(ctx.half_spread, ctx.point_size, ctx.pip_value, size, tp1_frac)
    spread_exit = price_abs_to_usd(ctx.half_spread, ctx.point_size, ctx.pip_value, size, exit_frac)

    slip_entry = price_abs_to_usd(ctx.slippage_abs, ctx.point_size, ctx.pip_value, size, entry_frac) if exec_entry == EXEC_MARKET else 0.0
    slip_exit = price_abs_to_usd(ctx.slippage_abs, ctx.point_size, ctx.pip_value, size, exit_frac) if exec_exit == EXEC_MARKET else 0.0

    trade["spread_usd_total"] = spread_entry + spread_tp1 + spread_exit
    trade["slippage_usd_total"] = slip_entry + slip_exit
    trade["costs_usd_total"] = trade["spread_usd_total"] + trade["slippage_usd_total"]