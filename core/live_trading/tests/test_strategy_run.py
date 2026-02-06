from datetime import datetime, timezone
from unittest.mock import Mock

import pandas as pd

from core.live_trading.strategy_runner import LiveStrategyRunner


class DummyStrategy:
    def __init__(self):
        self.df = None
        self.strategy_config = {}

    def get_required_informatives(self):
        return []

    def populate_indicators(self): pass
    def populate_entry_trend(self): pass
    def populate_exit_trend(self): pass

    def get_strategy_name(self):
        return "dummy"

    def build_trade_plan_live(self, row, ctx):
        return "PLAN"



def test_live_strategy_runner_returns_last_row_and_plan():
    df = pd.DataFrame(
        {
            "time": [
                datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                datetime(2025, 1, 1, 12, 5, tzinfo=timezone.utc),
            ],
            "signal": ["long", "long"],
        }
    )

    provider = Mock()
    provider.fetch.return_value = {"M5": df}

    strategy = DummyStrategy()

    runner = LiveStrategyRunner(
        strategy=strategy,
        data_provider=provider,
        symbol="EURUSD",
    )

    result = runner.run()

    assert result.plan == "PLAN"
    assert result.last_row["signal"] == "long"