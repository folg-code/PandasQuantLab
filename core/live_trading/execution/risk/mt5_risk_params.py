from __future__ import annotations

import MetaTrader5 as mt5


class Mt5RiskParams:
    @staticmethod
    def get_symbol_risk_params(symbol: str) -> tuple[float, float]:
        """
        Returns (point_size, pip_value) for 1 lot.
        """
        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"Symbol not found: {symbol}")

        point_size = float(info.point)

        # heuristic from your code
        if info.point < 0.01:
            ticks_per_pip = 0.0001 / info.point
        else:
            ticks_per_pip = 1.0

        pip_value = float(info.trade_tick_value) * float(ticks_per_pip)
        return point_size, pip_value

    @staticmethod
    def normalize_volume(symbol: str, volume: float) -> float:
        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"Symbol not found: {symbol}")

        min_vol = float(info.volume_min)
        max_vol = float(info.volume_max)
        step = float(info.volume_step)

        volume = max(min_vol, min(float(volume), max_vol))

        steps = int(volume / step)
        normalized = round(steps * step, 2)

        if normalized < min_vol:
            raise RuntimeError(f"Normalized volume {normalized} < min volume {min_vol}")

        return normalized