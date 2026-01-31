from __future__ import annotations

from typing import Dict, Any, Optional

import numpy as np
import pandas as pd

from core.backtesting.reporting.core.context import ReportContext
from core.backtesting.reporting.core.section import ReportSection


class CorePerformanceSection(ReportSection):
    name = "Core Performance Metrics"

    def compute(self, ctx: ReportContext) -> Dict[str, Any]:
        trades = self._prepare_trades(ctx)
        if trades is None:
            return {"error": "No trades available"}

        initial_balance = float(ctx.initial_balance)
        start = trades["entry_time"].iloc[0]
        end = trades["exit_time"].iloc[-1]

        total_trades = int(len(trades))
        trades_per_day = self._trades_per_day(start, end, total_trades)

        equity = trades["equity"].astype(float)
        pnl = trades["pnl_usd"].astype(float)

        final_balance = float(equity.iloc[-1])
        absolute_profit = final_balance - initial_balance
        total_return_pct = self._total_return_pct(absolute_profit, initial_balance)
        cagr_pct = self._cagr_pct(initial_balance, final_balance, start, end)

        win_loss = self._win_loss_stats(pnl)
        risk = self._risk_stats(trades, equity, initial_balance)
        streaks = self._streaks(pnl)
        costs = self._costs_kpi(trades, pnl)

        return {
            # Run info
            "Backtesting from": {"raw": str(start), "kind": "text"},
            "Backtesting to": {"raw": str(end), "kind": "text"},
            "Total trades": {"raw": total_trades, "kind": "int"},
            "Trades/day (avg)": {"raw": float(trades_per_day), "kind": "num"},

            # Capital
            "Starting balance": {"raw": initial_balance, "kind": "money"},
            "Final balance": {"raw": final_balance, "kind": "money"},
            "Absolute profit": {"raw": float(absolute_profit), "kind": "money"},
            "Total return (%)": {"raw": total_return_pct, "kind": "pct"},

            # Performance
            "CAGR (%)": {"raw": cagr_pct, "kind": "pct"},
            "Profit factor": {"raw": win_loss["profit_factor"], "kind": "num"},
            "Expectancy (USD)": {"raw": win_loss["expectancy"], "kind": "money"},
            "Win rate (%)": {"raw": win_loss["win_rate_pct"], "kind": "pct"},
            "Avg win": {"raw": win_loss["avg_win"], "kind": "money"},
            "Avg loss": {"raw": win_loss["avg_loss"], "kind": "money"},
            "Avg win/loss": {"raw": win_loss["avg_win_loss_ratio"], "kind": "num"},

            # Risk
            "Max drawdown ($)": {"raw": risk["max_dd_abs"], "kind": "money"},
            "Max drawdown (%)": {"raw": risk["max_dd_pct"], "kind": "pct"},
            "Max balance": {"raw": risk["max_balance"], "kind": "money"},
            "Min balance": {"raw": risk["min_balance"], "kind": "money"},
            "Max daily loss ($)": {"raw": risk["max_daily_loss"], "kind": "money"},
            "Max daily loss (%)": {"raw": risk["max_daily_loss_pct"], "kind": "pct"},

            # Costs & execution
            "Total costs (USD)": {"raw": costs["costs_total"], "kind": "money"},
            "Spread cost (USD)": {"raw": costs["spread_total"], "kind": "money"},
            "Slippage cost (USD)": {"raw": costs["slippage_total"], "kind": "money"},
            "Costs (bps)": {"raw": costs["costs_bps"], "kind": "num"},
            "Spread (bps)": {"raw": costs["spread_bps"], "kind": "num"},
            "Slippage (bps)": {"raw": costs["slippage_bps"], "kind": "num"},
            "Avg cost/trade (USD)": {"raw": costs["avg_cost_per_trade"], "kind": "money"},
            "Traded volume (USD)": {"raw": costs["traded_volume_total"], "kind": "money"},
            "Avg volume/trade (USD)": {"raw": costs["avg_volume_per_trade"], "kind": "money"},
            "Costs as % of gross PnL": {"raw": costs["costs_pct_gross"], "kind": "pct"},
            "Entry market share (%)": {"raw": costs["entry_market_share"], "kind": "pct"},
            "Exit market share (%)": {"raw": costs["exit_market_share"], "kind": "pct"},

            # Streaks
            "Max consecutive wins": {"raw": streaks["max_consec_wins"], "kind": "int"},
            "Max consecutive losses": {"raw": streaks["max_consec_losses"], "kind": "int"},
        }

    # -----------------------------
    # Helpers: prepare / time
    # -----------------------------
    def _prepare_trades(self, ctx: ReportContext) -> Optional[pd.DataFrame]:
        trades = getattr(ctx, "trades", None)
        if trades is None or trades.empty:
            return None

        trades = trades.copy()

        # Ensure datetimes
        trades["entry_time"] = pd.to_datetime(trades["entry_time"], utc=True)
        trades["exit_time"] = pd.to_datetime(trades["exit_time"], utc=True)

        # Sort to avoid time going backwards in downstream usage
        trades = trades.sort_values(["exit_time", "entry_time"]).reset_index(drop=True)
        return trades

    def _trades_per_day(self, start: pd.Timestamp, end: pd.Timestamp, total_trades: int) -> float:
        days = max(int((end - start).days), 1)
        return float(total_trades) / float(days)

    # -----------------------------
    # Helpers: performance
    # -----------------------------
    def _total_return_pct(self, absolute_profit: float, initial_balance: float) -> Optional[float]:
        if initial_balance <= 0:
            return None
        total_return = absolute_profit / initial_balance
        return float(100.0 * total_return) if np.isfinite(total_return) else None

    def _cagr_pct(
        self,
        initial_balance: float,
        final_balance: float,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
    ) -> Optional[float]:
        cagr = self._cagr(initial_balance, final_balance, start_time, end_time)
        return float(100.0 * cagr) if cagr is not None else None

    def _win_loss_stats(self, pnl: pd.Series) -> Dict[str, Any]:
        pnl = pnl.astype(float)

        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]

        profit_factor = (
            float(wins.sum() / abs(losses.sum()))
            if not losses.empty else None
        )

        expectancy = float(pnl.mean()) if len(pnl) else None
        win_rate = float((pnl > 0).mean()) if len(pnl) else None
        win_rate_pct = 100.0 * win_rate if win_rate is not None else None

        avg_win = float(wins.mean()) if not wins.empty else None
        avg_loss = float(losses.mean()) if not losses.empty else None  # negative
        avg_win_loss_ratio = (
            float(avg_win / abs(avg_loss))
            if (avg_win is not None and avg_loss is not None and avg_loss != 0) else None
        )

        return {
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "win_rate_pct": win_rate_pct,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "avg_win_loss_ratio": avg_win_loss_ratio,
        }

    # -----------------------------
    # Helpers: risk
    # -----------------------------
    def _risk_stats(self, trades: pd.DataFrame, equity: pd.Series, initial_balance: float) -> Dict[str, Any]:
        # Drawdown
        if "drawdown" in trades.columns:
            dd = trades["drawdown"].astype(float).values
            max_dd_abs = float(np.max(np.abs(dd))) if len(dd) else None
        else:
            max_dd_abs = None

        max_dd_pct = (
            (100.0 * max_dd_abs / initial_balance)
            if (max_dd_abs is not None and initial_balance) else None
        )

        max_balance = float(equity.max())
        min_balance = float(equity.min())

        # Daily loss (realized PnL by exit day)
        tmp = trades[["exit_time", "pnl_usd"]].copy()
        tmp["exit_day"] = tmp["exit_time"].dt.date
        daily_pnl = tmp.groupby("exit_day")["pnl_usd"].sum()

        worst_daily = float(daily_pnl.min()) if not daily_pnl.empty else None  # most negative
        max_daily_loss = float(abs(worst_daily)) if worst_daily is not None else None
        max_daily_loss_pct = (
            100.0 * max_daily_loss / initial_balance
            if (max_daily_loss is not None and initial_balance) else None
        )

        return {
            "max_dd_abs": max_dd_abs,
            "max_dd_pct": max_dd_pct,
            "max_balance": max_balance,
            "min_balance": min_balance,
            "max_daily_loss": max_daily_loss,
            "max_daily_loss_pct": max_daily_loss_pct,
        }

    # -----------------------------
    # Helpers: streaks
    # -----------------------------
    def _streaks(self, pnl: pd.Series) -> Dict[str, int]:
        pnl = pnl.astype(float)
        return {
            "max_consec_wins": self._max_consecutive(pnl > 0),
            "max_consec_losses": self._max_consecutive(pnl < 0),
        }

    def _max_consecutive(self, mask: pd.Series) -> int:
        max_run = run = 0
        for v in mask.values:
            if v:
                run += 1
                max_run = max(max_run, run)
            else:
                run = 0
        return int(max_run)

    # -----------------------------
    # Helpers: costs & execution
    # -----------------------------
    def _costs_kpi(self, trades: pd.DataFrame, pnl: pd.Series) -> Dict[str, Any]:
        def safe_sum(col: str) -> Optional[float]:
            if col not in trades.columns:
                return None
            s = pd.to_numeric(trades[col], errors="coerce").fillna(0.0)
            return float(s.sum())

        def safe_mean(col: str) -> Optional[float]:
            if col not in trades.columns or len(trades) == 0:
                return None
            s = pd.to_numeric(trades[col], errors="coerce").fillna(0.0)
            return float(s.mean())

        def bps(cost: Optional[float], vol: Optional[float]) -> Optional[float]:
            if cost is None or vol is None or vol <= 0:
                return None
            return 10000.0 * (cost / vol)

        costs_total = safe_sum("costs_usd_total")
        spread_total = safe_sum("spread_usd_total")
        slippage_total = safe_sum("slippage_usd_total")

        traded_volume_total = safe_sum("traded_volume_usd_total")
        avg_volume_per_trade = safe_mean("traded_volume_usd_total")
        avg_cost_per_trade = safe_mean("costs_usd_total")

        costs_bps = bps(costs_total, traded_volume_total)
        spread_bps = bps(spread_total, traded_volume_total)
        slippage_bps = bps(slippage_total, traded_volume_total)

        gross_pnl_total = float(pnl.astype(float).sum()) if len(pnl) else 0.0
        costs_pct_gross = None
        if costs_total is not None and gross_pnl_total != 0.0:
            costs_pct_gross = 100.0 * (costs_total / gross_pnl_total)

        entry_market_share = None
        exit_market_share = None
        if "exec_type_entry" in trades.columns:
            entry_market_share = float((trades["exec_type_entry"].astype(str) == "market").mean()) * 100.0
        if "exec_type_exit" in trades.columns:
            exit_market_share = float((trades["exec_type_exit"].astype(str) == "market").mean()) * 100.0

        return {
            "costs_total": costs_total,
            "spread_total": spread_total,
            "slippage_total": slippage_total,

            "traded_volume_total": traded_volume_total,
            "avg_volume_per_trade": avg_volume_per_trade,

            "costs_bps": costs_bps,
            "spread_bps": spread_bps,
            "slippage_bps": slippage_bps,

            "avg_cost_per_trade": avg_cost_per_trade,
            "costs_pct_gross": costs_pct_gross,

            "entry_market_share": entry_market_share,
            "exit_market_share": exit_market_share,
        }

    # -----------------------------
    # CAGR helper
    # -----------------------------
    def _cagr(
        self,
        initial_balance: float,
        final_balance: float,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
    ) -> Optional[float]:
        days = (end_time - start_time).days
        if days <= 0 or final_balance <= 0 or initial_balance <= 0:
            return None
        years = days / 365.0
        return (final_balance / initial_balance) ** (1 / years) - 1