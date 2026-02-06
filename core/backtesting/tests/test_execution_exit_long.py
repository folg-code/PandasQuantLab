from core.backtesting.engine.execution_loop import run_execution_loop


def test_long_hits_sl(base_df, long_plan, instrument_ctx):
    plans = long_plan.copy()
    plans["plan_tp1"] = 10.0
    plans["plan_sl"] = 0.9

    df = base_df.copy()
    df["high"] = 1.0
    df.loc[2, "low"] = 0.85

    trades = run_execution_loop(
        df=df, symbol="EURUSD", plans=plans, instrument_ctx=instrument_ctx
    )

    assert trades[0]["exit_level_tag"] == "SL"


def test_long_tp1_then_be(base_df, long_plan, instrument_ctx):
    df = base_df.copy()
    df.loc[2, "high"] = 1.1
    df.loc[3, "low"] = df.loc[1, "close"]

    trades = run_execution_loop(
        df=df, symbol="EURUSD", plans=long_plan, instrument_ctx=instrument_ctx
    )

    assert trades[0]["exit_level_tag"] == "TP1"


def test_long_hits_tp2_without_tp1(base_df, long_plan, instrument_ctx):
    plans = long_plan.copy()
    plans["plan_tp1"] = 10.0
    plans["plan_sl"] = 0.8

    df = base_df.copy()
    df["low"] = 0.95
    df.loc[2, "high"] = 1.21

    trades = run_execution_loop(
        df=df, symbol="EURUSD", plans=plans, instrument_ctx=instrument_ctx
    )

    assert trades[0]["exit_level_tag"] == "TP2"