from dataclasses import dataclass


@dataclass(frozen=True)
class InstrumentCtx:
    symbol: str
    point_size: float
    pip_value: float
    contract_size: float
    spread_abs: float
    half_spread: float
    slippage_abs: float