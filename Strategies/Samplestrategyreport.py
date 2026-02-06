import pandas as pd
import talib.abstract as ta

from FeatureEngineering.Indicators import indicators as qtpylib
from FeatureEngineering.MarketStructure.engine import MarketStructureEngine
from core.reporting.core.context import ContextSpec
from core.reporting.core.metrics import ExpectancyMetric, MaxDrawdownMetric
from core.strategy.base import BaseStrategy
from core.strategy.informatives import informative


class Samplestrategyreport(BaseStrategy):

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

    strategy_config = {
        "USE_TP1": True,
        "USE_TP2": False,

        "USE_TRAILING": True,
        "TRAIL_FROM": "tp1",  # "entry" | "tp1"

        "TRAIL_MODE": "ribbon",
        "SWING_LOOKBACK": 5,

        "ALLOW_TP2_WITH_TRAILING": False,
    }

    @informative('M30')
    def populate_indicators_M30(self, df: pd.DataFrame):

        df['rma_33_low'] = qtpylib.rma(df, df['low'], 33)
        df['rma_33_high'] = qtpylib.rma(df, df['high'], 33)

        df['rma_144_low'] = qtpylib.rma(df, df['low'], 144)
        df['rma_144_high'] = qtpylib.rma(df, df['high'], 144)

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


        return df

    def populate_indicators(self) -> None:
        df = self.df


        df['atr'] = ta.ATR(df, 14)



        df['rma_33_low'] = qtpylib.rma(df, df['low'], 33)
        df['rma_33_high'] = qtpylib.rma(df, df['high'], 33)

        df['rma_144_low'] = qtpylib.rma(df, df['low'], 144)
        df['rma_144_high'] = qtpylib.rma(self.df, df['high'], 144)

        df['sl_long'] =df['rma_33_low']  #df['close'] - (1 * df['atr'])
        df['sl_short'] = df['rma_33_high'] #df['close'] + (1* df['atr'])

        df['low_5'] = df['low'].rolling(5).min()
        df['high_5'] = df['high'].rolling(5).max()
        df['low_15'] = df['low'].rolling(15).min()
        df['high_15'] = df['high'].rolling(15).max()

        df['fast_rma_upper_than_slow'] = None
        df['slow_rma_uprising'] = None
        df['fast_rma_uprising'] = None

        df['fast_rma_upper_than_slow'] = df['rma_33_low'] > df['rma_144_high']
        df['fast_rma_lower_than_slow'] = df['rma_33_high'] < df['rma_144_low']

        df['slow_rma_uprising'] = df['rma_144_low'] > df['rma_144_low'].shift(1)
        df['fast_rma_uprising'] = df['rma_33_low'] > df['rma_33_low'].shift(1)

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

        self.df = df

    def populate_entry_trend(self) -> None:
        df = self.df
        """
        Buduje sygnały wejścia łączące:
        - kierunek sesyjny (sessions_signal)
        - kierunek dnia (prev_day_direction)
        - bias rynkowy (session_bias)
        - strefy HTF/LTF (OB, FVG, Breaker)
        """



        # --- 🔹 5. Maski logiczne ---
        long_mask_rma_33 = (
                (df['close'] > df['open']) &
                (df['fast_rma_upper_than_slow']) &  # HTF trend
                (df['low'] <= df['rma_33_high']) &  # pullback into ribbon
                (df['close'] > df['rma_33_high']) &  # rejection
                (df['slow_rma_uprising'] ) &  # trend still rising
                (df['close'] > df['rma_144_low_M30'])
        )

        long_mask_rma_144 = (
                (df['close'] > df['open']) &
                (df['fast_rma_upper_than_slow']) &  # HTF trend
                (df['low'] <= df['rma_144_high']) &  # pullback into ribbon
                (df['close'] > df['rma_144_high']) &  # rejection
                (df['rma_144_low'] > df['rma_144_low'].shift(1))  # trend still rising
                & (df['close'] > df['rma_144_low_M30'])
        )

        short_mask = (
                (df['close'] < df['open']) &
                (df['rma_33_high'] < df['rma_144_low']) &  # trend down
                (df['high'] >= df['rma_33_low']) &  # pullback
                (df['close'] < df['rma_33_low']) &  # rejection
                (df['rma_33_high'] < df['rma_33_high'].shift(1))   # falling impulse
                & (df['close'] < df['rma_144_high_M30'])
        )

        short_mask_2 = (
                (df['close'] < df['open']) &
                (df['fast_rma_lower_than_slow']) &  # trend down
                (df['high'] >= df['rma_144_low']) &  # pullback
                (df['close'] < df['rma_144_low']) &  # rejection
                (df['rma_144_high'] < df['rma_144_high'].shift(1))  # falling impulse
                & (df['close'] < df['rma_144_high_M30'])
        )

        df["signal_entry"] = None

        idx = df.index[long_mask_rma_33]
        df.loc[idx, "signal_entry"] = [{"direction": "long", "tag": "LONG SETUP 1"}] * len(idx)

        idx = df.index[long_mask_rma_144]
        df.loc[idx, "signal_entry"] = [{"direction": "long", "tag": "LONG SETUP 2"}] * len(idx)

        idx = df.index[short_mask]
        df.loc[idx, "signal_entry"] = [{"direction": "short", "tag": "SHORT SETUP 1"}] * len(idx)

        idx = df.index[short_mask_2]
        df.loc[idx, "signal_entry"] = [{"direction": "short", "tag": "SHORT SETUP 2"}] * len(idx)


        # --- 🔹 7. Poziomy SL/TP ---
        has_signals = df["signal_entry"].apply(bool)
        df.loc[has_signals, "levels"] = df.loc[has_signals].apply(
            lambda row: self.calculate_levels(row["signal_entry"], row),
            axis=1
        )



        self.df = df



    def populate_exit_trend(self):
        self.df["signal_exit"] = None
        self.df["custom_stop_loss"] = None

    def compute_sl(
            self,
            *,
            row,
            direction,
            min_atr_mult=0.5,
            min_pct=0.001,
    ):
        """
        Zwraca:
        - sl_level
        - sl_source: 'struct' | 'min'
        """

        close = row["close"]
        atr = row["atr"]

        # =========================
        # SL STRUKTURALNY
        # =========================

        if direction == "long":
            sl_structural = min(row["low_15"], row["low_5"]) - atr * 0.5
        else:
            sl_structural = max(row["high_15"], row["high_5"]) + atr * 0.5

        # =========================
        # MINIMALNY SL
        # =========================

        min_sl_atr = atr * min_atr_mult
        min_sl_pct = close * min_pct
        min_distance = max(min_sl_atr, min_sl_pct)

        if direction == "long":
            sl_min = close - min_distance

            if sl_structural < sl_min:
                return sl_structural, "struct"
            else:
                return sl_min, "min"

        else:
            sl_min = close + min_distance

            if sl_structural > sl_min:
                return sl_structural, "struct"
            else:
                return sl_min, "min"

    def calculate_levels(self, signals, row):

        if not isinstance(signals, dict):
            return None

        direction = signals["direction"]
        close = row["close"]

        sl, sl_source = self.compute_sl(
            row=row,
            direction=direction,
            min_atr_mult=1,
            min_pct=0.001
        )

        risk = abs(close - sl)

        # ============================
        # MICROSTRUCTURE-AWARE TP
        # ============================

        tp1_mult = 1
        tp2_mult = 2

        if direction == "long":
            tp1_level = close + risk * tp1_mult
            tp2_level = close + risk * tp2_mult
        else:
            tp1_level = close - risk * tp1_mult
            tp2_level = close - risk * tp2_mult

        return {
            "SL": {
                "level": sl,
                "tag": f"{sl_source}"
            },
            "TP1": {
                "level": tp1_level,
                "tag": f"RR 1:{tp1_mult} from {sl_source}"
            },
            "TP2": {
                "level": tp2_level,
                "tag": f"RR 1:{tp2_mult} from {sl_source}"
            },
        }

    def build_report_spec(self):

        return (
            super()
            .build_report_spec()
            .add_metric(ExpectancyMetric())
            .add_metric(MaxDrawdownMetric())
            .add_context(
                ContextSpec(
                    name="trend regime HTF",
                    column="trend_regime_M30",
                    source="entry_candle"
                )
            )
            .add_context(
                ContextSpec(
                    name="trend regime LTF",
                    column="trend_regime",
                    source="entry_candle"
                )
            )

            .add_context(
                ContextSpec(
                    name="trend strength HTF",
                    column="trend_strength_M30",
                    source="entry_candle"
                )
            )
            .add_context(
                ContextSpec(
                    name="trend strength LTF",
                    column="trend_strength",
                    source="entry_candle"
                )
            )

            .add_context(
                ContextSpec(
                    name="trend bias HTF",
                    column="trend_bias_M30",
                    source="entry_candle"
                )
            )
            .add_context(
                ContextSpec(
                    name="trend bias LTF",
                    column="trend_bias",
                    source="entry_candle"
                )
            )
        )