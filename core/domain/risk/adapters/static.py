from core.domain.risk.sizing import position_size


def position_size_static(
    *,
    entry_price: float,
    stop_price: float,
    max_risk: float,
    account_size: float,
    point_size: float,
    pip_value: float,
) -> float:
    return position_size(
        entry_price=entry_price,
        stop_price=stop_price,
        max_risk=max_risk,
        account_size=account_size,
        point_size=point_size,
        pip_value=pip_value,
    )