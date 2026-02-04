def price_abs_to_usd(
    price_abs: float,
    point_size: float,
    pip_value: float,
    position_size: float,
    fraction: float,
) -> float:
    if fraction <= 0.0:
        return 0.0
    pips = price_abs / point_size
    return pips * pip_value * position_size * fraction


def attach_net_pnl(trade: dict) -> None:
    gross = float(trade.get("pnl_usd", 0.0))
    costs = float(trade.get("costs_usd_total", 0.0))
    trade["pnl_net_usd"] = float(gross - costs)