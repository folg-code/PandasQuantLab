from core.domain.cost.instrument_ctx import InstrumentCtx


def attach_traded_volume(trade: dict, ctx: InstrumentCtx) -> None:
    size = float(trade["position_size"])

    entry = trade["entry_price"] * size * ctx.contract_size
    tp1_exec = trade.get("tp1_time") is not None
    exit_frac = 0.5 if tp1_exec else 1.0

    exit_notional = trade["exit_price"] * size * ctx.contract_size * exit_frac

    tp1_notional = 0.0
    if tp1_exec and trade.get("tp1_price") is not None:
        tp1_notional = trade["tp1_price"] * size * ctx.contract_size * 0.5

    trade["traded_volume_usd_entry"] = entry
    trade["traded_volume_usd_tp1"] = tp1_notional
    trade["traded_volume_usd_exit"] = exit_notional
    trade["traded_volume_usd_total"] = entry + tp1_notional + exit_notional