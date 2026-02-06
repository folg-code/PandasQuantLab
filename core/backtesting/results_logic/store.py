from pathlib import Path
from core.backtesting.results_logic.result import BacktestResult


class ResultStore:
    """
    File-based registry for BacktestResult.
    Single source of truth for run paths.
    """

    def __init__(self, base_path: str | Path = "results/backtests"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def run_path(self, run_id: str) -> Path:
        return self.base_path / run_id

    def save(self, result: BacktestResult) -> Path:
        path = self.run_path(result.metadata.run_id)
        result.save(path)
        return path

    def load(self, run_id: str) -> BacktestResult:
        path = self.run_path(run_id)
        if not path.exists():
            raise FileNotFoundError(run_id)
        return BacktestResult.load(path)

    def list_runs(self) -> list[str]:
        return sorted(
            p.name for p in self.base_path.iterdir()
            if p.is_dir()
        )