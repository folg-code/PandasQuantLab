from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


@dataclass
class BacktestMetadata:
    run_id: str
    created_at: str

    backtest_mode: str
    windows: dict[str, tuple[str, str]] | None

    strategies: list[str]
    strategy_names: dict[str, str]

    symbols: list[str]
    timeframe: str

    initial_balance: float
    slippage: float
    max_risk_per_trade: float

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
