from core.backtesting.reporting.reports.risk import RiskMonitoringReport


class ReportRunner:
    def __init__(self, strategy, trades_df):
        self.strategy = strategy
        self.trades_df = trades_df

    def run(self):
        config = self.strategy.report_config

        if not config.metrics:
            return

        report = RiskMonitoringReport(
            df=self.trades_df,
            metrics=config.metrics,
            contexts=config.contexts,
        )

        report.run()