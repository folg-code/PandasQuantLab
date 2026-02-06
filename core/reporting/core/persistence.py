from pathlib import Path
import json
import pandas as pd


class ReportPersistence:
    """
    Persist report outputs INSIDE a backtest run directory.

    Contract:
    - base_path == results/backtests/{run_id}/report
    - does NOT create run_id
    - does NOT timestamp directories
    - does NOT duplicate raw trades
    """

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def persist(
        self,
        *,
        trades: pd.DataFrame,
        equity: pd.Series,
        report_data: dict,
        meta: dict | None = None,
    ) -> Path:
        """
        Persists analytics + report artifacts.

        Files written:
        - report.json
        - equity.parquet
        - meta.json
        """

        # ----------------------------
        # equity snapshot
        # ----------------------------
        equity.to_frame(name="equity").to_parquet(
            self.base_path / "equity.parquet",
            index=False,
        )

        # ----------------------------
        # report (JSON)
        # ----------------------------
        with open(self.base_path / "report.json", "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)

        # ----------------------------
        # meta
        # ----------------------------
        meta_payload = meta or {}
        with open(self.base_path / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta_payload, f, indent=2)

        return self.base_path
