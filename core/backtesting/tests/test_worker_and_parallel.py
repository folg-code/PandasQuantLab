from core.backtesting.engine.worker import run_backtest_worker


def test_run_backtest_worker_smoke(base_df, long_plan):
    trades = run_backtest_worker(
        signals_df=base_df,
        trade_plans=long_plan,
    )

    assert trades is not None
