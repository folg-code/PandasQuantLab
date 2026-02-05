

from core.backtesting.results.result import BacktestResult
from config.backtest import INITIAL_BALANCE
from core.reporting.core.context import ReportContext
from core.reporting.core.equity import EquityPreparer
from core.reporting.core.formating import materialize
from core.reporting.core.persistence import ReportPersistence
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


class ReportRunner:
    """
    Strategy-agnostic report runner.

    Input:
    - BacktestResult (required)
    - PlotContext (optional)

    Does NOT:
    - require strategy runtime
    - require live backtest
    """

    def __init__(self, *, result, config, run_path, plot_context=None, renderer=None):
        self.result = result
        self.config = config
        self.run_path = run_path
        self.plot_context = plot_context
        self.renderer = renderer or StdoutRenderer()

    def run(self):
        # ==================================================
        # 1️⃣ PREPARE EQUITY & DRAWDOWN
        # ==================================================

        equity_preparer = EquityPreparer(
            initial_balance=self.config.INITIAL_BALANCE
        )

        trades = equity_preparer.prepare(self.result.trades)

        ctx = ReportContext(
            trades=trades,
            equity=trades["equity"],
            drawdown=trades["drawdown"],
            df_plot=self.plot_context,
            initial_balance=INITIAL_BALANCE,
            config=self.config,
            metadata=self.result.metadata,
        )

        # ==================================================
        # 2️⃣ BUILD REPORT
        # ==================================================

        report = RiskReport(
            sections=[
                BacktestConfigSection(),
                CorePerformanceSection(),
                TradeDistributionSection(),
                TailRiskSection(),
                ConditionalExpectancySection(),
                EntryTagPerformanceSection(),
                ConditionalEntryTagPerformanceSection(),
                ExitLogicDiagnosticsSection(),
                DrawdownStructureSection(),
                CapitalExposureSection(),
            ]
        )

        data = materialize(report.compute(ctx))

        # ==================================================
        # 3️⃣ STDOUT RENDER (OPTIONAL)
        # ==================================================

        if self.renderer is not None:
            self.renderer.render(data)

        # ==================================================
        # 4️⃣ PERSIST REPORT (RELATIVE TO RUN)
        # ==================================================

        report_dir = self.run_path / "report"
        report_dir.mkdir(parents=True, exist_ok=True)

        ReportPersistence(base_path=report_dir).persist(
            trades=ctx.trades,
            equity=ctx.equity,
            report_data=data,
            meta=self.result.metadata.to_dict(),
        )

        # ==================================================
        # 5️⃣ DASHBOARD (RELATIVE TO RUN)
        # ==================================================

        DashboardRenderer(run_path=self.run_path).render(data, ctx)

        print("\n✅ Dashboard built successfully\n")
