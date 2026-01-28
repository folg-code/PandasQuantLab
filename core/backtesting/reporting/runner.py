from config.backtest import INITIAL_BALANCE
from core.backtesting.reporting.core.contex_enricher import TradeContextEnricher
from core.backtesting.reporting.core.preparer import RiskDataPreparer
from core.backtesting.reporting.renders.stdout import StdoutRenderer
from core.backtesting.reporting.reports.risk import RiskMonitoringReport


class ReportRunner:
    def __init__(self, strategy, trades_df, renderer=None):
        self.strategy = strategy
        self.trades_df = trades_df
        self.renderer = renderer or StdoutRenderer()

    def run(self):
        config = self.strategy.report_config

        preparer = RiskDataPreparer(
            initial_balance=INITIAL_BALANCE
        )

        prepared_df = preparer.prepare(self.trades_df)

        enricher = TradeContextEnricher(self.strategy.df_plot)
        prepared_df = enricher.enrich(
            prepared_df,
            self.strategy.report_config.contexts
        )

        report = RiskMonitoringReport(
            df=prepared_df,
            metrics=config.metrics,
            contexts=config.contexts,
        )

        data = report.compute()
        self.renderer.render(data)