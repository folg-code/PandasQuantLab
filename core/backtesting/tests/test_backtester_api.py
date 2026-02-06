import pandas as pd
import pytest

from core.backtesting.engine.backtester import Backtester


def test_backtester_empty_inputs():
    bt = Backtester()
    out = bt.run(signals_df=pd.DataFrame(), trade_plans=pd.DataFrame())
    assert out.empty


def test_backtester_requires_signal_columns():
    bt = Backtester()

    signals = pd.DataFrame({
        "close": [1, 2, 3],
        "symbol": ["EURUSD"] * 3,
    })

    plans = pd.DataFrame({
        "plan_valid": [True, True, True],
        "plan_direction": ["long"] * 3,
        "plan_entry_tag": ["A"] * 3,
        "plan_sl": [0.9] * 3,
        "plan_tp1": [1.1] * 3,
        "plan_tp2": [1.2] * 3,
        "plan_sl_tag": ["SL"] * 3,
        "plan_tp1_tag": ["TP1"] * 3,
        "plan_tp2_tag": ["TP2"] * 3,
    })

    with pytest.raises(ValueError):
        bt.run(signals_df=signals, trade_plans=plans)