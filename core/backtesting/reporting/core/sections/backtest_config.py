from typing import Dict, Any

from core.backtesting.reporting.core.section import ReportSection
from core.backtesting.reporting.core.context import ReportContext


class BacktestConfigSection(ReportSection):
    """
    Section 1:
    Backtest Configuration & Assumptions

    Purely declarative.
    No calculations.
    No pandas.
    """

    name = "Backtest Configuration & Assumptions"

    def compute(self, ctx: ReportContext) -> Dict[str, Any]:
        return {
            "Market & Data": self._market_and_data(ctx),
            "Execution Model": self._execution_model(ctx),
            "Capital Model": self._capital_model(ctx),
        }

    # ==================================================
    # 1.1 Market & Data
    # ==================================================

    def _market_and_data(self, ctx: ReportContext) -> Dict[str, Any]:
        cfg = ctx.config

        return {
            "Instruments": getattr(cfg, "SYMBOLS", "N/A"),
            "Timeframe(s)": getattr(cfg, "TIMEFRAME", "N/A"),
            "Data source": getattr(cfg, "BACKTEST_DATA_BACKEND", "N/A"),
            "Backtest period": getattr(cfg, "TIMERANGE", "N/A"),
            "Missing data handling": "Forward-fill OHLC gaps (assumed)",
        }

    # ==================================================
    # 1.2 Execution Model
    # ==================================================

    def _execution_model(self, ctx: ReportContext) -> Dict[str, Any]:
        cfg = ctx.config

        return {
            "Order type": getattr(cfg, "ORDER_TYPE", "Market"),
            "Execution delay": getattr(cfg, "EXECUTION_DELAY", "None"),
            "Spread model": getattr(cfg, "SPREAD_MODEL", "Bid/Ask (implicit)"),
            "Slippage model": getattr(cfg, "SLIPPAGE", "None"),
        }

    # ==================================================
    # 1.3 Capital Model
    # ==================================================

    def _capital_model(self, ctx: ReportContext) -> Dict[str, Any]:
        cfg = ctx.config
        strategy = ctx.strategy

        return {
            "Starting equity": getattr(cfg, "INITIAL_BALANCE", "N/A"),
            "Position sizing method": getattr(
                strategy, "position_sizing_method", "Fixed size (implicit)"
            ),
            "Leverage": getattr(cfg, "LEVERAGE", "1x"),
            "Max concurrent positions": getattr(
                cfg, "MAX_CONCURRENT_POSITIONS", "Unlimited"
            ),
            "Capital floor / kill-switch": "None (intentional – diagnostic mode)",
        }