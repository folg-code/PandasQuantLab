import pandas as pd
from core.backtesting.results_logic.result import BacktestResult
from core.backtesting.results_logic.metadata import BacktestMetadata
from core.backtesting.results_logic.store import ResultStore


def test_backtest_result_save_load(tmp_path):
    meta = BacktestMetadata(
        run_id="test",
        created_at="now",
        backtest_mode="single",
        windows=None,
        strategies=["s1"],
        strategy_names={"s1": "TestStrategy"},
        symbols=["EURUSD"],
        timeframe="H1",
        initial_balance=1000,
        slippage=0.0,
        max_risk_per_trade=0.01,
    )

    trades = pd.DataFrame([{"a": 1}])

    result = BacktestResult(metadata=meta, trades=trades)

    store = ResultStore(base_path=tmp_path)
    path = store.save(result)

    loaded = store.load("test")

    assert loaded.metadata.run_id == "test"
    assert loaded.trades.equals(trades)