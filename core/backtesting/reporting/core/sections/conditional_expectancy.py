import numpy as np
from typing import Dict, Any

from core.backtesting.reporting.core.section import ReportSection
from core.backtesting.reporting.core.context import ReportContext


class ConditionalExpectancySection(ReportSection):
    """
    Section 4.2:
    Conditional Expectancy Analysis
    """

    name = "Conditional Expectancy Analysis"

    def compute(self, ctx: ReportContext) -> Dict[str, Any]:
        trades = ctx.trades.copy()

        if trades.empty:
            return {"error": "No trades available"}

        # Ensure datetime
        trades["entry_time"] = trades["entry_time"].astype("datetime64[ns, UTC]")

        results = {}

        # ==========================
        # 1. Hour of Day
        # ==========================
        trades["hour"] = trades["entry_time"].dt.hour
        results["By hour of day"] = self._group_expectancy(
            trades, group_col="hour"
        )

        # ==========================
        # 2. Day of Week
        # ==========================
        trades["weekday"] = trades["entry_time"].dt.day_name()
        results["By day of week"] = self._group_expectancy(
            trades, group_col="weekday"
        )

        # ==========================
        # 3. Context-based (dynamic)
        # ==========================
        for col in self._detect_context_columns(trades):
            results[f"By context: {col}"] = self._group_expectancy(
                trades, group_col=col
            )

        return results

    # ==================================================
    # Helpers
    # ==================================================

    def _group_expectancy(self, trades, group_col):
        """
        Compute expectancy and winrate grouped by column.
        """

        rows = []

        for value, g in trades.groupby(group_col):
            pnl = g["pnl_usd"]

            rows.append({
                group_col: str(value),
                "Trades": int(len(g)),
                "Expectancy (USD)": float(pnl.mean()),
                "Win rate": float((pnl > 0).mean()),
                "Total PnL": float(pnl.sum()),
            })

        # Sort by expectancy
        rows = sorted(
            rows,
            key=lambda x: x["Expectancy (USD)"],
            reverse=True
        )

        return {
            "rows": rows,
            "sorted_by": "Expectancy (USD)"
        }

    def _detect_context_columns(self, trades):
        """
        Heuristically detect context columns.
        Excludes known base columns.
        """

        excluded = {
            "symbol", "direction",
            "entry_time", "exit_time",
            "entry_price", "exit_price",
            "position_size", "pnl_usd",
            "returns", "entry_tag", "exit_tag",
            "exit_level_tag", "duration", "window",
            "equity", "equity_peak", "drawdown",
            "hour", "weekday"
        }

        candidates = []

        for col in trades.columns:
            if col in excluded:
                continue
            if trades[col].dtype == object:
                candidates.append(col)

        return candidates