import os
import contextlib
from io import StringIO
from datetime import timedelta
import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table

import pandas as pd
from rich.console import Console
from rich.table import Table
from datetime import timedelta


class BacktestReporter:

    def __init__(self, trades: pd.DataFrame, signals: pd.DataFrame, initial_balance: float):
        self.console = Console()
        self.trades = trades.copy()
        self.signals = signals
        self.initial_balance = initial_balance

        self._compute_equity_curve()
        self._prepare_trades()

    # ------------------------------------------------------------------
    # PREPARE
    # ------------------------------------------------------------------
    def _prepare_trades(self):
        required_cols = [
            "symbol", "entry_time", "exit_time",
            "entry_tag", "exit_tag",
            "pnl_usd", "returns",
            "duration"
        ]
        for c in required_cols:
            if c not in self.trades.columns:
                raise ValueError(f"Missing column in trades: {c}")

        # safety
        self.trades["entry_tag"] = self.trades["entry_tag"].fillna("UNKNOWN")
        self.trades["exit_tag"] = self.trades["exit_tag"].fillna("UNKNOWN")


    def _compute_equity_curve(self):
        # Sortowanie po czasie wyjścia
        self.trades = self.trades.sort_values(by="exit_time").reset_index(drop=True)

        # Equity curve wektorowo
        self.trades["equity"] = self.initial_balance + self.trades["pnl_usd"].cumsum()

        # Maksimum, minimum i drawdown
        self.trades["running_max"] = self.trades["equity"].cummax()
        self.trades["drawdown"] = self.trades["running_max"] - self.trades["equity"]
        self.max_balance = self.trades["equity"].max()
        self.min_balance = self.trades["equity"].min()
        self.max_drawdown = self.trades["drawdown"].max()

    # ------------------------------------------------------------------
    # CORE AGGREGATION LOGIC
    # ------------------------------------------------------------------
    def _aggregate_trades(self, df: pd.DataFrame) -> dict:
        if df.empty:
            return {
                "trades": 0,
                "avg_profit_pct": 0,
                "tot_profit_usd": 0,
                "tot_profit_pct": 0,
                "avg_duration": timedelta(0),
                "win": 0,
                "draw": 0,
                "loss": 0,
                "win_pct": 0,
                "avg_winner": 0,
                "avg_losser": 0,
                "exp": 0,
            }

        wins = df[df["pnl_usd"] > 0]
        losses = df[df["pnl_usd"] < 0]
        draws = df[df["pnl_usd"] == 0]

        win_rate = len(wins) / len(df)

        avg_win = wins["pnl_usd"].mean() if not wins.empty else 0
        avg_loss = losses["pnl_usd"].mean() if not losses.empty else 0

        expectancy = win_rate * avg_win - (1 - win_rate) * abs(avg_loss)

        return {
            "trades": len(df),
            "avg_profit_pct": df["returns"].mean() * 100,
            "tot_profit_usd": df["pnl_usd"].sum(),
            "tot_profit_pct": df["returns"].sum() * 100,
            "avg_duration": df["duration"].mean(),
            "win": len(wins),
            "draw": len(draws),
            "loss": len(losses),
            "win_pct": win_rate * 100,
            "avg_winner": avg_win,
            "avg_losser": avg_loss,
            "exp": expectancy,
        }

    # ------------------------------------------------------------------
    # GENERIC GROUP TABLE
    # ------------------------------------------------------------------
    def _print_group_table(self, title: str, group_col: str, df: pd.DataFrame):
        self.console.rule(f"[bold yellow]{title}[/bold yellow]")

        total_df = []
        stats_list = []

        # grupowanie i agregacja
        for name, g in df.groupby(group_col):
            stats = self._aggregate_trades(g)
            stats["name"] = name
            stats_list.append(stats)
            total_df.append(g)

        if not stats_list:
            print("⚠️ Brak danych do wyświetlenia.")
            return

        # sortowanie po tot_profit_usd malejąco
        stats_list = sorted(stats_list, key=lambda x: x["tot_profit_usd"], reverse=True)

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column(str(group_col))
        table.add_column("Trades", justify="right")
        table.add_column("Tot Profit USD", justify="right")
        table.add_column("Tot Profit %", justify="right")
        table.add_column("Avg Duration", justify="center")
        table.add_column("Win", justify="right")
        table.add_column("Draw", justify="right")
        table.add_column("Loss", justify="right")
        table.add_column("Win %", justify="right")
        table.add_column("Avg Winner", justify="right")
        table.add_column("Avg Losser", justify="right")
        table.add_column("Exp", justify="right")

        # dodanie wierszy do tabeli
        for stats in stats_list:
            # formatowanie avg_duration w HH:MM:SS
            avg_duration_str = str(pd.to_timedelta(stats["avg_duration"], unit='s')).split('.')[0]

            table.add_row(
                str(stats["name"]),
                f"{stats['trades']}",
                f"{stats['tot_profit_usd']:.3f}",
                f"{stats['tot_profit_pct']:.2f}",
                avg_duration_str,
                f"{stats['win']}",
                f"{stats['draw']}",
                f"{stats['loss']}",
                f"{stats['win_pct']:.1f}",
                f"{stats['avg_winner']:.2f}",
                f"{stats['avg_losser']:.2f}",
                f"{stats['exp']:.2f}"
            )

        self.console.print(table)

    def _print_summary_metrics(self):
        t = self.trades.sort_values("exit_time")

        start = t["entry_time"].min()
        end = t["exit_time"].max()

        total_trades = len(t)
        days = max((end - start).days, 1)
        trades_per_day = total_trades / days

        final_balance = t["equity"].iloc[-1]
        absolute_profit = final_balance - self.initial_balance
        total_profit_pct = (final_balance / self.initial_balance - 1) * 100
        cagr = ((final_balance / self.initial_balance) ** (365 / days) - 1) * 100

        daily_returns = t.groupby(t["exit_time"].dt.date)["pnl_usd"].sum()
        max_daily_loss = daily_returns.min()
        max_daily_loss_pct = max_daily_loss / self.initial_balance * 100

        equity = t["equity"]
        max_balance = equity.cummax()
        drawdown = max_balance - equity
        max_dd = drawdown.max()
        max_dd_pct = (drawdown / max_balance).max() * 100

        wins = t[t["pnl_usd"] > 0]
        losses = t[t["pnl_usd"] < 0]

        profit_factor = wins["pnl_usd"].sum() / abs(losses["pnl_usd"].sum()) if not losses.empty else float("inf")

        expectancy = self._aggregate_trades(t)["exp"]

        table = Table(title="SUMMARY METRICS", show_header=False)
        table.add_column("Metric")
        table.add_column("Value", justify="right")

        rows = [
            ("Backtesting from", str(start)),
            ("Backtesting to", str(end)),
            ("Total/Daily Avg Trades", f"{total_trades} / {trades_per_day:.1f}"),
            ("Starting balance", f"{self.initial_balance:.2f} USD"),
            ("Final balance", f"{final_balance:.2f} USD"),
            ("Absolute profit", f"{absolute_profit:.2f} USD"),
            ("Total profit %", f"{total_profit_pct:.2f}%"),
            ("CAGR %", f"{cagr:.2f}%"),
            ("Profit factor", f"{profit_factor:.2f}"),
            ("Expectancy", f"{expectancy:.2f}"),
            ("Max balance", f"{max_balance.max():.2f} USD"),
            ("Min balance", f"{equity.min():.2f} USD"),
            ("Absolute Drawdown", f"{max_dd:.2f} USD"),
            ("Max % underwater", f"{max_dd_pct:.2f}%"),
            ("Max daily loss $", f"{max_daily_loss:.2f} USD"),
            ("Max daily loss %", f"{max_daily_loss_pct:.2f}%"),
        ]

        for r in rows:
            table.add_row(*r)

        self.console.print(table)

    # ------------------------------------------------------------------
    # PUBLIC REPORTS
    # ------------------------------------------------------------------
    def print_entry_tag_stats(self):
        self._print_group_table("ENTER TAG STATS", "entry_tag", self.trades)

    def print_exit_reason_stats(self):
        self._print_group_table("EXIT REASON STATS", "exit_tag", self.trades)

    def print_tp1_entry_stats(self):
        df = self.trades[self.trades['tp1_price'].notna()]
        self._print_group_table(
            "ENTER TAG STATS for trades that HIT TP1",
            "entry_tag",
            df
        )

    def print_tp1_exit_stats(self):
        df = self.trades[self.trades['tp1_price'].notna()]
        self._print_group_table(
            "EXIT STATS for trades that HIT TP1",
            "exit_tag",
            df
        )

    def print_symbol_report(self):
        self._print_group_table(
            "BACKTESTING REPORT",
            "symbol",
            self.trades
        )

    # ------------------------------------------------------------------
    # RUN ALL REPORTS
    # ------------------------------------------------------------------
    def run(self):
        self.console.rule("[bold cyan]SUMMARY METRICS[/bold cyan]")

        self._print_summary_metrics()

        self.console.rule("[bold cyan]DETAILED REPORTS[/bold cyan]")

        self.print_entry_tag_stats()
        self.print_exit_reason_stats()
        self.print_tp1_entry_stats()
        self.print_tp1_exit_stats()
        self.print_symbol_report()

    def save(self, filename: str):
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        buffer = StringIO()
        with contextlib.redirect_stdout(buffer):
            self.run()

        with open(filename, "w", encoding="utf-8") as f:
            f.write(buffer.getvalue())

        print(f"✅ Raport zapisany do pliku: {filename}")
