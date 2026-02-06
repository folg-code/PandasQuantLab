from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class MarketStateProvider(ABC):
    """
    Provides market state events for the LiveEngine.
    """

    @abstractmethod
    def poll(self) -> Optional[Dict[str, Any]]:
        """
        Returns:
            {
              "price": float,
              "time": datetime,
              "candle_time": datetime | None
            }
        """
        ...