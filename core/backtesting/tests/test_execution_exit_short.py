from core.backtesting.engine.execution_loop import run_execution_loop


def test_short_hits_sl(base_df, short_plan, instrument_ctx):
    plans = short_plan.copy()
    plans["plan_tp1"] = -10.0

    df = base_df.copy()
    df["low"] = 1.05
    df.loc[2, "high"] = 1.25

    trades = run_execution_loop(
        df=df, symbol="EURUSD", plans=plans, instrument_ctx=instrument_ctx
    )

    assert trades[0]["exit_level_tag"] == "SL"