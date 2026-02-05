import pandas as pd
import talib.abstract as ta

from core.backtesting.reporting.core.context import ContextSpec
from core.backtesting.reporting.core.metrics import ExpectancyMetric, MaxDrawdownMetric
from FeatureEngineering.MarketStructure.engine import MarketStructureEngine
from core.strategy.base import BaseStrategy
from core.strategy.informatives import informative

class Samplestrategy(BaseStrategy):

    def __init__(
            self,
            df,
            symbol,
            startup_candle_count,
    ):
        super().__init__(
            df=df,
            symbol=symbol,
            startup_candle_count=startup_candle_count,
        )

    @informative("M30")
    def populate_indicators_M30(self, df):

        df = df.copy()
        # --- minimum techniczne
        df["atr"] = ta.ATR(df, 14)

        # --- market structure HTF
        df = MarketStructureEngine.apply(
            df,
            features=[
                "pivots",
                "price_action",
                "follow_through",
                "structural_vol",
                "trend_regime",
            ],
        )

        # --- bias flags (czytelne na GitHubie)
        df["bias_long"] = df["trend_regime"] == "trend_up"
        df["bias_short"] = df["trend_regime"] == "trend_down"

        return df


    def populate_indicators(self):

        df = self.df.copy()
        # --- base indicators
        df["atr"] = ta.ATR(df, 14)

        # --- market structure
        df = MarketStructureEngine.apply(
            df,
            features=[
                "pivots",
                "price_action",
                "follow_through",
                "structural_vol",
                "trend_regime",
            ],
        )

        df['low_15'] = df['low'].rolling(15).min()
        df['high_15'] = df['high'].rolling(15).max()

        self.df = df

    def populate_entry_trend(self):

        df = self.df.copy()




        # =====================
        # LONG CONTINUATION SETUP
        # =====================
        setup_continuation_long = (
                #df["bias_long_M30"]  #
                 (df["trend_regime"] == "trend_up")
                & df["bos_bull_event"]
                & df["bos_bull_ft_valid"]
               # & (df["bos_bull_struct_vol"] == "high")
        )

        trigger_continuation_long = (
            setup_continuation_long
            & (df["close"] > df["open"])
        )

        # =====================
        # LONG MEAN REVERSION SETUP
        # =====================



        # =====================
        # SHORT CONTINUATION SETUP
        # =====================

        setup_mr_long = df["close"] > df["open"]
        setup_continuation_short = df["close"] < df["open"]

        df["signal_entry"] = None

        idx = df.index[setup_mr_long]

        df.loc[idx, "signal_entry"] = pd.Series(
            [{"direction": "long", "tag": "long"}] * len(idx),
            index=idx
        )

        idx = df.index[setup_continuation_short]

        df.loc[idx, "signal_entry"] = pd.Series(
            [{"direction": "short", "tag": "short"}] * len(idx),
            index=idx
        )

        df["levels"] = None


        df.loc[df['signal_entry'].notna(), "levels"] = df.loc[df['signal_entry'].notna()].apply(
            lambda row: self.calculate_levels(
                row["signal_entry"],
                row["close"],
                row["low_15"],
                row['high_15']
            ),
            axis=1
        )

        print(df["signal_entry"].notna().sum())

        self.df = df




        return df

    def build_report_config(self):
        return (
            super()
            .build_report_config()
            .add_metric(ExpectancyMetric())
            .add_metric(MaxDrawdownMetric())
            .add_context(
                ContextSpec(
                    name="bos_bear_struct_vol",
                    column="bos_bear_struct_vol",
                    source="entry_candle"
                )
            )
            .add_context(
                ContextSpec(
                    name="trend_regime",
                    column="trend_regime",
                    source="entry_candle"
                )
            )
        )

    def populate_exit_trend(self):
        self.df["signal_exit"] = None
        self.df["custom_stop_loss"] = None


    def calculate_levels(self, signals, close, sl_long, sl_short):

        if not isinstance(signals, dict):
            return None

        direction = signals.get("direction")
        tag = signals.get("tag")

        if direction == "long":
            sl = sl_long
            tp1 = close + (close - sl_long) * 1
            tp2 = close + (close - sl_long) * 2
        else:
            sl = sl_short
            tp1 = close - (sl_short - close) * 1
            tp2 = close - (sl_short - close) * 2

        return {
            "SL": {"level": sl, "tag": "auto"},
            "TP1": {"level": tp1, "tag": "RR_1:2"},
            "TP2": {"level": tp2, "tag": "RR_1:4"},
        }