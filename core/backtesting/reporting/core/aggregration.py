from core.backtesting.reporting.core.base import BaseAggregator
from core.backtesting.reporting.core.context import ContextSpec


class ContextualAggregator(BaseAggregator):
    def __init__(self, context: ContextSpec):
        self.context = context

    def aggregate(self, df, metrics):
        out = {}

        for value, g in df.groupby(self.context.column):
            if self.context.allowed_values and value not in self.context.allowed_values:
                continue

            out[value] = {
                m.name: m.compute(g)
                for m in metrics
            }

        return out