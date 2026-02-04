from config.instrument_meta import FINANCING_RATES_PER_DAY, FINANCING_MODEL, FINANCING_USD_PER_LOT_DAY, \
    FX_TRIPLE_MULTIPLIER, FX_TRIPLE_ROLLOVER_WEEKDAY, FX_ROLLOVER_HOUR_UTC, FX_ROLLOVER_MINUTE_UTC, FINANCING_ENABLED
from core.domain.cost.instrument_ctx import InstrumentCtx
from core.domain.cost.time_utils import count_rollovers, to_dt


def attach_financing_costs(trade: dict, ctx: InstrumentCtx) -> None:
    trade["financing_usd_overnight"] = 0.0
    trade["financing_usd_weekend"] = 0.0
    trade["financing_usd_total"] = 0.0

    if not FINANCING_ENABLED:
        return

    entry_time = to_dt(trade["entry_time"])
    exit_time = to_dt(trade["exit_time"])

    rollovers = count_rollovers(entry_time, exit_time, FX_ROLLOVER_HOUR_UTC, FX_ROLLOVER_MINUTE_UTC)
    if not rollovers:
        return

    direction = trade.get("direction")
    if direction not in ("long", "short"):
        return

    overnight = 0.0
    weekend = 0.0

    triple_wd = FX_TRIPLE_ROLLOVER_WEEKDAY
    triple_mult = FX_TRIPLE_MULTIPLIER


    if FINANCING_MODEL == "usd_per_lot_day":
        sym = ctx.symbol
        rates = FINANCING_USD_PER_LOT_DAY.get(sym, {})
        usd_per_lot = float(rates.get(direction, 0.0))
        if usd_per_lot == 0.0:
            return

        lots = float(trade["position_size"])

        for t in rollovers:
            mult = triple_mult if t.weekday() == triple_wd else 1
            cost = lots * usd_per_lot * mult

            if mult > 1:
                overnight += lots * usd_per_lot
                weekend += lots * usd_per_lot * (mult - 1)
            else:
                overnight += cost

    # -----------------------------
    # MODEL: % OF NOTIONAL
    # -----------------------------
    elif FINANCING_MODEL == "notional_rate":
        sym_rates = FINANCING_RATES_PER_DAY.get(ctx.symbol)
        if not sym_rates:
            return

        rate_per_day = float(sym_rates.get(direction, 0.0))
        if rate_per_day == 0.0:
            return

        notional = float(trade.get("traded_volume_usd_entry", 0.0))
        if notional <= 0.0:
            notional = float(trade["entry_price"]) * float(trade["position_size"]) * float(
                ctx.contract_size)

        for t in rollovers:
            mult = triple_mult if t.weekday() == triple_wd else 1
            cost = notional * rate_per_day * mult

            if mult > 1:
                overnight += notional * rate_per_day
                weekend += notional * rate_per_day * (mult - 1)
            else:
                overnight += cost

    total = overnight + weekend

    trade["financing_usd_overnight"] = float(overnight)
    trade["financing_usd_weekend"] = float(weekend)
    trade["financing_usd_total"] = float(total)

    trade["costs_usd_total"] = float(trade.get("costs_usd_total", 0.0)) + float(total)