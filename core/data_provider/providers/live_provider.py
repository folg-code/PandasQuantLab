import pandas as pd

from core.data_provider.contracts import LiveMarketDataClient


class LiveStrategyDataProvider:
    """
    Strategy-level provider for LIVE trading.

    Adapts any LiveMarketDataClient to StrategyDataProvider.
    """

    def __init__(
        self,
        *,
        client: LiveMarketDataClient,
        bars_per_tf: dict[str, int],
    ):
        self.client = client
        self.bars_per_tf = bars_per_tf

    def fetch(self, symbol: str) -> dict[str, pd.DataFrame]:
        data: dict[str, pd.DataFrame] = {}

        for tf, bars in self.bars_per_tf.items():
            df = self.client.get_ohlcv(
                symbol=symbol,
                timeframe=tf,
                bars=bars,
            )
            data[tf] = df

        return data