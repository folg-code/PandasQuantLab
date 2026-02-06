from core.backtesting.engine.execution_loop import run_execution_loop


def test_execution_is_deterministic(base_df, long_plan, instrument_ctx):
    t1 = run_execution_loop(
        df=base_df, symbol="EURUSD", plans=long_plan, instrument_ctx=instrument_ctx
    )
    t2 = run_execution_loop(
        df=base_df, symbol="EURUSD", plans=long_plan, instrument_ctx=instrument_ctx
    )

    assert t1 == t2