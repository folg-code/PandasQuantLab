from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from config.instrument_meta import FX_TRIPLE_ROLLOVER_WEEKDAY, FX_TRIPLE_MULTIPLIER, FX_ROLLOVER_HOUR_UTC, \
    FX_ROLLOVER_MINUTE_UTC, FINANCING_ENABLED, FINANCING_MODEL, FINANCING_USD_PER_LOT_DAY, FINANCING_RATES_PER_DAY
from core.backtesting.execution_policy import EXEC_MARKET, EXEC_LIMIT


def _to_dt(x) -> datetime:
    if hasattr(x, "to_pydatetime"):
        return x.to_pydatetime()
    if isinstance(x, datetime):
        return x
    return datetime.fromisoformat(str(x))


def _rollover_anchor(dt: datetime, hour: int, minute: int) -> datetime:
    return dt.replace(hour=hour, minute=minute, second=0, microsecond=0)


def count_rollovers(entry_time: datetime, exit_time: datetime, hour: int, minute: int) -> list[datetime]:
    """
    Returns rollover timestamps (UTC) strictly after entry_time and <= exit_time.
    """
    if exit_time <= entry_time:
        return []

    t = _rollover_anchor(entry_time, hour, minute)
    if t <= entry_time:
        t += timedelta(days=1)

    out = []
    while t <= exit_time:
        out.append(t)
        t += timedelta(days=1)
    return out


def price_abs_to_usd(price_abs: float, point_size: float, pip_value: float, position_size: float, fraction: float) -> float:
    if fraction <= 0.0:
        return 0.0
    pips = float(price_abs) / float(point_size)
    return float(pips) * float(pip_value) * float(position_size) * float(fraction)


@dataclass(frozen=True)
class InstrumentCtx:
    symbol: str
    point_size: float
    pip_value: float
    contract_size: float
    spread_abs: float
    half_spread: float
    slippage_abs: float


