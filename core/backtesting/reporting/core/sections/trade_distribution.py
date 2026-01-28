import numpy as np
from typing import Dict, Any

from core.backtesting.reporting.core.section import ReportSection
from core.backtesting.reporting.core.context import ReportContext


class TradeDistributionSection(ReportSection):
    """
    Section 3:
    Trade Distribution & Payoff Geometry
    """

    name = "Trade Distribution & Payoff Geometry"

    def compute(self, ctx: ReportContext) -> Dict[str, Any]:
        trades = ctx.trades

        if trades.empty:
            return {"error": "No trades available"}

        r = self._compute_r_multiples(trades)

        buckets = self._bucketize_r(r)

        return {
            "R-multiple distribution": buckets,
            "Summary": {
                "Trades count": int(len(r)),
                "Mean R": float(np.mean(r)),
                "Median R": float(np.median(r)),
                "Positive R %": float((r > 0).mean()),
                "Negative R %": float((r < 0).mean()),
            }
        }

    # ==================================================
    # Helpers
    # ==================================================

    def _compute_r_multiples(self, trades):
        """
        Computes R-multiple per trade.
        Requires column 'returns' OR risk proxy via abs(loss).
        """

        if "returns" in trades.columns:
            return trades["returns"].astype(float)

        # fallback: pnl normalized by average loss
        losses = trades.loc[trades["pnl_usd"] < 0, "pnl_usd"].abs()

        if losses.empty:
            return np.zeros(len(trades))

        avg_loss = losses.mean()
        return trades["pnl_usd"] / avg_loss

    def _bucketize_r(self, r):
        """
        Buckets R-multiples into standard payoff geometry bins.
        """

        total = len(r)

        def pct(mask):
            return float(mask.sum() / total) if total else 0.0

        return {
            "< -1R": pct(r < -1),
            "-1R to 0": pct((r >= -1) & (r < 0)),
            "0 to +1R": pct((r >= 0) & (r < 1)),
            "+1R to +2R": pct((r >= 1) & (r < 2)),
            "> +2R": pct(r >= 2),
        }