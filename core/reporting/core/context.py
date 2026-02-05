from dataclasses import dataclass
from typing import Optional, Set, Any

import pandas as pd


@dataclass(frozen=True)
class ContextSpec:
    name: str
    column: str
    source: str
    allowed_values: Optional[Set] = None


@dataclass
class ReportContext:
    # --- core data ---
    trades: pd.DataFrame
    equity: pd.Series | None
    drawdown: pd.Series | None

    df_plot: pd.DataFrame | None

    initial_balance: float
    config: Any

    metadata: Any | None = None

    strategy: Any | None = None

    def __post_init__(self):
        """
        Adapter layer:
        - old code expects ctx.strategy
        - new code should use ctx.metadata
        """
        if self.strategy is None and self.metadata is not None:
            self.strategy = self.metadata