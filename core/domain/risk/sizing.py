def position_size(
    *,
    entry_price: float,
    stop_price: float,
    max_risk: float,
    account_size: float,
    point_size: float,
    pip_value: float,
    risk_is_percent: bool = True,
    precision: int = 3,
) -> float:
    """
    Domain-level risk sizing.
    Pure function.
    """

    if entry_price == stop_price:
        return 0.0

    pip_distance = abs(entry_price - stop_price) / point_size
    risk_amount = max_risk * account_size if risk_is_percent else max_risk

    size = risk_amount / (pip_distance * pip_value)
    return round(size, precision)