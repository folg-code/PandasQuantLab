from core.backtesting.reporting.core.aggregration import ContextualAggregator
from core.backtesting.reporting.core.base import BaseReport


class RiskMonitoringReport(BaseReport):

    def __init__(self, df, metrics, contexts):
        super().__init__(df)
        self.metrics = metrics
        self.contexts = contexts

    def run(self):
        # GLOBAL
        global_stats = {
            m.name: m.compute(self.df)
            for m in self.metrics
        }

        print("\n=== GLOBAL RISK METRICS ===")
        for k, v in global_stats.items():
            print(f"{k:20s}: {v}")

        # CONTEXTUAL
        for ctx in self.contexts:
            agg = ContextualAggregator(ctx)
            stats = agg.aggregate(self.df, self.metrics)

            print(f"\n=== RISK BY {ctx.name.upper()} ===")
            for key, values in stats.items():
                print(f"\n[{key}]")
                for m, val in values.items():
                    print(f"  {m:18s}: {val}")