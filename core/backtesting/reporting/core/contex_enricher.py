import pandas as pd

class TradeContextEnricher:
    """
    Maps candle-level context to trades.
    """

    def __init__(self, df_candles: pd.DataFrame):
        self.df_candles = df_candles.set_index("time")

    def enrich(
        self,
        trades: pd.DataFrame,
        contexts: list
    ) -> pd.DataFrame:

        df = trades.copy()

        for ctx in contexts:
            if ctx.source != "entry_candle":
                continue

            if ctx.column not in self.df_candles.columns:
                raise KeyError(
                    f"Context column '{ctx.column}' not found in df_plot"
                )

            df[ctx.name] = (
                df["entry_time"]
                .map(self.df_candles[ctx.column])
            )

        return df