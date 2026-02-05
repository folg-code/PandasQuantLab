from __future__ import annotations

import MetaTrader5 as mt5

from core.domain.risk.sizing import position_size
from core.live_trading.execution.risk.mt5_risk_params import Mt5RiskParams


class LiveSizer:
    @staticmethod
    def get_account_size() -> float:
        account = mt5.account_info()
        if account is None:
            raise RuntimeError("MT5 account info unavailable")
        return float(account.balance)

    @staticmethod
    def calculate_volume(*, symbol: str, entry_price: float, sl: float, max_risk: float) -> float:
        account_size = LiveSizer.get_account_size()
        point_size, pip_value = Mt5RiskParams.get_symbol_risk_params(symbol)

        vol = position_size(
            entry_price=float(entry_price),
            stop_price=float(sl),
            max_risk=float(max_risk),
            account_size=float(account_size),
            point_size=float(point_size),
            pip_value=float(pip_value),
        )
        if vol <= 0:
            raise RuntimeError(f"Calculated invalid volume: {vol}")
        return float(vol)