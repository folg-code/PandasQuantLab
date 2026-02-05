from __future__ import annotations

import inspect
from typing import Any, Dict, Optional, List

from core.reporting.core.section import ReportSection


def extract_informative_timeframes(strategy: Any) -> Optional[List[str]]:
    """
    Extract informative timeframes from strategy methods decorated with @informative(timeframe)
    where decorator sets:
        func._informative = True
        func._informative_timeframe = "<TF>"
    """
    if strategy is None:
        return None

    cls = strategy if inspect.isclass(strategy) else strategy.__class__
    timeframes: set[str] = set()

    for _, member in inspect.getmembers(cls):
        fn = None

        if inspect.isfunction(member):
            fn = member
        elif isinstance(member, (staticmethod, classmethod)):
            fn = member.__func__

        if fn is None:
            continue

        if getattr(fn, "_informative", False):
            tf = getattr(fn, "_informative_timeframe", None)
            if tf:
                timeframes.add(str(tf))

    return sorted(timeframes) if timeframes else None


def _safe_getattr(obj: Any, name: str, default=None):
    try:
        return getattr(obj, name, default)
    except Exception:
        return default


class BacktestConfigSection(ReportSection):
    """
    Backtest Configuration & Assumptions

    Goals:
    - No hardcoded claims about execution that aren't actually modeled.
    - Pull info from cfg + (optionally) strategy + execution_policy.
    - Avoid duplicating KPI metrics (we use "Data timerange" wording).
    """

    name = "Backtest Configuration & Assumptions"

    def compute(self, ctx: "ReportContext") -> dict:
        cfg = ctx.config

        strategy = _safe_getattr(ctx, "strategy", None)
        execution_policy = _safe_getattr(ctx, "execution_policy", None)

        market_data = self._market_and_data(cfg, strategy=strategy)
        exec_model = self._execution_model(cfg, execution_policy=execution_policy)
        capital_model = self._capital_model(cfg)

        return {
            "Market & Data": market_data,
            "Execution Model": exec_model,
            "Capital Model": capital_model,
        }

    # -----------------------
    # Market & Data
    # -----------------------
    def _market_and_data(self, cfg, strategy=None) -> Dict[str, Any]:
        symbols = _safe_getattr(cfg, "SYMBOLS", None)
        exec_tf = _safe_getattr(cfg, "TIMEFRAME", None)
        data_src = _safe_getattr(cfg, "BACKTEST_DATA_BACKEND", None)

        timerange = _safe_getattr(cfg, "TIMERANGE", None) or {}
        data_start = timerange.get("start")
        data_end = timerange.get("end")

        missing_handling = _safe_getattr(cfg, "MISSING_DATA_HANDLING", None) or "Forward-fill OHLC gaps (assumed)"

        strat_name = self._strategy_name(strategy)
        strat_desc = self._strategy_description(cfg, strategy)
        informatives = self._informative_timeframes(strategy)

        out: Dict[str, Any] = {
            "Strategy": strat_name,
            "Strategy description": strat_desc,  # may be None
            "Instruments": symbols,
            "Execution timeframe": exec_tf,
            "Data source": data_src,
            "Data timerange": f"{data_start} → {data_end}" if (data_start and data_end) else None,
            "Missing data handling": missing_handling,
        }

        if informatives:
            out["Informative timeframes"] = informatives

        # Remove empty keys (avoid clutter in UI)
        return {k: v for k, v in out.items() if v is not None}

    @staticmethod
    def _strategy_name(strategy: Any) -> str:

        if strategy is not None:
            cls = strategy if inspect.isclass(strategy) else strategy.__class__
            return cls.__name__

        return "Unknown"

    @staticmethod
    def _strategy_description(cfg, strategy: Any) -> Optional[str]:
        """
        Optional. Priority:
        1) cfg.STRATEGY_DESCRIPTION / cfg.STRATEGY_DESC
        2) strategy.description / strategy.strategy_description
        3) strategy.get_description() method
        """
        for key in ("STRATEGY_DESCRIPTION", "STRATEGY_DESC"):
            val = _safe_getattr(cfg, key, None)
            if val:
                return str(val)

        if strategy is None:
            return None

        for attr in ("description", "strategy_description"):
            val = _safe_getattr(strategy, attr, None)
            if val:
                return str(val)

        if hasattr(strategy, "get_description"):
            try:
                val = strategy.get_description()
                if val:
                    return str(val)
            except Exception:
                pass

        return None

    @staticmethod
    def _informative_timeframes(strategy: Any) -> Optional[List[str]]:

        if strategy is not None:
            if hasattr(strategy, "get_informative_timeframes"):
                try:
                    v = strategy.get_informative_timeframes()
                    if v:
                        return list(v) if isinstance(v, (list, tuple, set)) else [str(v)]
                except Exception:
                    pass

            v = _safe_getattr(strategy, "informative_timeframes", None)
            if v:
                return list(v) if isinstance(v, (list, tuple, set)) else [str(v)]

            # decorator scan
            v = extract_informative_timeframes(strategy)
            if v:
                return v

        return None

    def _execution_model(self, cfg, execution_policy=None) -> Dict[str, Any]:
        entry_type = _safe_getattr(execution_policy, "entry_type", None)
        exit_default_type = _safe_getattr(execution_policy, "exit_default_type", None)
        tp_type = _safe_getattr(execution_policy, "tp_type", None)

        exec_delay = _safe_getattr(cfg, "EXECUTION_DELAY", None) or "None"
        slippage = _safe_getattr(cfg, "SLIPPAGE", None)

        spread_model = self._describe_spread_model(cfg)

        # Make overrides explicit to avoid misinformation.
        exit_overrides = _safe_getattr(cfg, "EXIT_OVERRIDES_DESC", None) or (
            "Common override: SL/BE/EOD act like market exits; TP exits are limit (strategy-dependent)."
        )

        out = {
            "Entry order type (default)": entry_type or "Market",
            "Exit order type (default)": exit_default_type or "Limit",
            "TP order type (default)": tp_type or "Limit",
            "Exit overrides": exit_overrides,
            "Execution delay": exec_delay,
            "Spread model": spread_model,
            "Slippage": slippage,
        }

        return {k: v for k, v in out.items() if v is not None}

    @staticmethod
    def _describe_spread_model(cfg) -> str:

        v = _safe_getattr(cfg, "SPREAD_MODEL", None)
        if v:
            return str(v)

        # Current reality in your implementation:
        # you compute spread_usd_* using fixed per-instrument spread config as a reporting/cost overlay
        return "Fixed spread (per instrument) → cost overlay in USD (no bid/ask price simulation)"

    @staticmethod
    def _capital_model(cfg) -> Dict[str, Any]:
        initial_balance = _safe_getattr(cfg, "INITIAL_BALANCE", None)
        max_risk = _safe_getattr(cfg, "MAX_RISK_PER_TRADE", None)

        position_sizing = _safe_getattr(cfg, "POSITION_SIZING_MODEL", None) or "Risk-based sizing (position_sizer_fast)"
        leverage = _safe_getattr(cfg, "LEVERAGE", None) or "1x"

        max_concurrent = _safe_getattr(cfg, "MAX_CONCURRENT_POSITIONS", None)
        max_concurrent = max_concurrent if max_concurrent is not None else "Unlimited"

        kill_switch = _safe_getattr(cfg, "CAPITAL_FLOOR", None)
        kill_switch = kill_switch if kill_switch is not None else "None (diagnostic mode)"

        max_risk_str = f"{float(max_risk) * 100:.2f} %" if max_risk is not None else None

        out = {
            "Starting equity": initial_balance,
            "Position sizing": position_sizing,
            "Max risk per trade": max_risk_str,
            "Leverage": leverage,
            "Max concurrent positions": max_concurrent,
            "Capital floor / kill-switch": kill_switch,
        }
        return {k: v for k, v in out.items() if v is not None}