class TradeCostEngine:
    """
    Single responsibility:
      - enrich trade_dict with execution types, traded volume, spread/slippage costs,
        financing (overnight/weekend), and pnl_net_usd.

    It does NOT change entry/exit prices. It's an accounting overlay.
    """

    def __init__(self, execution_policy):
        self.execution_policy = execution_policy


    def enrich(self, trade_dict: dict, *, df, ctx: InstrumentCtx) -> None:
        self._attach_execution_types(trade_dict, df=df)
        self._attach_traded_volume(trade_dict, ctx)
        self._attach_spread_slippage_costs(trade_dict, ctx)
        self._attach_financing_costs(trade_dict, ctx)
        self._attach_net_pnl(trade_dict)


    def _attach_execution_types(self, trade_dict: dict, *, df) -> None:
        exit_reason = trade_dict.get("exit_tag")
        exit_signal_col = getattr(self.execution_policy, "exit_signal_column", "exit_signal")

        has_exit_signal = bool(df is not None and exit_signal_col in df.columns)

        # IMPORTANT:
        # Per-trade exit-by-signal should come from simulation.
        # For now: always False, until  EXIT_SIGNAL implemented.
        exit_signal_value = bool(trade_dict.get("exit_by_signal", False))

        trade_dict["exec_type_entry"] = self.execution_policy.entry_type
        trade_dict["exec_type_tp1"] = self.execution_policy.tp_type if trade_dict.get("tp1_time") is not None else None
        trade_dict["exec_type_exit"] = self.execution_policy.classify_exit_type(
            exit_reason=exit_reason,
            has_exit_signal=has_exit_signal,
            exit_signal_value=exit_signal_value,
        )

    @staticmethod
    def _attach_traded_volume(trade_dict: dict, ctx: InstrumentCtx) -> None:
        position_size = float(trade_dict["position_size"])

        entry_notional = float(trade_dict["entry_price"]) * position_size * float(ctx.contract_size)

        tp1_executed = trade_dict.get("tp1_time") is not None
        exit_fraction = 0.5 if tp1_executed else 1.0

        exit_notional = float(trade_dict["exit_price"]) * position_size * float(ctx.contract_size) * exit_fraction

        tp1_notional = 0.0
        if tp1_executed and trade_dict.get("tp1_price") is not None:
            tp1_notional = float(trade_dict["tp1_price"]) * position_size * float(ctx.contract_size) * 0.5

        trade_dict["traded_volume_usd_entry"] = float(entry_notional)
        trade_dict["traded_volume_usd_tp1"] = float(tp1_notional)
        trade_dict["traded_volume_usd_exit"] = float(exit_notional)
        trade_dict["traded_volume_usd_total"] = float(entry_notional + tp1_notional + exit_notional)

    @staticmethod
    def _attach_spread_slippage_costs(trade_dict: dict, ctx: InstrumentCtx) -> None:
        position_size = float(trade_dict["position_size"])

        tp1_executed = trade_dict.get("tp1_time") is not None
        entry_fraction = 1.0
        tp1_fraction = 0.5 if tp1_executed else 0.0
        exit_fraction = 0.5 if tp1_executed else 1.0

        exec_entry = trade_dict.get("exec_type_entry") or EXEC_MARKET
        exec_exit = trade_dict.get("exec_type_exit") or EXEC_LIMIT

        spread_usd_entry = price_abs_to_usd(ctx.half_spread, ctx.point_size, ctx.pip_value, position_size, entry_fraction)
        spread_usd_tp1 = price_abs_to_usd(ctx.half_spread, ctx.point_size, ctx.pip_value, position_size, tp1_fraction) if tp1_executed else 0.0
        spread_usd_exit = price_abs_to_usd(ctx.half_spread, ctx.point_size, ctx.pip_value, position_size, exit_fraction)

        slip_usd_entry = price_abs_to_usd(ctx.slippage_abs, ctx.point_size, ctx.pip_value, position_size, entry_fraction) if exec_entry == EXEC_MARKET else 0.0
        slip_usd_tp1 = 0.0
        slip_usd_exit = price_abs_to_usd(ctx.slippage_abs, ctx.point_size, ctx.pip_value, position_size, exit_fraction) if exec_exit == EXEC_MARKET else 0.0

        trade_dict["spread_usd_entry"] = float(spread_usd_entry)
        trade_dict["spread_usd_tp1"] = float(spread_usd_tp1)
        trade_dict["spread_usd_exit"] = float(spread_usd_exit)
        trade_dict["spread_usd_total"] = float(spread_usd_entry + spread_usd_tp1 + spread_usd_exit)

        trade_dict["slippage_usd_entry"] = float(slip_usd_entry)
        trade_dict["slippage_usd_tp1"] = float(slip_usd_tp1)
        trade_dict["slippage_usd_exit"] = float(slip_usd_exit)
        trade_dict["slippage_usd_total"] = float(slip_usd_entry + slip_usd_tp1 + slip_usd_exit)

        trade_dict["costs_usd_total"] = float(trade_dict["spread_usd_total"] + trade_dict["slippage_usd_total"])

    @staticmethod
    def _attach_financing_costs(trade_dict: dict, ctx: InstrumentCtx) -> None:
        trade_dict["financing_usd_overnight"] = 0.0
        trade_dict["financing_usd_weekend"] = 0.0
        trade_dict["financing_usd_total"] = 0.0

        if not FINANCING_ENABLED:
            return

        entry_time = _to_dt(trade_dict["entry_time"])
        exit_time = _to_dt(trade_dict["exit_time"])

        rollovers = count_rollovers(entry_time, exit_time, FX_ROLLOVER_HOUR_UTC, FX_ROLLOVER_MINUTE_UTC)
        if not rollovers:
            return

        direction = trade_dict.get("direction")
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

            lots = float(trade_dict["position_size"])

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

            notional = float(trade_dict.get("traded_volume_usd_entry", 0.0))
            if notional <= 0.0:
                notional = float(trade_dict["entry_price"]) * float(trade_dict["position_size"]) * float(
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

        trade_dict["financing_usd_overnight"] = float(overnight)
        trade_dict["financing_usd_weekend"] = float(weekend)
        trade_dict["financing_usd_total"] = float(total)

        trade_dict["costs_usd_total"] = float(trade_dict.get("costs_usd_total", 0.0)) + float(total)

    @staticmethod
    def _attach_net_pnl(trade_dict: dict) -> None:
        gross = float(trade_dict.get("pnl_usd", 0.0))
        costs = float(trade_dict.get("costs_usd_total", 0.0))
        trade_dict["pnl_net_usd"] = float(gross - costs)