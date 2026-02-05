import pandas as pd

from core.strategy.base import BaseStrategy
from core.strategy.informatives import informative


class DummyProvider:
    """
    Realistic HTF provider for tests.
    Must satisfy strategy HTF indicator requirements.
    """

    def get_informative_df(self, symbol, timeframe, startup_candle_count):
        n = 50

        return pd.DataFrame({
            "time": pd.date_range(
                "2024-01-01",
                periods=n,
                freq="30min",
                tz="UTC",
            ),
            "open": 100.0,
            "high": 110.0,
            "low": 90.0,
            "close": 100.0,
            "volume": 1.0,
        })


class DummyStrategy(BaseStrategy):
    def populate_indicators(self):
        pass

    def populate_entry_trend(self):
        pass

    def populate_exit_trend(self):
        pass


class TestStrategy(BaseStrategy):

    @informative("M30")
    def populate_htf(self, df):
        return df

    def populate_indicators(self): pass
    def populate_entry_trend(self): pass
    def populate_exit_trend(self): pass
