from core.backtesting.engine.execution_loop import run_execution_loop


def test_plan_valid_false_produces_no_trades(base_df, long_plan, instrument_ctx):
    plans = long_plan.copy()
    plans["plan_valid"] = False

    trades = run_execution_loop(
        df=base_df,
        symbol="EURUSD",
        plans=plans,
        instrument_ctx=instrument_ctx,
    )

    assert trades == []
