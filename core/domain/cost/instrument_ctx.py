from dataclasses import dataclass

from config.backtest import SLIPPAGE
from config.instrument_meta import INSTRUMENT_META, get_spread_abs


@dataclass(frozen=True)
class InstrumentCtx:
    symbol: str
    point_size: float
    pip_value: float
    contract_size: float
    spread_abs: float
    half_spread: float
    slippage_abs: float


def build_instrument_ctx(symbol: str) -> InstrumentCtx:
    meta = INSTRUMENT_META[symbol]

    point_size = float(meta["point"])
    pip_value = float(meta["pip_value"])
    contract_size = float(meta.get("contract_size", 1.0))

    spread_abs = get_spread_abs(symbol, point_size)
    half_spread = 0.5 * spread_abs
    slippage_abs = float(SLIPPAGE) * point_size

    return InstrumentCtx(
        symbol=symbol,
        point_size=point_size,
        pip_value=pip_value,
        contract_size=contract_size,
        spread_abs=spread_abs,
        half_spread=half_spread,
        slippage_abs=slippage_abs,
    )