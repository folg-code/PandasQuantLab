import pandas as pd
import pytest

from core.domain.cost.instrument_ctx import build_instrument_ctx


@pytest.fixture
def instrument_ctx():
    return build_instrument_ctx("EURUSD")


@pytest.fixture
def base_df():
    return pd.DataFrame({
        "time": pd.date_range("2022-01-01", periods=6, freq="1H"),
        "open":  [1, 1, 1, 1, 1, 1],
        "high":  [1, 1.1, 1.1, 1.1, 1.1, 1.1],
        "low":   [1, 0.9, 0.9, 0.9, 0.9, 0.9],
        "close": [1, 1.05, 1.05, 1.05, 1.05, 1.05],
        "signal_entry": [None, True, None, None, None, None],
        "symbol": ["EURUSD"] * 6,
    })


@pytest.fixture
def long_plan():
    return pd.DataFrame({
        "plan_valid": [False, True, False, False, False, False],
        "plan_direction": ["long"] * 6,
        "plan_entry_tag": ["L1"] * 6,
        "plan_sl": [0.9] * 6,
        "plan_tp1": [1.1] * 6,
        "plan_tp2": [1.2] * 6,
        "plan_sl_tag": ["SL"] * 6,
        "plan_tp1_tag": ["TP1"] * 6,
        "plan_tp2_tag": ["TP2"] * 6,
    })


@pytest.fixture
def short_plan(long_plan):
    df = long_plan.copy()
    df["plan_direction"] = "short"
    df["plan_sl"] = 1.2
    df["plan_tp1"] = 1.0
    df["plan_tp2"] = 0.9
    return df
