from config.backtest import INITIAL_BALANCE
from core.reporting.core.context import ReportContext
from core.reporting.core.equity import EquityPreparer
from core.reporting.core.formating import materialize
from core.reporting.core.persistence import ReportPersistence
from core.reporting.core.sections.backtest_config import BacktestConfigSection
from core.reporting.core.sections.capital_exposure import CapitalExposureSection
from core.reporting.core.sections.conditional_entry_tag import ConditionalEntryTagPerformanceSection
from core.reporting.core.sections.conditional_expectancy import ConditionalExpectancySection
from core.reporting.core.sections.kpi import CorePerformanceSection
from core.reporting.core.sections.drawdown_structure import DrawdownStructureSection
from core.reporting.core.sections.entry_tag_performance import EntryTagPerformanceSection
from core.reporting.core.sections.exit_logic_diagnostics import ExitLogicDiagnosticsSection
from core.reporting.core.sections.tail_risk import TailRiskSection
from core.reporting.core.sections.trade_distribution import TradeDistributionSection
from core.reporting.renders.dashboard.dashboard_renderer import DashboardRenderer
from core.reporting.renders.stdout import StdoutRenderer
from core.reporting.reports.risk import RiskReport


class ReportRunner:
    """
    Orchestrates report execution.
    Prepares ReportContext and delegates computation to RiskReport.
    """

    def __init__(self, strategy, trades_df, config, renderer=None):
        self.strategy = strategy
        self.trades_df = trades_df
        self.config = config
        self.renderer = renderer or StdoutRenderer()

    def run(self):
        # ==================================================
        # PREPARE EQUITY & DRAWDOWN
        # ==================================================

        equity_preparer = EquityPreparer(
            initial_balance=self.config.INITIAL_BALANCE
        )

        trades_with_equity = equity_preparer.prepare(self.trades_df)

        equity = trades_with_equity["equity"]
        drawdown = trades_with_equity["drawdown"]

        # ==================================================
        # BUILD REPORT CONTEXT
        # ==================================================

        ctx = ReportContext(
            trades=trades_with_equity,
            equity=equity,
            drawdown=drawdown,
            df_plot=self.strategy.df_plot,
            initial_balance=INITIAL_BALANCE,
            config=self.config,
            strategy=self.strategy,
        )


        # ==================================================
        # BUILD REPORT (SECTIONS)
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

        data = report.compute(ctx)
        data = materialize(data)

        self.renderer.render(data)

        # ==========================
        # PERSIST FOR DASHBOARD
        # ==========================

        ReportPersistence().persist(
            trades=ctx.trades,
            equity=ctx.equity,
            report_data=data,
            meta={},
        )

        DashboardRenderer().render(data, ctx)

        print("\n✅ Dashboard built successfully\n")
