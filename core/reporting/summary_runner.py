import json

import pandas as pd

from core.reporting.core.contex_enricher import TradeContextEnricher
from core.reporting.core.context import ReportContext
from core.reporting.core.equity import EquityPreparer
from core.reporting.core.formating import materialize
from core.reporting.core.sections.backtest_config import BacktestConfigSection
from core.reporting.core.sections.capital_exposure import CapitalExposureSection
from core.reporting.core.sections.conditional_entry_tag import ConditionalEntryTagPerformanceSection
from core.reporting.core.sections.conditional_expectancy import ConditionalExpectancySection
from core.reporting.core.sections.drawdown_structure import DrawdownStructureSection
from core.reporting.core.sections.entry_tag_performance import EntryTagPerformanceSection
from core.reporting.core.sections.exit_logic_diagnostics import ExitLogicDiagnosticsSection
from core.reporting.core.sections.kpi import CorePerformanceSection
from core.reporting.core.sections.tail_risk import TailRiskSection
from core.reporting.core.sections.trade_distribution import TradeDistributionSection
from core.reporting.renders.dashboard.dashboard_renderer import DashboardRenderer
from core.reporting.renders.stdout import StdoutRenderer
from core.reporting.reports.risk import RiskReport


class SummaryReportRunner:
    """
    Portfolio / multi-run summary report.
    SINGLE stdout. SINGLE dashboard.
    """

    def __init__(
        self,
        *,
        strategy_runs,
        trades_by_run,
        config,
        run_path,
    ):
        self.strategy_runs = strategy_runs
        self.trades_by_run = trades_by_run
        self.config = config
        self.run_path = run_path

        self.stdout_renderer = StdoutRenderer()

    def run(self):
        # ==================================================
        # AGGREGATE TRADES
        # ==================================================

        trades_all = []
        for run, trades in zip(self.strategy_runs, self.trades_by_run):
            df = trades.copy()
            df["symbol"] = run.symbol
            df["strategy_id"] = run.strategy_id
            trades_all.append(df)

        trades_all = pd.concat(trades_all).reset_index(drop=True)

        # ==================================================
        # PORTFOLIO EQUITY
        # ==================================================

        preparer = EquityPreparer(
            initial_balance=self.config.INITIAL_BALANCE
        )

        trades_all = preparer.prepare(trades_all)

        # ==================================================
        # REPORT CONTEXT (PORTFOLIO)
        # ==================================================

        ctx = ReportContext(
            trades=trades_all,
            equity=trades_all["equity"],
            drawdown=trades_all["drawdown"],
            df_plot=None,  # ❗ no candle context at portfolio level
            initial_balance=self.config.INITIAL_BALANCE,
            config=self.config,
            metadata={
                "scope": "portfolio",
                "symbols": sorted(trades_all["symbol"].unique().tolist()),
                "strategies": sorted(trades_all["strategy_id"].unique().tolist()),
            },
        )

        # ==================================================
        # REPORT
        # ==================================================

        report = RiskReport(
            sections=[
                CorePerformanceSection(),
                DrawdownStructureSection(),
                CapitalExposureSection(),
            ]
        )

        data = materialize(report.compute(ctx))

        # ==================================================
        # STDOUT (SINGLE)
        # ==================================================

        self.stdout_renderer.render(data)

        # ==================================================
        # PERSIST + DASHBOARD
        # ==================================================

        out = self.run_path / "summary"
        out.mkdir(parents=True, exist_ok=True)

        with open(out / "report.json", "w") as f:
            json.dump(data, f, indent=2, default=str)

        DashboardRenderer(run_path=out).render(data, ctx)