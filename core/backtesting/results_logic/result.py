from pathlib import Path
import json
import pandas as pd
from core.backtesting.results_logic.metadata import BacktestMetadata


class BacktestResult:
    """
    Immutable snapshot of backtest output.
    """

    def __init__(
        self,
        *,
        metadata: BacktestMetadata,
        trades: pd.DataFrame,
        analytics: pd.DataFrame | None = None,
    ):
        self.metadata = metadata
        self.trades = trades
        self.analytics = analytics

    # ==================================================
    # SAVE / LOAD
    # ==================================================

    def save(self, path: str | Path):
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        with open(path / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(self.metadata.to_dict(), f, indent=2)

        self.trades.to_parquet(path / "trades.parquet", index=False)

        if self.analytics is not None:
            self.analytics.to_parquet(path / "analytics.parquet", index=False)

        self._write_readme(path)

    @staticmethod
    def load(path: str | Path) -> "BacktestResult":
        path = Path(path)

        with open(path / "metadata.json", encoding="utf-8") as f:
            meta = BacktestMetadata(**json.load(f))

        trades = pd.read_parquet(path / "trades.parquet")

        analytics = (
            pd.read_parquet(path / "analytics.parquet")
            if (path / "analytics.parquet").exists()
            else None
        )

        return BacktestResult(
            metadata=meta,
            trades=trades,
            analytics=analytics,
        )

    # ==================================================
    # README
    # ==================================================

    def _write_readme(self, path: Path):
        m = self.metadata
        txt = f"""# Backtest Result

Run ID: {m.run_id}
Created: {m.created_at}

Strategies:
{chr(10).join(f"- {sid}: {m.strategy_names[sid]}" for sid in m.strategies)}

Symbols: {", ".join(m.symbols)}
Timeframe: {m.timeframe}
Backtest mode: {m.backtest_mode}
"""
        (path / "README.md").write_text(txt, encoding="utf-8")
