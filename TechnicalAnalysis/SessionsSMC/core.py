import numpy as np
import pandas as pd


class SessionsSMC:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()



    def calculate_previous_ranges(self):

        df = self.df.copy()
        df['date'] = df['time'].dt.floor('D')  # pełna data (00:00)
        df['weekday'] = df['time'].dt.weekday
        df['week'] = df['time'].dt.isocalendar().week
        df['year'] = df['time'].dt.isocalendar().year
        df['hour'] = df['time'].dt.hour

        # MONDAY HIGH/LOW
        monday_data = df[df['weekday'] == 0].copy()
        monday_data['monday'] = monday_data['date']
        monday_ranges = monday_data.groupby(['year', 'week']).agg({
            'high': 'max',
            'low': 'min',
            'monday': 'first'
        }).reset_index()
        df = df.merge(monday_ranges, on=['year', 'week'], how='left', suffixes=('', '_monday'))
        df.rename(columns={
            'high_monday': 'monday_high',
            'low_monday': 'monday_low'
        }, inplace=True)

        # PDH/PDL (Poprzedni dzień high/low)
        daily_ranges = df.groupby('date').agg({
            'high': 'max',
            'low': 'min'
        }).rename(columns={'high': 'PDH', 'low': 'PDL'}).reset_index()

        # Shift o 1 dzień (dla poprzedniego dnia)
        daily_ranges['date'] = pd.to_datetime(daily_ranges['date'])
        daily_ranges['date_shift'] = daily_ranges['date'] + pd.Timedelta(days=1)

        df = df.merge(
            daily_ranges[['date_shift', 'PDH', 'PDL']],
            left_on='date',
            right_on='date_shift',
            how='left'
        )
        df.drop(columns=['date_shift'], inplace=True)

        # Weekly high/low (dla bieżącego tygodnia)
        weekly_ranges = df.groupby(['year', 'week']).agg({
            'high': 'max',
            'low': 'min'
        }).rename(columns={'high': 'weekly_high', 'low': 'weekly_low'}).reset_index()

        df = df.merge(weekly_ranges, on=['year', 'week'], how='left')

        # PWH/PWL (Poprzedni tydzień high/low)
        prev_weekly_ranges = weekly_ranges.copy()
        prev_weekly_ranges['week'] += 1  # uwaga: działa jeśli nie przechodzisz przez granicę roku
        prev_weekly_ranges.rename(columns={
            'weekly_high': 'PWH',
            'weekly_low': 'PWL'
        }, inplace=True)

        df = df.merge(prev_weekly_ranges[['year', 'week', 'PWH', 'PWL']], on=['year', 'week'], how='left')

        return df

    def calculate_sessions_ranges(self):
        df = self.df.copy()
        df['time'] = pd.to_datetime(df['time'], utc=True)
        df['date'] = df['time'].dt.normalize()
        df['hour'] = df['time'].dt.hour
        df = df.sort_values('time')

        # Inicjalizacja kolumn
        for s in ['asian', 'london', 'ny']:
            df[f'{s}_high'] = np.nan
            df[f'{s}_low'] = np.nan

        # Definicja godzin sesji i killzone
        sessions = {
            'asia': range(3, 11),
            'london': range(9, 18),
            'ny': range(15, 24),
        }

        # Obliczanie high/low dla każdej sesji osobno
        for session_name, hours in sessions.items():
            mask = df['hour'].isin(hours)
            for date in df.loc[mask, 'date'].unique():
                session_mask = mask & (df['date'] == date)
                highs = df.loc[session_mask, 'high'].expanding().max()
                lows = df.loc[session_mask, 'low'].expanding().min()
                df.loc[session_mask, f'{session_name}_high'] = highs.values
                df.loc[session_mask, f'{session_name}_low'] = lows.values

        # Propagacja wartości high/low z main sesji do kolejnych killzone
        for col in ['asia_high', 'asia_low', 'london_high', 'london_low', 'ny_high',
                    'ny_low']:
            df[col] = df[col].ffill()

        df.drop(columns=['hour', 'date'], inplace=True, errors='ignore')
        self.df = df

    def detect_session_type(self):
        """
        Przypisuje każdej świecy odpowiednią sesję:
        - asia_main, killzone_london, london_main, killzone_ny, ny_main
        """
        df = self.df.copy()
        df['hour'] = df['time'].dt.hour

        conditions = [
            (df['hour'] >= 3) & (df['hour'] < 9),
            (df['hour'] >= 9) & (df['hour'] < 11),
            (df['hour'] >= 11) & (df['hour'] < 15),
            (df['hour'] >= 15) & (df['hour'] < 18),
            (df['hour'] >= 18) & (df['hour'] < 24)
        ]
        choices = ['asia_main', 'killzone_london', 'london_main', 'killzone_ny', 'ny_main']

        df['session'] = np.select(conditions, choices, default='other')
        self.df = df

    def calculate_prev_day_type(self, method: str = 'percentile', percentile: float = 0.5,
                                ma_window: int = 5, atr_period: int = 14):
        """
        Określa typ dnia poprzedniego (wide/narrow) na podstawie wybranej metody.

        Metody:
        - 'percentile' : porównanie zakresu dnia do percentyla wszystkich zakresów
        - 'ma'         : porównanie zakresu dnia do średniej z ostatnich `ma_window` dni
        - 'atr'        : porównanie zakresu dnia do średniego true range (ATR) z ostatnich `atr_period` dni

        Wynik zapisywany jest w kolumnie 'prev_day_type'.
        """
        df = self.df.copy()
        df['date'] = df['time'].dt.floor('D')

        daily_ranges = df.groupby('date').agg({'high': 'max', 'low': 'min'}).reset_index()
        daily_ranges['range'] = daily_ranges['high'] - daily_ranges['low']

        if method == 'percentile':
            threshold = daily_ranges['range'].quantile(percentile)
            daily_ranges['prev_day_type'] = np.where(daily_ranges['range'] > threshold, 'wide', 'narrow')

        elif method == 'ma':
            daily_ranges['ma_range'] = daily_ranges['range'].rolling(ma_window).mean()
            daily_ranges['prev_day_type'] = np.where(daily_ranges['range'] > daily_ranges['ma_range'], 'wide', 'narrow')

        elif method == 'atr':
            daily_ranges['atr'] = daily_ranges['range'].rolling(atr_period).mean()
            daily_ranges['prev_day_type'] = np.where(daily_ranges['range'] > daily_ranges['atr'], 'wide', 'narrow')

        else:
            raise ValueError(f"Nieznana metoda '{method}'. Wybierz 'percentile', 'ma' lub 'atr'.")

        # Przesunięcie o 1 dzień do przodu, żeby kolumna odpowiadała faktycznie dnia poprzedniego
        daily_ranges['date'] += pd.Timedelta(days=1)
        df = df.merge(daily_ranges[['date', 'prev_day_type']], left_on='date', right_on='date', how='left')
        self.df = df.drop(columns=['date'], errors='ignore')

    def detect_signals(self):
        """
        Wektoryzowane generowanie sygnałów sesyjnych LONG/SHORT oraz kontekstu rynkowego.

        Metoda analizuje strukturę dnia (typ dnia poprzedniego, zakresy sesji Asia/London/NY)
        i generuje sygnały wejścia dla kluczowych stref czasowych (killzone / main session),
        bez użycia pętli — w pełni wektoryzowana logika z wykorzystaniem `numpy.select()`.

        ---
        🔹 **Założenia ogólne:**
        - Sygnały powstają w zależności od wybicia lub reakcji na poziomy:
          `asia_high`, `asia_low`, `london_high`, `london_low`, `ny_high`, `ny_low`, `PDH`, `PDL`.
        - Typ dnia (`prev_day_type`) określa szerokość ruchu z dnia poprzedniego:
          `"narrow"` (wąski zakres) lub `"wide"` (szeroki zakres).
        - Kontekst sesji (`session`) zawiera:
          `"killzone_london"`, `"london_main"`, `"killzone_ny"`, `"ny_main"`.

        ---
        🔹 **Lista sygnałów i kontekstów:**

        | # |      Sesja      |Typ dnia|Kierunek|Kontekst                | Opis logiki |
        |---|-----------------|--------|-------|-----------|-------------|
        | 1 | Killzone London | narrow | long  | `asian_high_breakout` | Wybicie powyżej `asia_high` w wąskim dniu poprzednim (kontynuacja siły). |
        | 2 | Killzone London | narrow | short | `asian_low_breakout` | Wybicie poniżej `asia_low` w wąskim dniu poprzednim (słabość rynku). |
        | 3 | Killzone London | wide   | long  | `PDL_sweep_reversal` | Fałszywe wybicie poniżej `PDL` i powrót powyżej — możliwy odwrót. |
        | 4 | Killzone London | wide   | short | `PDH_sweep_reversal` | Fałszywe wybicie powyżej `PDH` i powrót poniżej — odwrót po sile. |
        | 5 | London Main     |    -   | long  | `PDL_sweep_reversal` | Test `PDL` i odbicie — long po reakcji w Londynie. |
        | 6 | London Main     |    -   | short | `PDH_sweep_reversal` | Test `PDH` i odbicie — short po reakcji w Londynie. |
        | 7 | London Main     |    -   | long  | `london_continuation_long` | Wybicie powyżej `asia_high` i `PDH` — kontynuacja trendu wzrostowego. |
        | 8 | London Main     |    -   | short | `london_continuation_short` | Wybicie poniżej `asia_low` i `PDL` — kontynuacja trendu spadkowego. |
        | 9 | Killzone NY     |    -   | long  | `ny_reversal_long` | Test `london_low` i powrót powyżej — odwrót po spadku Londynu. |
        | 10 | Killzone NY    |    -   | short | `ny_reversal_short` | Test `london_high` i powrót poniżej — odwrót po wzroście Londynu. |
        | 11 | Killzone NY    |    -   | long  | `ny_continuation_long` | Cena utrzymuje się powyżej `london_high` — kontynuacja trendu long. |
        | 12 | Killzone NY    |    -   | short | `ny_continuation_short` | Cena utrzymuje się poniżej `london_low` — kontynuacja trendu short. |
        | 13 | NY Main        |    -   | long  | `ny_main_continuation_long` | Cena powyżej `ny_high` — silna kontynuacja trendu long. |
        | 14 | NY Main        |    -   | short | `ny_main_continuation_short` | Cena poniżej `ny_low` — silna kontynuacja trendu short.
        ---
        🔹 **Kolumny wyjściowe:**
        - `sessions_signal` → sygnał kierunkowy: `"long"` lub `"short"`
        - `session_context` → opis kontekstu formacji / logiki (np. `"PDL_sweep_reversal"`, `"ny_continuation_short"`)

        ---
        🔹 **Przykład użycia:**
        ```python
        session_model = Sessions(df)
        df_signals = session_model.detect_signals()
        print(df_signals[["time", "session", "sessions_signal", "session_context"]].dropna())
        ```

        ---
        🔹 **Przykładowy wynik:**
        ```
               time          session   sessions_signal        session_context
        45  09:30:00   killzone_london        long           asian_high_breakout
        123 11:00:00       london_main        short          PDH_sweep_reversal
        231 15:30:00         ny_main          long           ny_main_continuation_long
        ```
        """

        df = self.df.copy()

        # --- inicjalizacja kolumn ---
        df["sessions_signal"] = None
        df["session_context"] = None

        # --- przygotowanie zmiennych ---
        price = df["close"].values
        high = df["high"].values
        low = df["low"].values

        prev_day_type = df.get("prev_day_type", pd.Series(["narrow"] * len(df))).values

        asia_high = df.get("asia_high", pd.Series([np.nan] * len(df))).values
        asia_low = df.get("asia_low", pd.Series([np.nan] * len(df))).values
        london_high = df.get("london_high", pd.Series([np.nan] * len(df))).values
        london_low = df.get("london_low", pd.Series([np.nan] * len(df))).values
        ny_high = df.get("ny_high", pd.Series([np.nan] * len(df))).values
        ny_low = df.get("ny_low", pd.Series([np.nan] * len(df))).values
        pdh = df.get("PDH", pd.Series([np.nan] * len(df))).values
        pdl = df.get("PDL", pd.Series([np.nan] * len(df))).values

        session = df["session"].values

        # --- maski sesji ---
        kill_london = session == "killzone_london"
        london_main = session == "london_main"
        kill_ny = session == "killzone_ny"
        ny_main = session == "ny_main"

        # --- warunki Killzone London ---
        mask = kill_london & (prev_day_type == "narrow")
        long_kl_narrow = mask & (~np.isnan(asia_high)) & (london_high >= asia_high) #& (price > asia_high)
        short_kl_narrow = mask & (~np.isnan(asia_low)) & (london_low <= asia_low) #& (price < asia_low)

        mask = kill_london & (prev_day_type == "wide")
        short_kl_wide = mask & (~np.isnan(pdh)) & (london_high > pdh) #& (price < pdh)
        long_kl_wide = mask & (~np.isnan(pdl)) & (london_low < pdl) #& (price > pdl)

        # --- warunki London Main ---
        long_lm = london_main & (~np.isnan(pdl)) & (london_low < pdl) & (price > pdl)
        short_lm = london_main & (~np.isnan(pdh)) & (london_high > pdh) & (price < pdh)
        long_lm_cont = london_main & (~np.isnan(asia_high)) & (london_high > asia_high) & (london_high > pdh)
        short_lm_cont = london_main & (~np.isnan(asia_low)) & (london_low < asia_low) & (london_low < pdl)

        # --- warunki Killzone NY ---
        short_kny = kill_ny & (~np.isnan(london_high)) & (ny_high >= london_high) & (price < london_high)
        long_kny = kill_ny & (~np.isnan(london_low)) & (ny_low <= london_low) & (price > london_low)
        long_kny_cont = kill_ny & (~np.isnan(london_high)) & (price > london_high)
        short_kny_cont = kill_ny & (~np.isnan(london_low)) & (price < london_low)

        # --- warunki NY Main ---
        long_nym = ny_main & (~np.isnan(ny_high)) & (price > ny_high)
        short_nym = ny_main & (~np.isnan(ny_low)) & (price < ny_low)

        # --- lista warunków i wyników ---
        conditions = [
            long_kl_narrow, short_kl_narrow, long_kl_wide, short_kl_wide,
            long_lm, short_lm, long_lm_cont, short_lm_cont,
            long_kny, short_kny, long_kny_cont, short_kny_cont,
            long_nym,
            short_nym
        ]

        signals = [
            "long", "short",
            "long", "short",
            "long", "short",
            "long", "short",
            "long", "short",
            "long", "short",
            "long", "short"
        ]

        contexts = [
            "asian_high_breakout", "asian_low_breakout",
            "PDL_sweep_reversal", "PDH_sweep_reversal",
            "PDL_sweep_reversal", "PDH_sweep_reversal",
            "london_continuation_long", "london_continuation_short",
            "ny_reversal_long", "ny_reversal_short",
            "ny_continuation_long", "ny_continuation_short",
            "ny_main_continuation_long","ny_main_continuation_short"
        ]

        # --- zastosowanie np.select ---
        df["sessions_signal"] = np.select(conditions, signals, default=None)
        df["session_context"] = np.select(conditions, contexts, default=None)

        self.df = df
        return df