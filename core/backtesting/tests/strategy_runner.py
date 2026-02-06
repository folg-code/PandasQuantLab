import pytest
from core.backtesting.strategy_runner import StrategyRunResult


def test_strategy_run_result_is_immutable():
    with pytest.raises(TypeError):
        StrategyRunResult(
            symbol="EURUSD",
            strategy_id="s",
            strategy_name="x",
            df_signals=None,
            df_context=None,
            trade_plans=None,
            report_spec=None,
            timing={},
            extra_field=123,
        )
