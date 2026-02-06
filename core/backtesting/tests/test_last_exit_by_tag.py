from core.backtesting.engine.execution_loop import run_execution_loop


def test_no_overlapping_trades_by_tag(base_df, long_plan, instrument_ctx):
    plans = long_plan.copy()
    plans["plan_valid"] = True
    plans["plan_entry_tag"] = ["A"] * len(plans)

    plans["plan_tp1"] = 10.0
    plans["plan_sl"] = 0.5

    df = base_df.copy()
    df["high"] = 1.0
    df["low"] = 1.0

    trades = run_execution_loop(
        df=df,
        symbol="EURUSD",
        plans=plans,
        instrument_ctx=instrument_ctx,
    )

    for t1, t2 in zip(trades, trades[1:]):
        assert t1["exit_time"] <= t2["entry_time"]