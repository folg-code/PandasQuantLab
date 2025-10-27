import time

import pandas as pd
import talib.abstract as ta
from TechnicalAnalysis.Indicators import indicators as qtpylib
from Strategies.utils.decorators import informative
from Strategies.utils.df_trimmer import trim_all_dataframes
from Strategies.utils.informative import populate_informative_indicators
from TechnicalAnalysis.Indicators.indicators import candlestick_confirmation
from TechnicalAnalysis.PointOfInterestSMC.core import SmartMoneyConcepts
from TechnicalAnalysis.SessionsSMC.core import SessionsSMC


class PoiSessions:
    def __init__(self, df: pd.DataFrame, symbol, startup_candle_count: int = 600):
        self.startup_candle_count = startup_candle_count
        self.df = df.copy()
        self.symbol = symbol
        self.informative_dataframes = {}
        # Inicjalizacja klasy SmartMoneyConcepts
        self.smc = SmartMoneyConcepts(self.df)
        self.sessions = SessionsSMC(self.df)
        self.sessions_h1 = None

    @informative('H1')
    def populate_indicators_H1(self, df: pd.DataFrame):

        df['idx'] = df.index
        df['atr'] = ta.ATR(df, 14)


        # Aktualizujemy niezależne instancje
        self.smc.df = df.copy()
        self.smc.find_validate_zones(tf="H1")

        self.sessions_h1 = SessionsSMC(df.copy())
        self.sessions_h1.df = self.sessions_h1.calculate_previous_ranges()

        # Zwracamy coś, by merge mógł zadziałać
        return df

    def populate_indicators(self):
        self.df = self.df.rename(columns={'time_x': 'time'})
        if 'time_y' in self.df.columns:
            self.df = self.df.drop(columns=['time_y'])

        self.df['idx'] = self.df.index
        self.df['atr'] = ta.ATR(self.df, 14)
        heikinashi = qtpylib.heikinashi(self.df)
        self.df[['ha_open', 'ha_close', 'ha_high', 'ha_low']] = heikinashi[['open', 'close', 'high', 'low']]

        self.df['candle_bullish'] = qtpylib.candlestick_confirmation(self.df, 'bullish')
        self.df['candle_bearish'] = qtpylib.candlestick_confirmation(self.df, 'bearish')

        first_high = self.df['high'].shift(2)
        first_low = self.df['low'].shift(2)

        self.df['min_5'] = self.df['low'].rolling(5).min()
        self.df['max_5'] = self.df['high'].rolling(5).max()

        cisd_bull_cond = ((self.df['high'] < first_low))
        cisd_bear_cond = ((self.df['low'] > first_high))

        self.df.loc[cisd_bull_cond, 'cisd_bull_line'] = first_low
        self.df.loc[cisd_bear_cond, 'cisd_bear_line'] = first_high

        self.df[f'cisd_bull_line'] = self.df[f'cisd_bull_line'].ffill()
        self.df[f'cisd_bear_line'] = self.df[f'cisd_bear_line'].ffill()

        # Aktualizujemy również na M5
        self.smc.df = self.df.copy()
        self.smc.find_validate_zones(tf="M5")
        self.smc.detect_reaction()

        self.sessions.df = self.df.copy()
        self.sessions.calculate_sessions_ranges()

        if self.sessions_h1 is not None:
            self.sessions.df = pd.merge_asof(
                self.sessions.df.sort_values('time'),
                self.sessions_h1.df.sort_values('time'),
                on='time',
                direction='backward',
                suffixes=('', '_H1')
            )

        self.sessions.detect_session_type()
        self.sessions.detect_signals()

    def merge_external_dfs(self):
        """
        Łączy dane z:
        - self.smc.df
        - self.sessions.df
        - sygnały z self.sessions.detect_signals()

        Pomija kolumny już obecne w self.df.
        """
        base = self.df.copy()

        # --- Łączenie z self.smc.df ---
        if hasattr(self, "smc") and hasattr(self.smc, "df"):
            smc_df = self.smc.df.copy()
            new_cols = [c for c in smc_df.columns if c not in base.columns]
            if new_cols:
                base = base.merge(smc_df[['time'] + new_cols], on='time', how='left', validate='1:1')

        # --- Łączenie z self.sessions.df ---
        if hasattr(self, "sessions") and hasattr(self.sessions, "df"):
            sessions_df = self.sessions.df.copy()
            new_cols = [c for c in sessions_df.columns if c not in base.columns]
            if new_cols:
                base = base.merge(sessions_df[['time'] + new_cols], on='time', how='left', validate='1:1')

        self.df = base



    def populate_entry_trend(self):
        """
        Buduje sygnały wejścia na podstawie:
        - kierunku sesyjnego (sessions_signal)
        - stref HTF (OB, FVG, Breaker)
        - stref LTF (OB, FVG, Breaker)
        """

        df = self.df.copy()

        # --- 1️⃣ Agregacja stref bullish / bearish ---
        df['bullish_breaker_H1'] = df['bullish_breaker_reaction_H1'] | df['bullish_breaker_in_zone_H1']
        df['bullish_fvg_H1'] = df['bullish_fvg_reaction_H1'] | df['bullish_fvg_in_zone_H1']
        df['bullish_ob_H1'] = df['bullish_ob_reaction_H1'] | df['bullish_ob_in_zone_H1']

        df['bullish_breaker'] = df['bullish_breaker_reaction'] | df['bullish_breaker_in_zone']
        df['bullish_fvg'] = df['bullish_fvg_reaction'] | df['bullish_fvg_in_zone']
        df['bullish_ob'] = df['bullish_ob_reaction'] | df['bullish_ob_in_zone']

        df['bearish_breaker_H1'] = df['bearish_breaker_reaction_H1'] | df['bearish_breaker_in_zone_H1']
        df['bearish_fvg_H1'] = df['bearish_fvg_reaction_H1'] | df['bearish_fvg_in_zone_H1']
        df['bearish_ob_H1'] = df['bearish_ob_reaction_H1'] | df['bearish_ob_in_zone_H1']

        df['bearish_breaker'] = df['bearish_breaker_reaction'] | df['bearish_breaker_in_zone']
        df['bearish_fvg'] = df['bearish_fvg_reaction'] | df['bearish_fvg_in_zone']
        df['bearish_ob'] = df['bearish_ob_reaction'] | df['bearish_ob_in_zone']

        # --- 2️⃣ Określenie aktywnych stref (listy nazw) ---
        df["htf_long_active"] = df[['bullish_breaker_H1', 'bullish_ob_H1', 'bullish_fvg_H1']].apply(
            lambda x: [col.replace('bullish_', '').replace('_H1', '').upper() for col in x.index if x[col]], axis=1)
        df["ltf_long_active"] = df[['bullish_breaker', 'bullish_ob', 'bullish_fvg']].apply(
            lambda x: [col.replace('bullish_', '').upper() for col in x.index if x[col]], axis=1)

        df["htf_short_active"] = df[['bearish_breaker_H1', 'bearish_ob_H1', 'bearish_fvg_H1']].apply(
            lambda x: [col.replace('bearish_', '').replace('_H1', '').upper() for col in x.index if x[col]], axis=1)
        df["ltf_short_active"] = df[['bearish_breaker', 'bearish_ob', 'bearish_fvg']].apply(
            lambda x: [col.replace('bearish_', '').upper() for col in x.index if x[col]], axis=1)

        # --- 3️⃣ Tworzenie pustej kolumny ---
        df["signal_entry"] = None

        # --- 4️⃣ LONG: sesja = long + bullish HTF/LTF aktywne ---
        long_mask = (
                (df["sessions_signal"] == "long")
                &(df["htf_long_active"].apply(len) > 0)
                &(df["ltf_long_active"].apply(len) > 0)
               # &(df['candle_bullish'] == True)
        )


        df.loc[long_mask, "signal_entry"] = df.loc[long_mask].apply(
            lambda row: {
                "direction": "long",
                "tag": "_".join(
                    [row["session_context"]]
                    + (["HTF"] + row["htf_long_active"] if row["htf_long_active"] else [])
                    + (["LTF"] + row["ltf_long_active"] if row["ltf_long_active"] else [])
                )
            },
            axis=1
        )

        # --- 5️⃣ SHORT: sesja = short + bearish HTF/LTF aktywne ---
        short_mask = (
                (df["sessions_signal"] == "short")
                &(df["htf_short_active"].apply(len) > 0)
                &(df["ltf_short_active"].apply(len) > 0)
                #& (df['candle_bearish'] == True)
        )

        df.loc[short_mask, "signal_entry"] = df.loc[short_mask].apply(
            lambda row: {
                "direction": "short",
                "tag": "_".join(
                    [row["session_context"]]
                    + (["HTF"] + row["htf_short_active"] if row["htf_short_active"] else [])
                    + (["LTF"] + row["ltf_short_active"] if row["ltf_short_active"] else [])
                )
            },
            axis=1
        )

        # --- 6️⃣ Wyliczenie poziomów SL/TP dla aktywnych sygnałów ---
        df["levels"] = None
        has_signals = df["signal_entry"].apply(bool)
        df.loc[has_signals, "levels"] = df.loc[has_signals].apply(
            lambda row: self.calculate_levels(row["signal_entry"], row["close"]),
            axis=1
        )

        # --- 7️⃣ Zapisz wynik ---
        self.df = df


        return df

    def populate_exit_trend(self):

        df = self.df

        df['signal_exit'] = None

    def bool_series(self):
        return []

    def get_extra_values_to_plot(self):
        return [
             ("london_high", self.sessions.df["london_high"], "blue", "dot"),
             ("london_low", self.sessions.df["london_low"], "blue", "dot"),
             ("asia_high", self.sessions.df["asia_high"], "purple", "dot"),
             ("asia_low", self.sessions.df["asia_low"], "purple", "dot"),
             ("ny_high", self.sessions.df["ny_high"], "orange", "dash"),
             ("ny_low", self.sessions.df["ny_low"], "orange", "dash"),

            # ("PDH", self.sessions.df["PDH"], "blue"),
            # ("PDL", self.sessions.df["PDL"], "blue"),

            # ("PWH", self.sessions.df["PWH"], "yellow"),
            # ("PWL", self.sessions.df["PWL"], "yellow"),
        ]

    def get_bullish_zones(self):
        return [
             #("Bullish IFVG H1", self.smc.bullish_ifvg_validated_H1, "rgba(255, 160, 122, 0.7)"),
            # Pomarańcz (pozostawiony bez zmian)
             #("Bullish IFVG", self.smc.bullish_ifvg_validated, "rgba(139, 0, 0, 1)"),

             #("Bullish FVG H1", self.smc.bullish_fvg_validated_H1, "rgba(255, 152, 0, 0.7)"),  # Jasnoniebieski
             ("Bullish FVG", self.smc.bullish_fvg_validated, "rgba(255, 152, 0, 0.7)"),             # Ciemnoniebieski

            #("Bullish OB H1", self.smc.bullish_ob_validated_H1, "rgba(144, 238, 144, 0.7)"),  # Jasnozielony
             ("Bullish OB", self.smc.bullish_ob_validated, "rgba(0, 100, 0, 1)"),           # Ciemnozielony

            #("Bullish Breaker H1", self.smc.bullish_breaker_validated_H1, "rgba(173, 216, 230, 0.7)"),  # Jasnoniebieski
             ("Bullish Breaker", self.smc.bullish_breaker_validated, "rgba(0, 0, 139, 1)"),             # Ciemnoniebieski

            # ("Bullish GAP ", self.bullish_gap_validated, "rgba(56, 142, 60, 1)"),
        ]

    def get_bearish_zones(self):
        return [
             #("Bearish Breaker", self.smc.bearish_breaker_validated, "rgba(64, 64, 64, 1)"),      # Ciemnoszary
            ("Bearish Breaker H1", self.smc.bearish_breaker_validated_H1, "rgba(169, 169, 169, 0.7)"),  # Jasnoszary

             #("Bearish OB", self.smc.bearish_ob_validated, "rgba(139, 0, 0, 1)"),                # Ciemnoczerwony
            ("Bearish OB H1", self.smc.bearish_ob_validated_H1, "rgba(255, 160, 122, 0.7)"),  # Jasnoczerwony

             #("Bearish IFVG H1", self.smc.bearish_ifvg_validated_H1, "rgba(139, 0, 0, 1)"),  # Pomarańcz (pozostawiony bez zmian)
             #("Bearish IFVG", self.smc.bearish_ifvg_validated, "rgba(255, 160, 122, 0.7)"),

             ("Bearish FVG", self.smc.bearish_fvg_validated, "rgba(0, 0, 139, 1)"),      # Ciemnoszary
             #("Bearish FVG H1", self.smc.bearish_fvg_validated_H1, "rgba(173, 216, 230, 0.7)"),  # Jasnoszary
        ]

    def run(self) -> pd.DataFrame:

        timings = []  # Lista do przechowywania czasów

        def timeit(label, func):
            start = time.time()
            func()
            end = time.time()
            duration = end - start
            timings.append((label, duration))


        timeit("_populate_informative_indicators", lambda: populate_informative_indicators(self))
        timeit("self.populate_indicators()", lambda: self.populate_indicators())
        timeit("self.merge_external_dfs()", lambda: self.merge_external_dfs())
        timeit("self.populate_entry_trend()", lambda: self.populate_entry_trend())
        timeit("self.populate_exit_trend()", lambda: self.populate_exit_trend())
        timeit("trim_all_dataframes(self)", lambda: trim_all_dataframes(self))

        print("\nSummary:")
        for label, duration in timings:
            print(f"{label:<35} {duration:.4f} sec")

        self.df_plot = self.df.copy()


        # Przygotuj okrojoną wersję do backtestu
        self.df_backtest = self.df[
            ['time', 'open', 'high', 'low', 'close', 'atr', 'signal_entry', 'signal_exit', 'levels']].copy()

        return self.df_backtest

    def calculate_levels(self, signals, close):

        if not isinstance(signals, dict):
            return None

        direction = signals.get("direction")
        tag = signals.get("tag")

        risk = close * 0.001  # np. 0.1%
        rr1 = 2
        rr2 = 4

        if direction == "long":
            sl = close - risk
            tp1 = close + risk * rr1
            tp2 = close + risk * rr2
        else:
            sl = close + risk
            tp1 = close - risk * rr1
            tp2 = close - risk * rr2

        return {
            "SL": {"level": sl, "tag": "auto"},
            "TP1": {"level": tp1, "tag": "RR_1:2"},
            "TP2": {"level": tp2, "tag": "RR_1:4"},
        }