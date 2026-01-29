import numpy as np
from typing import Dict, Any

from core.backtesting.reporting.core.section import ReportSection
from core.backtesting.reporting.core.context import ReportContext


class ConditionalEntryTagPerformanceSection(ReportSection):
    """
    Conditional performance of entry tags across regimes / time.
    """

    name = "Conditional Entry Tag Performance"

    def compute(self, ctx: ReportContext) -> Dict[str, Any]:
        trades = ctx.trades.copy()

        if trades.empty:
            return {"error": "No trades available"}

        if "entry_tag" not in trades.columns:
            return {"error": "entry_tag missing"}

        # Ensure datetime
        trades["entry_time"] = trades["entry_time"].astype("datetime64[ns, UTC]")
        trades["hour"] = trades["entry_time"].dt.hour
        trades["weekday"] = trades["entry_time"].dt.day_name()

        results = {}

        # -----------------------------------
        # 1. By market regime (all contexts)
        # -----------------------------------
        for col in self._detect_context_columns(trades):
            results[f"By {col}"] = self._by_context(trades, col)

        # -----------------------------------
        # 2. By hour of day
        # -----------------------------------
        results["By hour"] = self._by_context(trades, "hour")

        return results

    # ==================================================
    # Core logic
    # ==================================================

    def _by_context(self, trades, context_col):
        rows = []

        grouped = trades.groupby(["entry_tag", context_col])

        for (tag, ctx_val), g in grouped:
            pnl = g["pnl_usd"]

            rows.append({
                "Entry tag": str(tag),
                "Context": str(ctx_val),
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
            "sorted_by": "Expectancy (USD)",
            "context": context_col,
        }

    def _detect_context_columns(self, trades):
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

        return [
            c for c in trades.columns
            if c not in excluded and trades[c].dtype == object
        ]