import pandas as pd


class MarketStructureEngine:
    """
    Orchestrates MarketStructure modules
    and performs batch writes to DataFrame.
    """

    def __init__(
        self,
        pivot_detector=None,
        relations=None,
        fibo=None,
        price_action=None,
    ):
        self.pivot_detector = pivot_detector
        self.relations = relations
        self.fibo = fibo
        self.price_action = price_action

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies enabled MarketStructure components
        and writes outputs to df in a batch-safe way.
        """

        outputs = {}

        if self.pivot_detector is not None:
            pivot_out = self.pivot_detector.apply(df)
            outputs.update(pivot_out)

        if self.relations is not None:
            rel_out = self.relations.apply(df)
            outputs.update(rel_out)

        if self.fibo is not None:
            fibo_out = self.fibo.apply(df)
            outputs.update(fibo_out)

        if self.price_action is not None:
            pa_out = self.price_action.apply(df)
            outputs.update(pa_out)

        # 🔑 JEDYNY MOMENT ZAPISU DO DF
        if outputs:
            df = df.assign(**outputs)

        return df