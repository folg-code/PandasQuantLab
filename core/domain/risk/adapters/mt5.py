import os
import json
import MetaTrader5 as mt5

from core.domain.risk.sizing import position_size

CACHE_FILE = "market_data/pip_values.json"


def _load_pip_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_pip_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def get_point_size_mt5(symbol: str, default: float = 0.0001) -> float:
    if mt5.initialize():
        info = mt5.symbol_info(symbol)
        if info:
            point = info.point
            mt5.shutdown()
            return point
    return default


def get_pip_value_mt5(symbol: str, lot_size: float = 1.0, default: float = 10.0) -> float:
    cache = _load_pip_cache()
    if symbol in cache:
        return cache[symbol]

    pip_value = default
    if mt5.initialize():
        info = mt5.symbol_info(symbol)
        if info:
            ticks_per_pip = 0.0001 / info.point if info.point < 0.01 else 1.0
            pip_value = info.trade_tick_value * ticks_per_pip * lot_size
        mt5.shutdown()

    cache[symbol] = pip_value
    _save_pip_cache(cache)
    return pip_value


def position_size_live(
    *,
    entry_price: float,
    stop_price: float,
    max_risk: float,
    account_size: float,
    symbol: str,
    lot_size: float = 1.0,
) -> float:
    point_size = get_point_size_mt5(symbol)
    pip_value = get_pip_value_mt5(symbol, lot_size)

    return position_size(
        entry_price=entry_price,
        stop_price=stop_price,
        max_risk=max_risk,
        account_size=account_size,
        point_size=point_size,
        pip_value=pip_value,
    )