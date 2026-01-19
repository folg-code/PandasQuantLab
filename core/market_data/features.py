# core/market_data/features.py

from dataclasses import dataclass

@dataclass(frozen=True)
class MarketDataFeatures:
    """
    Declares which market data features are available.
    This is explicit by design – no guessing, no defaults.
    """
    has_volume: bool = False          # tick_volume / volume
    has_real_volume: bool = False     # exchange-reported volume
    has_spread: bool = False
    has_ticks: bool = False

    def satisfies(self, required: "MarketDataFeatures") -> bool:
        """
        Check whether this feature set satisfies required features.
        """
        return (
            (not required.has_volume or self.has_volume) and
            (not required.has_real_volume or self.has_real_volume) and
            (not required.has_spread or self.has_spread) and
            (not required.has_ticks or self.has_ticks)
        )


@dataclass(frozen=True)
class MarketDataCapabilities:
    """
    Describes what a backend can provide.
    """
    source: str                       # "dukascopy", "mt5", "binance", ...
    features: MarketDataFeatures