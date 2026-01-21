import pandas as pd


class MarketStructureEngine:
    def __init__(self, pivot_detector=None, relations=None, fibo=None, price_action=None):
        self.pivot_detector = pivot_detector
        self.relations = relations
        self.fibo = fibo
        self.price_action = price_action

    def apply(self, df):
        outputs = {}

        if self.pivot_detector:
            outputs.update(self.pivot_detector.apply(df))

        if self.relations:
            outputs.update(self.relations.apply(df))

        if self.fibo:
            outputs.update(self.fibo.apply(df))

        if self.price_action:
            outputs.update(self.price_action.apply(df))

        if outputs:
            df = df.assign(**outputs)

        return df