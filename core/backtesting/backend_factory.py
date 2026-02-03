from core.data_provider import MarketDataBackend
from core.data_provider.backends.dukascopy_backend import DukascopyBackend
from core.data_provider.clients.dukascopy_client import DukascopyClient


def create_backtest_backend(name: str) -> MarketDataBackend:
    name = name.lower()

    if name == "dukascopy":
        return DukascopyBackend(
            client=DukascopyClient()
        )

    raise ValueError(
        f"Unsupported backtest backend: {name}. Allowed: dukascopy, csv")
