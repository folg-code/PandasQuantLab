from core.backtesting.reporting.core.aggregration import ContextualAggregator
from core.backtesting.reporting.core.base import BaseReport


class RiskMonitoringReport(BaseReport):

    def __init__(self, df, metrics, contexts):
        super().__init__(df)
        self.metrics = metrics
        self.contexts = contexts

    def compute(self) -> dict:
        report = {
            "global": {},
            "by_context": {}
        }

        # 1️⃣ GLOBAL METRICS
        report["global"] = {
            m.name: m.compute(self.df)
            for m in self.metrics
        }

        # 2️⃣ CONTEXTUAL METRICS
        for ctx in self.contexts:
            agg = ContextualAggregator(ctx)
            report["by_context"][ctx.name] = agg.aggregate(
                self.df,
                self.metrics
            )

        return report