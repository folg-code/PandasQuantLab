from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Literal, Tuple

import numpy as np
import pandas as pd

from core.strategy.trade_plan import TradePlan, FixedExitPlan, ManagedExitPlan


@dataclass(frozen=True)
class PlanBuildContext:
    symbol: str
    strategy_name: str
    strategy_config: Dict[str, Any]
    account_size: float | None = None
    max_risk_per_trade: float | None = None


# ==========================================================
# Helpers
# ==========================================================

def _extract_direction_tag(
        signal: Any
) -> Tuple[Optional[Literal["long", "short"]], str]:
    if not isinstance(signal, dict):
        return None, ""
    d = signal.get("direction")
    if d not in ("long", "short"):
        return None, ""
    return d, str(signal.get("tag", ""))


def _extract_level(levels: Any, key: Any) -> Optional[float]:
    if not isinstance(levels, dict):
        return None

    item = levels.get(key)
    if item is None and isinstance(key, str):
        fallback = {"SL": 0, "TP1": 1, "TP2": 2}.get(key)
        if fallback is not None:
            item = levels.get(fallback)

    if not isinstance(item, dict):
        return None

    v = item.get("level")
    if v is None:
        return None

    try:
        return float(v)
    except Exception:
        return None


def _extract_level_tag(levels: Any, key: Any) -> str:
    if not isinstance(levels, dict):
        return ""

    item = levels.get(key)
    if item is None and isinstance(key, str):
        fallback = {"SL": 0, "TP1": 1, "TP2": 2}.get(key)
        if fallback is not None:
            item = levels.get(fallback)

    if not isinstance(item, dict):
        return ""

    tag = item.get("tag")
    return "" if tag is None else str(tag)


def _has_dict(x: Any) -> bool:
    return isinstance(x, dict)


def build_trade_plan_from_row(
        *,
        row: pd.Series,
        ctx: PlanBuildContext
) -> TradePlan | None:
    signal = row.get("signal_entry")
    levels = row.get("levels")

    direction, entry_tag = _extract_direction_tag(signal)
    if direction is None or not isinstance(levels, dict):
        return None

    sl = _extract_level(levels, "SL")
    tp1 = _extract_level(levels, "TP1")
    tp2 = _extract_level(levels, "TP2")

    if sl is None:
        return None

    use_trailing = bool(ctx.strategy_config.get("USE_TRAILING", False))
    has_signal_exit = _has_dict(row.get("signal_exit"))
    has_custom_sl = _has_dict(row.get("custom_stop_loss"))
    is_managed = use_trailing or has_signal_exit or has_custom_sl

    entry_price = float(row["close"])

    if is_managed:
        exit_plan = ManagedExitPlan(sl=sl, tp1=tp1)
    else:
        if tp1 is None or tp2 is None:
            return None
        exit_plan = FixedExitPlan(sl=sl, tp1=tp1, tp2=tp2)

    return TradePlan(
        symbol=ctx.symbol,
        direction=direction,
        entry_price=entry_price,
        entry_tag=entry_tag,
        volume=0.0,
        exit_plan=exit_plan,
        strategy_name=ctx.strategy_name,
        strategy_config=dict(ctx.strategy_config),
    )

def build_plans_frame(
    *,
    df: pd.DataFrame,
    ctx: PlanBuildContext,
    allow_managed_in_backtest: bool = False,
) -> pd.DataFrame:
    """
    Returns plans_df aligned to df.index with:
      - plan_valid
      - plan_direction
      - plan_entry_tag
      - plan_entry_price
      - plan_sl, plan_tp1, plan_tp2
      - plan_sl_tag, plan_tp1_tag, plan_tp2_tag   <-- NEW
      - plan_exit_mode (fixed/managed/None)
    """
    n = len(df)
    plans = pd.DataFrame(index=df.index)

    sig_vals = df.get("signal_entry", pd.Series(index=df.index, dtype=object)).values
    lvl_vals = df.get("levels", pd.Series(index=df.index, dtype=object)).values

    direction = np.empty(n, dtype=object)
    entry_tag = np.empty(n, dtype=object)

    sl = np.full(n, np.nan, dtype=float)
    tp1 = np.full(n, np.nan, dtype=float)
    tp2 = np.full(n, np.nan, dtype=float)

    sl_tag = np.empty(n, dtype=object); sl_tag[:] = ""
    tp1_tag = np.empty(n, dtype=object); tp1_tag[:] = ""
    tp2_tag = np.empty(n, dtype=object); tp2_tag[:] = ""

    for i in range(n):
        d, t = _extract_direction_tag(sig_vals[i])
        direction[i] = d
        entry_tag[i] = t

        lv = lvl_vals[i]
        if not isinstance(lv, dict):
            continue

        v_sl = _extract_level(lv, "SL")
        v_tp1 = _extract_level(lv, "TP1")
        v_tp2 = _extract_level(lv, "TP2")

        if v_sl is not None:
            sl[i] = v_sl
        if v_tp1 is not None:
            tp1[i] = v_tp1
        if v_tp2 is not None:
            tp2[i] = v_tp2

        sl_tag[i] = _extract_level_tag(lv, "SL")
        tp1_tag[i] = _extract_level_tag(lv, "TP1")
        tp2_tag[i] = _extract_level_tag(lv, "TP2")

    use_trailing = bool(ctx.strategy_config.get("USE_TRAILING", False))
    if use_trailing:
        is_managed = np.ones(n, dtype=bool)
    else:
        se = df.get("signal_exit")
        csl = df.get("custom_stop_loss")
        se_mask = se.apply(_has_dict).values if se is not None else np.zeros(n, dtype=bool)
        csl_mask = csl.apply(_has_dict).values if csl is not None else np.zeros(n, dtype=bool)
        is_managed = se_mask | csl_mask

    has_dir = pd.Series(direction).isin(["long", "short"]).values
    has_sl = ~np.isnan(sl)

    fixed_ok = has_dir & has_sl & (~np.isnan(tp1)) & (~np.isnan(tp2))
    managed_ok = has_dir & has_sl

    if not allow_managed_in_backtest:
        valid = fixed_ok
        exit_mode = np.where(valid, "fixed", None).astype(object)
    else:
        valid = fixed_ok | managed_ok
        exit_mode = np.where(is_managed, "managed", "fixed").astype(object)

    plans["plan_valid"] = valid
    plans["plan_direction"] = direction
    plans["plan_entry_tag"] = entry_tag
    plans["plan_entry_price"] = df["close"].astype(float).values

    plans["plan_sl"] = sl
    plans["plan_tp1"] = tp1
    plans["plan_tp2"] = tp2

    plans["plan_sl_tag"] = sl_tag
    plans["plan_tp1_tag"] = tp1_tag
    plans["plan_tp2_tag"] = tp2_tag

    plans["plan_exit_mode"] = exit_mode

    return plans
