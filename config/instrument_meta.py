INSTRUMENT_META = {
    "EURUSD": {
        "point": 0.0001,
        "pip_value": 10.0,
        "spread_pips": 1.0,
        "contract_size": 1.0,
    },
    "XAUUSD": {
        "point": 0.01,
        "pip_value": 1.0,
        "spread_points": 0.10,
        "contract_size": 1.0,
    },
    "USTECH100": {
        "point": 0.01,
        "pip_value": 1.0,
        "contract_size": 1.0,
        "spread_points": 1.0,
    }
}

def get_spread_abs(symbol: str, point_size: float) -> float:
    """
    Spread w jednostkach ceny (abs).
    - FX: spread_pips * point_size
    - Inne: spread_points (już w cenie)
    """
    meta = INSTRUMENT_META.get(symbol, {})
    if "spread_pips" in meta:
        return float(meta["spread_pips"]) * float(point_size)
    if "spread_points" in meta:
        return float(meta["spread_points"])
    return 0.0


def price_abs_to_usd(
    abs_price: float,
    point_size: float,
    pip_value: float,
    position_size: float,
    fraction: float = 1.0,
) -> float:
    """
    Przelicza ruch ceny / koszt w abs na USD wg Twojej konwencji:
    (abs/point)*pip_value*position_size
    """
    return (float(abs_price) / float(point_size)) * float(pip_value) * float(position_size) * float(fraction)


def get_contract_size(symbol: str) -> float:
    meta = INSTRUMENT_META.get(symbol, {})
    return float(meta.get("contract_size", 1.0))