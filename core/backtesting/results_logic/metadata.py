from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


@dataclass
class BacktestMetadata:
    run_id: str
    created_at: str

    # experiment scope
    backtest_mode: str                 # single / split
    windows: dict[str, tuple[str, str]] | None

    # strategy
    strategies: list[str]              # strategy_id list
    strategy_names: dict[str, str]     # id -> name

    # symbols
    symbols: list[str]
    timeframe: str

    # execution / capital
    initial_balance: float
    slippage: float
    max_risk_per_trade: float

    # misc
    notes: str | None = None

    @staticmethod
    def now(run_id: str, **kwargs) -> "BacktestMetadata":
        return BacktestMetadata(
            run_id=run_id,
            created_at=datetime.utcnow().isoformat(),
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)