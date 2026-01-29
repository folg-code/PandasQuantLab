import numpy as np
from typing import Dict, Any

from core.backtesting.reporting.core.section import ReportSection
from core.backtesting.reporting.core.context import ReportContext


class ExitLogicDiagnosticsSection(ReportSection):
    """
    Section 5:
    Exit Logic Diagnostics (entry-style tagging)
    """

    name = "Exit Logic Diagnostics"

    def compute(self, ctx: ReportContext) -> Dict[str, Any]:
        trades = ctx.trades.copy()

        if trades.empty:
            return {"error": "No trades available"}

        if "exit_tag" not in trades.columns:
            return {"error": "Column 'exit_tag' not found"}

        # --------------------------------------------------
        # Compose unified exit_tag (reason + level)
        # --------------------------------------------------
        trades["exit_compound_tag"] = trades.apply(
            self._compose_exit_tag,
            axis=1
        )

        total_pnl = trades["pnl_usd"].sum()
        rows = []

        for tag, g in trades.groupby("exit_compound_tag"):
            pnl = g["pnl_usd"]

            rows.append({
                "Exit tag": str(tag),
                "Trades": int(len(g)),
                "Expectancy (USD)": float(pnl.mean()),
                "Win rate": float((pnl > 0).mean()),
                "Average PnL": float(pnl.mean()),
                "Total PnL": float(pnl.sum()),
                "Contribution to total PnL (%)": (
                    float(pnl.sum() / total_pnl) if total_pnl != 0 else np.nan
                ),
            })

        # Sort by expectancy (DESC)
        rows = sorted(
            rows,
            key=lambda x: x["Expectancy (USD)"],
            reverse=True
        )

        return {
            "rows": rows,
            "sorted_by": "Expectancy (USD)"
        }

    # ==================================================
    # Helpers
    # ==================================================

    @staticmethod
    def _compose_exit_tag(row):
        reason = row.get("exit_tag")
        level = row.get("exit_level_tag")

        if not isinstance(level, str) or level == "":
            return reason

        return f"{reason}_{level}"