import pandas as pd

from config.backtest import INITIAL_BALANCE, StdoutMode
from core.reporting.core.contex_enricher import TradeContextEnricher
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
    Executes analytics + report rendering
    for ONE StrategyRunResult.
    """

    def __init__(
        self,
        *,
        trades: pd.DataFrame,
        df_context: pd.DataFrame,
        report_spec,
        metadata,
        config,
        report_config,
        run_path,
    ):
        self.trades = trades
        self.df_context = df_context
        self.report_spec = report_spec
        self.metadata = metadata
        self.config = config
        self.report_config = report_config
        self.run_path = run_path

        self.renderer = None

        if report_config.stdout_mode == StdoutMode.CONSOLE:
            self.renderer = StdoutRenderer()
        elif report_config.stdout_mode == StdoutMode.OFF:
            self.renderer = None
        else:
            raise NotImplementedError(
                f"StdoutMode {report_config.stdout_mode} not supported"
            )

    # ==================================================
    # MAIN
    # ==================================================

    def run(self):
        # -----------------------------
        # ANALYTICS
        # -----------------------------

        preparer = EquityPreparer(
            initial_balance=self.config.INITIAL_BALANCE
        )

        trades = preparer.prepare(self.trades)

        enricher = TradeContextEnricher(self.df_context)
        trades = enricher.enrich(
            trades,
            self.report_spec.contexts
        )

        ctx = ReportContext(
            trades=trades,
            equity=trades["equity"],
            drawdown=trades["drawdown"],
            df_plot=self.df_context,
            initial_balance=self.config.INITIAL_BALANCE,
            config=self.config,
            metadata=self.metadata,
        )

        # -----------------------------
        # REPORT COMPUTATION
        # -----------------------------

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

        # -----------------------------
        # STDOUT
        # -----------------------------

        if self.renderer is not None:
            self.renderer.render(data)

        # -----------------------------
        # PERSISTENCE
        # -----------------------------

        if self.report_config.persist_report:
            ReportPersistence(
                base_path=self.run_path / "report" / self.metadata.run_id
            ).persist(
                trades=ctx.trades,
                equity=ctx.equity,
                report_data=data,
                meta=self.metadata.to_dict(),
            )

        # -----------------------------
        # DASHBOARD
        # -----------------------------

        if self.report_config.generate_dashboard:
            DashboardRenderer(
                run_path=self.run_path / "dashboard" / self.metadata.run_id
            ).render(data, ctx)