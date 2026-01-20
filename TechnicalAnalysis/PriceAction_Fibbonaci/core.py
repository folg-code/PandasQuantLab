import numpy as np
import pandas as pd
import talib.abstract as ta
from debugpy.launcher.debuggee import describe


class IntradayMarketStructure:
    def __init__(
        self,
        pivot_range: int = 15,
        min_percentage_change: float = 0.01
    ):
        self.pivot_range = pivot_range
        self.min_percentage_change = min_percentage_change

    # =============================================================
    # 1️⃣ DETEKCJA PIVOTÓW
    # =============================================================
    def detect_peaks(self, df):

        pivot_range = self.pivot_range

        df['rsi'] = ta.RSI(df, pivot_range)
        df['atr'] = ta.ATR(df, pivot_range)
        df['idx'] = np.arange(len(df))

        ############################## DETECT PIVOTS ##############################
        local_high_price = (
                (df["high"].rolling(window=pivot_range).max().shift(pivot_range + 1) <= df["high"].shift(
                    pivot_range)) &
                (df["high"].rolling(window=pivot_range).max() <= df["high"].shift(pivot_range))
        )
        local_low_price = (
                ((df["low"].rolling(window=pivot_range).min()).shift(pivot_range + 1) >= df["low"].shift(
                    pivot_range)) &
                (df["low"].rolling(window=pivot_range).min() >= df["low"].shift(pivot_range))
        )

        df.loc[local_high_price, 'pivotprice'] = df['high'].shift(pivot_range)
        df.loc[local_low_price, 'pivotprice'] = df['low'].shift(pivot_range)

        df.loc[local_high_price, 'pivot_body'] = (
            df[['open', 'close']].max(axis=1).rolling(int(pivot_range)).max()).shift(int(pivot_range / 2))
        df.loc[local_low_price, 'pivot_body'] = (
            df[['open', 'close']].min(axis=1).rolling(int(pivot_range)).min()).shift(int(pivot_range / 2))

        HH_condition = local_high_price & (
                df.loc[local_high_price, 'pivotprice'] > df.loc[local_high_price, 'pivotprice'].shift(1))
        LL_condition = local_low_price & (
                df.loc[local_low_price, 'pivotprice'] < df.loc[local_low_price, 'pivotprice'].shift(1))
        LH_condition = local_high_price & (
                df.loc[local_high_price, 'pivotprice'] < df.loc[local_high_price, 'pivotprice'].shift(1))
        HL_condition = local_low_price & (
                df.loc[local_low_price, 'pivotprice'] > df.loc[local_low_price, 'pivotprice'].shift(1))

        df.loc[local_high_price, f'pivot'] = 1
        df.loc[local_low_price, f'pivot'] = 2
        df.loc[HH_condition, f'pivot'] = 3
        df.loc[LL_condition, f'pivot'] = 4
        df.loc[LH_condition, f'pivot'] = 5
        df.loc[HL_condition, f'pivot'] = 6

        df.loc[df[f'pivot'] == 3, f'HH_idx'] = df['idx']
        df.loc[df[f'pivot'] == 4, f'LL_idx'] = df['idx']
        df.loc[df[f'pivot'] == 5, f'LH_idx'] = df['idx']
        df.loc[df[f'pivot'] == 6, f'HL_idx'] = df['idx']

        df[f'HH_idx'] = df[f'HH_idx'].ffill()
        df[f'LL_idx'] = df[f'LL_idx'].ffill()
        df[f'LH_idx'] = df[f'LH_idx'].ffill()
        df[f'HL_idx'] = df[f'HL_idx'].ffill()




        ############################## MARK VALUES ##############################
        df.loc[df[f'pivot'] == 3, f'HH'] = df['pivotprice']
        df.loc[df[f'pivot'] == 4, f'LL'] = df['pivotprice']
        df.loc[df[f'pivot'] == 5, f'LH'] = df['pivotprice']
        df.loc[df[f'pivot'] == 6, f'HL'] = df['pivotprice']

        df[f'HH'] = df[f'HH'].ffill()
        df[f'LL'] = df[f'LL'].ffill()
        df[f'LH'] = df[f'LH'].ffill()
        df[f'HL'] = df[f'HL'].ffill()

        df[f'HH_shift'] = df.loc[df[f'pivot'] == 3, 'pivotprice'].shift(1)
        df[f'LL_shift'] = df.loc[df[f'pivot'] == 4, 'pivotprice'].shift(1)
        df[f'LH_shift'] = df.loc[df[f'pivot'] == 5, 'pivotprice'].shift(1)
        df[f'HL_shift'] = df.loc[df[f'pivot'] == 6, 'pivotprice'].shift(1)

        df[f'HH_shift'] = df[f'HH_shift'].ffill()
        df[f'LL_shift'] = df[f'LL_shift'].ffill()
        df[f'LH_shift'] = df[f'LH_shift'].ffill()
        df[f'HL_shift'] = df[f'HL_shift'].ffill()

        df[f'HH_idx_shift'] = df.loc[df[f'pivot'] == 3, 'idx'].shift(1)
        df[f'LL_idx_shift'] = df.loc[df[f'pivot'] == 4, 'idx'].shift(1)
        df[f'LH_idx_shift'] = df.loc[df[f'pivot'] == 5, 'idx'].shift(1)
        df[f'HL_idx_shift'] = df.loc[df[f'pivot'] == 6, 'idx'].shift(1)

        df[f'HH_idx_shift'] = df[f'HH_idx_shift'].ffill()
        df[f'LL_idx_shift'] = df[f'LL_idx_shift'].ffill()
        df[f'LH_idx_shift'] = df[f'LH_idx_shift'].ffill()
        df[f'HL_idx_shift'] = df[f'HL_idx_shift'].ffill()


        """

        buy_liq_cond = (
                ((df[f'pivot'] == 6)
                 & (df[f'HL_spread'] < 20)
                 ) |
                ((df[f'pivot'] == 4)
                 & (df[f'LL_spread'] < 20)
                 )
        )

        buy_liq = df.loc[buy_liq_cond, ['pivotprice', 'pivot_body', 'idx', 'time']]

        # Warunek dla bearish OB (pivot 3 = HH, pivot 5 = LH)
        sell_liq_cond = (
                ((df[f'pivot'] == 3)
                 & (df[f'HH_spread'] < 20)
                 ) |
                ((df[f'pivot'] == 5)
                 & (df[f'LH_spread'] < 20)
                 )
        )

        sell_liq = df.loc[sell_liq_cond, ['pivotprice', 'pivot_body', 'idx', 'time']]

        buy_liq_renamed = buy_liq.rename(columns={'pivotprice': 'low_boundary', 'pivot_body': 'high_boundary'})

        bearish_ob_renamed = sell_liq.rename(columns={'pivotprice': 'high_boundary', 'pivot_body': 'low_boundary'})

        """
        return df

    def detect_eqh_eql_from_pivots(
            self,
            df: pd.DataFrame,
            eq_atr_mult: float = 0.2,
            prefix: str = ""
    ) -> pd.DataFrame:
        """
        Detect Equal High (EQH) and Equal Low (EQL) levels based purely on
        pivot structure (HH, LH, LL, HL) using vectorized pandas logic only.

        Assumptions:
        - Pivot columns already exist and are forward-filled:
            HH, LH, LL, HL
            HH_idx, LH_idx, LL_idx, HL_idx
        - atr exists
        - No loops, no apply, no candle logic

        Output columns:
        - EQH (bool)
        - EQL (bool)
        - EQH_level (float)
        - EQL_level (float)
        """


        # =========================
        # Threshold
        # =========================
        eq_threshold = df['atr'] * eq_atr_mult

        # =========================
        # EQH: HH–HH
        # =========================
        eqh_hh = (
                (df['HH_idx'].notna()) &
                (df['HH_idx_shift'].notna()) &
                (df['HH_idx'] != df['HH_idx_shift']) &
                ((df['HH'] - df['HH_shift']).abs() <= eq_threshold)
        )

        # =========================
        # EQH: HH–LH
        # =========================
        eqh_hh_lh = (
                (df['LH_idx'].notna()) &
                (df['HH_idx'].notna()) &
                (df['LH_idx'] > df['HH_idx']) &
                (df['LH_idx'] != df['LH_idx_shift']) &
                ((df['LH'] - df['HH']).abs() <= eq_threshold)
        )

        df[f'{prefix}EQH'] = eqh_hh | eqh_hh_lh

        # EQH level
        df[f'{prefix}EQH_level'] = np.where(
            eqh_hh, df['HH'],
            np.where(eqh_hh_lh, df['HH'], np.nan)
        )
        df[f'{prefix}EQH_level'] = df[f'{prefix}EQH_level'].ffill()

        # =========================
        # EQL: LL–LL
        # =========================
        eql_ll = (
                (df['LL_idx'].notna()) &
                (df['LL_idx_shift'].notna()) &
                (df['LL_idx'] != df['LL_idx_shift']) &
                ((df['LL'] - df['LL_shift']).abs() <= eq_threshold)
        )

        # =========================
        # EQL: LL–HL
        # =========================
        eql_ll_hl = (
                (df['HL_idx'].notna()) &
                (df['LL_idx'].notna()) &
                (df['HL_idx'] > df['LL_idx']) &
                (df['HL_idx'] != df['HL_idx_shift']) &
                ((df['HL'] - df['LL']).abs() <= eq_threshold)
        )

        df[f'{prefix}EQL'] = eql_ll | eql_ll_hl

        # EQL level
        df[f'{prefix}EQL_level'] = np.where(
            eql_ll, df['LL'],
            np.where(eql_ll_hl, df['LL'], np.nan)
        )
        df[f'{prefix}EQL_level'] = df[f'{prefix}EQL_level'].ffill()



        return df

    # =============================================================
    # 2️⃣ DETEKCJA POZIOMÓW FIBO
    # =============================================================
    def detect_fibo(self, df):


        HH, LL, LH, HL = df[f'HH'], df[f'LL'], df[f'LH'], df[
            f'HL']
        HH_idx, LL_idx, LH_idx, HL_idx = (
            df[f'HH_idx'], df[f'LL_idx'],
            df[f'LH_idx'], df[f'HL_idx']
        )

        # Lokalne poziomy
        df[f'last_low'] = np.where(LL_idx > HL_idx, LL, HL)
        df[f'last_high'] = np.where(HH_idx > LH_idx, HH, LH)
        rise = df[f'last_high'] - df[f'last_low']

        cond_up = df[f'last_low'] < df[f'last_high']
        cond_down = ~cond_up
        fib_levels = [0.5, 0.618, 0.66, 1.272, 1.618]

        for coeff in fib_levels:
            df.loc[cond_up, f'fibo_local_{str(coeff).replace(".", "")}'] = (
                    df[f'last_high'] - rise * coeff
            )
            df.loc[cond_down, f'fibo_local_{str(coeff).replace(".", "")}_bear'] = (
                    df[f'last_low'] + rise * coeff
            )

        df['range_mid'] = np.where(
            cond_up,
            df['fibo_local_05'],
            df['fibo_local_05_bear']
        )

        df['in_discount'] = df['low'] < df['range_mid']
        df['in_premium'] = df['high'] > df['range_mid']

        return df

    # =============================================================
    # 3️⃣ DETEKCJA PRICE ACTION
    # =============================================================



    def detect_trend_regime(
        self,
        df,
        atr_mult: float = 1.0,
    ):
        """
        Finite State Machine (FSM) – Structural Market Regime Detector

        CEL FUNKCJI
        -----------
        Wykrywa i utrzymuje aktualny reżim rynku (bull / bear / range)
        w sposób deterministyczny, wydajny i odporny na szum,
        bazując WYŁĄCZNIE na strukturze (BOS / MSS) oraz potwierdzonym momentum.

        Funkcja stanowi FUNDAMENT warstwy "State Layer".
        NIE generuje sygnałów i NIE podejmuje decyzji tradingowych.

        ------------------------------------------------------------------
        INPUT
        ------------------------------------------------------------------
        df:
            DataFrame zawierający zdarzenia strukturalne HTF:
            - bos_bull_event : bool
            - bos_bear_event : bool
            - mss_bull_event : bool
            - mss_bear_event : bool
            - follow_through_atr : float
              (miara displacementu / momentum po BOS)

        atr_mult:
            Minimalny próg follow-through wymagany, aby BOS
            został uznany za strukturalnie ważny.
            Chroni FSM przed fake breakoutami.

        ------------------------------------------------------------------
        LOGIKA FSM (UPROSZCZONA)
        ------------------------------------------------------------------
        range:
            BOS bull + follow-through  → bull
            BOS bear + follow-through  → bear

        bull:
            BOS bear + follow-through  → bear   (FLIP)
            MSS bear                  → range  (CANCEL)

        bear:
            BOS bull + follow-through  → bull   (FLIP)
            MSS bull                  → range  (CANCEL)

        FSM NIE:
        - zgaduje przyszłości
        - nie używa rolling / ffill
        - nie reaguje na pojedyncze bary momentum

        ------------------------------------------------------------------
        OUTPUT FEATURES (KLUCZOWE)
        ------------------------------------------------------------------

        market_regime : {'range', 'bull', 'bear'}
            Aktualny stan strukturalny rynku.
            Jest JEDYNYM źródłem prawdy o kierunku struktury.
            NIE jest sygnałem.

        trend_active : bool
            True gdy market_regime ∈ {'bull', 'bear'}.
            Używane WYŁĄCZNIE jako filtr środowiska,
            nigdy jako trigger wejścia.

        regime_duration : int
            Liczba barów spędzonych w AKTUALNYM reżimie.
            Resetowana przy każdym flipie lub cancelu.

            Zastosowanie:
            - odróżnienie fake trendów od dojrzałych
            - filtrowanie zbyt krótkich struktur

        regime_flip : bool
            True TYLKO na barze, w którym nastąpił flip
            (bull ↔ bear).

            Interpretacja:
            - bar zmiany dominującej struktury
            - najwyższe ryzyko chaosu
            - NIE MIEJSCE na wejścia trendowe

        regime_cancel : bool
            True na barze, gdzie trend został anulowany
            przez MSS (powrót do range).

            Interpretacja:
            - utrata struktury
            - potencjalna akumulacja / dystrybucja
            - brak biasu kierunkowego

        regime_age_norm : float
            Znormalizowany wiek reżimu:
                regime_duration / mean(duration | regime)

            Co oznacza:
            - < 0.5 → bardzo świeży (wysokie ryzyko fake)
            - 0.5–1.2 → zdrowy
            - > 1.5 → dojrzały / potencjalnie zmęczony

            Użycie:
            - filtr jakości trendu
            - adaptacja TP / SL
            - ważenie kontekstu

            NIE JEST:
            - predyktorem flipu
            - sygnałem wejścia

        bars_since_flip : int
            Liczba barów od ostatniego FLIPU reżimu.

            Co mierzy:
            - stabilność struktury po zmianie dominacji

            Interpretacja:
            - 0–3  → chaos po flipie
            - 5–12 → struktura stabilna (optymalna dla entry)
            - >20  → dojrzały trend, mniejszy potencjał RR

            Użycie:
            - gating HTF (np. bars_since_flip >= 8)
            - modulacja ryzyka
            - confidence score kontekstu

        ------------------------------------------------------------------
        JAK UŻYWAĆ TEJ FUNKCJI
        ------------------------------------------------------------------
        - zawsze PRZED generacją sygnałów
        - jako warstwa nadrzędna (HTF bias)
        - w połączeniu z:
            * price action context
            * entry logic
            * risk engine

        ------------------------------------------------------------------
        JAK NIE UŻYWAĆ
        ------------------------------------------------------------------
        - NIE traktować żadnego outputu jako sygnału
        - NIE próbować przewidywać flipów
        - NIE łączyć FSM z rolling ffill logic

        ------------------------------------------------------------------
        FILOZOFIA
        ------------------------------------------------------------------
        Ta funkcja odpowiada wyłącznie na pytanie:

            "JAKA jest aktualna struktura rynku
             i jak stabilna ona jest?"

        Decyzje tradingowe należą do kolejnych warstw.
        """

        n = len(df)

        bos_bull = df['bos_bull_event'].values
        bos_bear = df['bos_bear_event'].values
        mss_bull = df['mss_bull_event'].values
        mss_bear = df['mss_bear_event'].values
        follow = df['follow_through_atr'].values

        regime = np.empty(n, dtype=np.int8)
        duration = np.zeros(n, dtype=np.int32)
        flip = np.zeros(n, dtype=bool)
        cancel = np.zeros(n, dtype=bool)

        # encoding:
        # 0 = range, 1 = bull, -1 = bear
        state = 0
        dur = 0

        for i in range(n):

            follow_ok = follow[i] >= atr_mult

            if state == 0:  # RANGE
                if bos_bull[i] and follow_ok:
                    state = 1
                    dur = 1
                elif bos_bear[i] and follow_ok:
                    state = -1
                    dur = 1
                else:
                    dur += 1

            elif state == 1:  # BULL
                if bos_bear[i] and follow_ok:
                    state = -1
                    dur = 1
                    flip[i] = True
                elif mss_bear[i]:
                    state = 0
                    dur = 1
                    cancel[i] = True
                else:
                    dur += 1

            elif state == -1:  # BEAR
                if bos_bull[i] and follow_ok:
                    state = 1
                    dur = 1
                    flip[i] = True
                elif mss_bull[i]:
                    state = 0
                    dur = 1
                    cancel[i] = True
                else:
                    dur += 1

            regime[i] = state
            duration[i] = dur

        # map back to labels
        mapping = np.array(['range', 'bull', 'bear'])
        df['market_regime'] = mapping[(regime + 1)]
        df['regime_duration'] = duration
        df['regime_flip'] = flip
        df['regime_cancel'] = cancel
        df['trend_active'] = regime != 0

        df['regime_age_norm'] = (
                df['regime_duration'] /
                df.groupby('market_regime')['regime_duration'].transform('mean')
        )

        df[df.regime_flip].groupby('market_regime')['regime_duration'].mean()

        df['bars_since_flip'] = (
            df['regime_flip']
            .astype(int)
            .groupby(df['market_regime'])
            .cumsum()
        )

    def detect_price_action(self, df):
        """
        Price Action detection with explicit EVENT vs STATE separation.

        Outputs per structure:
        - *_event        : True only on event bar
        - *_level        : price level created by event (ffilled)
        - *_event_idx    : index of event bar (ffilled, state)
        """

        actions = [
            # MSS
            {
                'name': 'mss_bull',
                'cond': (df['close'] > df['LH']) & (df['close'].shift(1) <= df['LH']),
                'level': df['LH'],
            },
            {
                'name': 'mss_bear',
                'cond': (df['close'] < df['HL']) & (df['close'].shift(1) >= df['HL']),
                'level': df['HL'],
            },

            # BOS
            {
                'name': 'bos_bull',
                'cond': (df['close'] > df['HH']) & (df['close'].shift(1) <= df['HH']),
                'level': df['HH'],
            },
            {
                'name': 'bos_bear',
                'cond': (df['close'] < df['LL']) & (df['close'].shift(1) >= df['LL']),
                'level': df['LL'],
            },
        ]

        for act in actions:
            name = act['name']

            # ==========================
            # EVENT (impulse)
            # ==========================
            df[f'{name}_event'] = act['cond']

            # ==========================
            # LEVEL CREATED BY EVENT
            # ==========================
            df[f'{name}_level'] = np.where(
                act['cond'],
                act['level'],
                np.nan
            )

            # ==========================
            # EVENT INDEX (STATEFUL)
            # ==========================
            df[f'{name}_event_idx'] = np.where(
                act['cond'],
                df.index,
                np.nan
            )

            # ==========================
            # FORWARD FILL STATE
            # ==========================
            df[f'{name}_level'] = df[f'{name}_level'].ffill()
            df[f'{name}_event_idx'] = df[f'{name}_event_idx'].ffill()

        print(df[[
            'bos_bull_event_idx', 'bos_bear_event_idx',
            'mss_bull_event_idx', 'mss_bear_event_idx', 'HL'
        ]].tail(200))



        return df

    def generate_price_action_context(self, df):
        """
        Priority-aware PA event generator.

        Rules:
        - BOS has absolute priority
        - MSS is ignored for N bars after BOS
        """

        df['pa_event_type'] = None
        df['pa_event_dir'] = None
        df['pa_event_idx'] = np.nan
        df['pa_level'] = np.nan

        bos_bull = df['bos_bull_event']
        bos_bear = df['bos_bear_event']

        # ==========================
        # BOS (ABSOLUTE PRIORITY)
        # ==========================
        df.loc[bos_bull, 'pa_event_type'] = 'bos'
        df.loc[bos_bull, 'pa_event_dir'] = 'bull'
        df.loc[bos_bull, 'pa_event_idx'] = df.loc[bos_bull, 'bos_bull_event_idx']
        df.loc[bos_bull, 'pa_level'] = df.loc[bos_bull, 'bos_bull_level']

        df.loc[bos_bear, 'pa_event_type'] = 'bos'
        df.loc[bos_bear, 'pa_event_dir'] = 'bear'
        df.loc[bos_bear, 'pa_event_idx'] = df.loc[bos_bear, 'bos_bear_event_idx']
        df.loc[bos_bear, 'pa_level'] = df.loc[bos_bear, 'bos_bear_level']

        # ==========================
        # MSS (ONLY IF NO RECENT BOS)
        # ==========================
        NO_RECENT_BOS = df['bars_since_bos'] > 2  # ← kluczowy parametr

        mss_bull = df['mss_bull_event'] & NO_RECENT_BOS & df['pa_event_type'].isna()
        mss_bear = df['mss_bear_event'] & NO_RECENT_BOS & df['pa_event_type'].isna()

        df.loc[mss_bull, 'pa_event_type'] = 'mss'
        df.loc[mss_bull, 'pa_event_dir'] = 'bull'
        df.loc[mss_bull, 'pa_event_idx'] = df.loc[mss_bull, 'mss_bull_event_idx']
        df.loc[mss_bull, 'pa_level'] = df.loc[mss_bull, 'mss_bull_level']

        df.loc[mss_bear, 'pa_event_type'] = 'mss'
        df.loc[mss_bear, 'pa_event_dir'] = 'bear'
        df.loc[mss_bear, 'pa_event_idx'] = df.loc[mss_bear, 'mss_bear_event_idx']
        df.loc[mss_bear, 'pa_level'] = df.loc[mss_bear, 'mss_bear_level']

        df['pa_event_idx'] = df['pa_event_idx'].ffill()
        df['pa_event_type'] = df['pa_event_type'].ffill()
        df['pa_event_dir'] = df['pa_event_dir'].ffill()
        df['pa_level'] = df['pa_level'].ffill()

        return df

    # ==========================
    # PA CONTEXT PARAMETERS
    # ==========================

    def enrich_pa_context(self, df):

        PA_COUNTER_MAX_BARS = 10
        PA_COUNTER_ATR_MULT = 2

        PA_CONT_MIN_BARS = 3
        PA_CONT_MIN_ATR = 0.8
        PA_CONT_MAX_ATR = 2.5



        # TIME SINCE PA EVENT
        df['bars_since_pa'] = df['idx']- df['pa_event_idx']

        print(df[['idx', 'pa_event_idx', 'bars_since_pa']].tail(20))

        # DISTANCE FROM PA LEVEL
        df['pa_dist'] = abs(df['close'] - df['pa_level'])
        df['pa_dist_atr'] = df['pa_dist'] / df['atr']

        # COUNTER-TREND ALLOWED
        df['pa_counter_allowed'] = (
                (df['bars_since_pa'] <= PA_COUNTER_MAX_BARS) &
                (df['pa_dist_atr'] <= PA_COUNTER_ATR_MULT)
        )

        # CONTINUATION ALLOWED
        df['pa_continuation_allowed'] = (
                (df['bars_since_pa'] >= PA_CONT_MIN_BARS) &
                (df['pa_dist_atr'] >= PA_CONT_MIN_ATR) &
                (df['pa_dist_atr'] <= PA_CONT_MAX_ATR)
        )

        return df


    def track_bos_follow_through(self, df):

        # ===============================
        # 1️⃣ INICJALIZACJA
        # ===============================
        df['bos_dir'] = None
        df['bos_price'] = np.nan
        df['bos_idx_event'] = np.nan

        # ===============================
        # 2️⃣ BOS EVENT (JEDNOZNACZNIE)
        # ===============================
        df.loc[df['bos_bull_event'], 'bos_dir'] = 'bull'
        df.loc[df['bos_bear_event'], 'bos_dir'] = 'bear'

        df.loc[df['bos_bull_event'], 'bos_price'] = df['bos_bull_level']
        df.loc[df['bos_bear_event'], 'bos_price'] = df['bos_bear_level']

        mask = df['bos_bull_event'] | df['bos_bear_event']
        df.loc[mask, 'bos_idx_event'] = df.index[mask]

        # ===============================
        # 3️⃣ FORWARD FILL – AKTYWNY BOS
        # ===============================
        df['bos_dir'] = df['bos_dir'].ffill()
        df['bos_price'] = df['bos_price'].ffill()
        df['bos_idx_event'] = df['bos_idx_event'].ffill()

        # ===============================
        # 4️⃣ BARS SINCE BOS
        # ===============================
        df['bars_since_bos'] = df.index - df['bos_idx_event']

        # ===============================
        # 5️⃣ ATR W MOMENCIE BOS
        # ===============================
        df['atr_at_bos'] = np.where(
            df.index == df['bos_idx_event'],
            df['atr'],
            np.nan
        )
        df['atr_at_bos'] = df['atr_at_bos'].ffill()

        # ===============================
        # 6️⃣ MFE / MAE
        # ===============================
        df['mfe_from_bos'] = np.nan
        df['mae_from_bos'] = np.nan

        bull_mask = df['bos_dir'] == 'bull'
        bear_mask = df['bos_dir'] == 'bear'

        df.loc[bull_mask, 'mfe_from_bos'] = df['high'] - df['bos_price']
        df.loc[bull_mask, 'mae_from_bos'] = df['bos_price'] - df['low']

        df.loc[bear_mask, 'mfe_from_bos'] = df['bos_price'] - df['low']
        df.loc[bear_mask, 'mae_from_bos'] = df['high'] - df['bos_price']

        # ===============================
        # 7️⃣ NORMALIZACJA
        # ===============================
        df['follow_through_atr'] = df['mfe_from_bos'] / df['atr_at_bos']
        df['adverse_atr'] = df['mae_from_bos'] / df['atr_at_bos']

        return df

    def detect_microstructure_regime(
            self,
            df,
            atr_short: int = 14,
            atr_long: int = 100,
            range_lookback: int = 20,
            impulse_mult: float = 1.2,
            compression_thr: float = 0.6,
            expansion_thr: float = 1.4,
    ):
        """
        ====================================================================
        MICROSTRUCTURE FSM & BIAS – STRATEGY USAGE DOCSTRING
        ====================================================================

        Ten moduł NIE generuje sygnałów tradingowych.
        Dostarcza WYŁĄCZNIE kontekst decyzyjny oparty o mikrostrukturę rynku.

        Każda kolumna odpowiada na inne pytanie:
            - „JAK rynek się porusza?”
            - „GDZIE jest asymetria?”
            - „CZY wolno grać momentum / countertrend?”

        --------------------------------------------------------------------
        PODSTAWOWA DETEKCJA STANU
        --------------------------------------------------------------------

        microstructure_regime : {'normal', 'compression', 'expansion', 'exhaustion'}

        Znaczenie:
            normal
                - baseline execution
                - brak asymetrii
                - najlepszy stan dla standardowych setupów

            compression
                - HTF / LTF coil (akumulacja, zwijanie zakresu)
                - NIE jest martwym rynkiem
                - brak natychmiastowego edge
                - edge pojawia się w przejściu → expansion

            expansion
                - impuls / displacement
                - najwyższy follow-through
                - jedyny stan z edge dla continuation

            exhaustion
                - wysoka zmienność bez progresu
                - statystyczny zwrot przeciwko impulsowi
                - idealny kontekst dla fade / sweep / risky countertrend

        UWAGA:
            Sam stan NIE jest sygnałem.
            Edge siedzi w SEKWENCJI stanów.

        --------------------------------------------------------------------
        SEKWENCJA STANÓW
        --------------------------------------------------------------------

        micro_transition : '<prev>_to_<current>'

        Przykłady:
            compression_to_expansion
            expansion_to_exhaustion
            normal_to_expansion

        Znaczenie:
            Sekwencja stanów jest ważniejsza niż aktualny stan.
            FSM używa transition, nie samego regime.

        --------------------------------------------------------------------
        MIKROSTRUKTURALNY BIAS (ASYMETRIA)
        --------------------------------------------------------------------

        micro_bias : {'momentum_favorable', 'countertrend_favorable', 'balanced'}

        Znaczenie:
            momentum_favorable
                - asymetria w kierunku impulsu
                - continuation ma edge
                - przykłady:
                    * compression → expansion
                    * normal → expansion

            countertrend_favorable
                - asymetria PRZECIWKO impulsowi
                - idealne środowisko na:
                    * fade
                    * failed BOS
                    * liquidity sweep
                - typowo:
                    * expansion → exhaustion

            balanced
                - brak asymetrii
                - rynek w równowadze
                - tylko standardowe, konserwatywne setupy

        --------------------------------------------------------------------
        PAMIĘĆ FSM (CZAS MA ZNACZENIE)
        --------------------------------------------------------------------

        bars_in_micro_bias : int

        Znaczenie:
            Liczba barów od wejścia w aktualny micro_bias.

        Interpretacja:
            momentum_favorable:
                1–3 bary → najlepsze RR
                >3       → momentum wygasa

            countertrend_favorable:
                1–2 bary → jedyne sensowne okno na fade
                >2       → edge znika

        --------------------------------------------------------------------
        BLOKADY I POZWOLENIA (NIE SYGNAŁY)
        --------------------------------------------------------------------

        allow_momentum : bool
            True:
                - wolno grać continuation
                - tylko gdy micro_bias == momentum_favorable
                - tylko krótko po transition

        block_momentum : bool
            True:
                - zakaz grania momentum
                - szczególnie po:
                    * expansion → exhaustion
                    * exhaustion → normal

        allow_countertrend : bool
            True:
                - wolno próbować fade / reversal
                - tylko w wąskim oknie exhaustion

        block_countertrend : bool
            True:
                - zakaz countertrend
                - brak asymetrii lub zbyt późno
                - świeży flip struktury (chaos)

        --------------------------------------------------------------------
        JAK UŻYWAĆ W STRATEGII
        --------------------------------------------------------------------

        1) Trend continuation (bez ryzyka):
            - trend_active == True
            - allow_momentum == True
            - block_momentum == False
            - bars_since_flip >= N

        2) Ryzykowny countertrend (świadomy):
            - bos_bull_event / bos_bear_event
            - allow_countertrend == True
            - block_countertrend == False
            - mniejszy risk (np. 0.3R)

        3) Gdy NIC nie jest True:
            - NIE handluj
            - rynek nie daje edge

        --------------------------------------------------------------------
        CZEGO NIE ROBIĆ
        --------------------------------------------------------------------

        ❌ Nie traktować żadnej kolumny jako sygnału wejścia
        ❌ Nie optymalizować progów pod TF osobno
        ❌ Nie grać countertrend poza exhaustion
        ❌ Nie ignorować czasu (bars_in_micro_bias)

        --------------------------------------------------------------------
        FILOZOFIA
        --------------------------------------------------------------------

        Ten moduł nie mówi:
            „KUP / SPRZEDAJ”

        On mówi:
            „KTO ma przewagę i JAKĄ”

        Decyzje tradingowe należą do kolejnych warstw strategii.
        """

        # ===============================
        # 1️⃣ ZMIENNOŚĆ RELATYWNA
        # ===============================
        df['atr_short'] = df['atr'].rolling(atr_short).mean()
        df['atr_long'] = df['atr'].rolling(atr_long).mean()

        df['atr_ratio'] = df['atr_short'] / df['atr_long']

        # ===============================
        # 2️⃣ RANGE / COMPRESSION
        # ===============================
        rolling_high = df['high'].rolling(range_lookback).max()
        rolling_low = df['low'].rolling(range_lookback).min()

        df['rolling_range'] = rolling_high - rolling_low
        df['range_atr_ratio'] = df['rolling_range'] / df['atr_long']

        # ===============================
        # 3️⃣ IMPULSE vs OVERLAP
        # ===============================
        body = (df['close'] - df['open']).abs()
        bar_range = (df['high'] - df['low']).replace(0, np.nan)

        df['body_ratio'] = body / bar_range

        df['impulse_bar'] = (
                (bar_range > impulse_mult * bar_range.rolling(50).median()) &
                (df['body_ratio'] > 0.6)
        )

        df['overlap_bar'] = (
                (bar_range < 0.8 * df['atr']) &
                (df['body_ratio'] < 0.4)
        )

        # rolling character
        df['impulse_freq'] = df['impulse_bar'].rolling(10).mean()
        df['overlap_freq'] = df['overlap_bar'].rolling(10).mean()

        # ===============================
        # 4️⃣ REGIME LOGIC (DETERMINISTIC)
        # ===============================
        regime = np.full(len(df), 'normal', dtype=object)

        range_decay = (
                df['rolling_range'] <
                df['rolling_range'].rolling(50).median() * 0.7
        )

        # COMPRESSION
        compression_mask = (
                range_decay &
                (df['overlap_freq'] > 0.55) &
                (df['impulse_freq'] < 0.25)  # ← KLUCZ
        )

        # EXPANSION
        expansion_mask = (
                (df['impulse_freq'] > 0.45) &
                (
                        (df['atr_ratio'] > expansion_thr) |
                        (df['impulse_freq'].shift(1) < 0.2)
                )
        )

        # EXHAUSTION
        exhaustion_mask = (
                (df['atr_ratio'] > expansion_thr) &
                (df['impulse_freq'] < 0.25) &
                (df['overlap_freq'] > 0.4) &
                (df['follow_through_atr'] < 1.2)
        )

        regime[compression_mask] = 'compression'
        regime[expansion_mask] = 'expansion'
        regime[exhaustion_mask] = 'exhaustion'

        df['microstructure_regime'] = regime

        # ===============================
        # 5️⃣ FEATURES POMOCNICZE
        # ===============================


        df['volatility_state'] = np.where(
            df['atr_ratio'] < 0.8, 'low',
            np.where(df['atr_ratio'] > 1.3, 'high', 'normal')
        )

        df['micro_prev'] = df['microstructure_regime'].shift(1)

        df['micro_transition'] = (
                df['micro_prev'].astype(str) +
                '_to_' +
                df['microstructure_regime'].astype(str)
        )

        # =============================================================
        # MICROSTRUCTURE FSM – SEKWENCJA STANÓW
        # =============================================================

        # 1️⃣ Poprzedni stan mikrostruktury
        df['micro_prev'] = df['microstructure_regime'].shift(1)

        # 2️⃣ Nazwa przejścia (sekcja deterministyczna)
        df['micro_transition'] = (
                df['micro_prev'].astype(str) +
                '_to_' +
                df['microstructure_regime'].astype(str)
        )

        # =============================================================
        # MICROSTRUCTURE BIAS – POPRAWNA SEMANTYKA
        # =============================================================

        df['micro_bias'] = 'balanced'

        # ==========================
        # MOMENTUM FAVORABLE
        # (KRÓTKIE OKNO PO TRANSITION)
        # ==========================
        df.loc[
            df['micro_transition'].isin({
                'compression_to_expansion',
                'normal_to_expansion',
            }),
            'micro_bias'
        ] = 'momentum_favorable'

        # ==========================
        # COUNTERTREND FAVORABLE
        # (CAŁA FAZA EXHAUSTION)
        # ==========================
        df.loc[
            df['microstructure_regime'] == 'exhaustion',
            'micro_bias'
        ] = 'countertrend_favorable'

        # ==========================
        # COUNTERTREND FAVORABLE
        # ==========================
        COUNTERTREND_FAVORABLE = {
            'expansion_to_exhaustion',
        }

        df.loc[
            df['micro_transition'].isin(COUNTERTREND_FAVORABLE),
            'micro_bias'
        ] = 'countertrend_favorable'


        # =============================================================
        # FSM PAMIĘĆ (STATE DURATION)
        # =============================================================

        # 3️⃣ Liczba barów w aktualnym micro_bias
        df['micro_bias_block'] = (
            df['micro_bias']
            .ne(df['micro_bias'].shift())
            .cumsum()
        )

        df['bars_in_micro_bias'] = (
                df.groupby(df['micro_bias_block'])
                .cumcount() + 1
        )

        # 4️⃣ Bary od ostatniego momentum_favorable
        df['bars_since_momentum'] = (
            df['micro_bias'].eq('momentum_favorable')
            .astype(int)
            .groupby(df['micro_bias'].ne('momentum_favorable').cumsum())
            .cumcount()
        )

        df['bars_since_countertrend'] = (
            df['micro_bias']
            .eq('countertrend_favorable')
            .astype(int)
            .groupby(df['micro_bias'].ne('countertrend_favorable').cumsum())
            .cumcount()
        )

        # =============================================================
        # KONTEKSTY WYSOKIEGO POZIOMU (BEZ SYGNAŁÓW)
        # =============================================================

        # 🚫 BLOK DLA MOMENTUM (late / chaos)
        df['block_momentum'] = (
                df['micro_bias'] == 'countertrend_favorable'
        )

        # ✅ POZWOLENIE NA CONTINUATION
        df['allow_momentum'] = (
                (df['micro_bias'] == 'momentum_favorable') &
                (df['bars_in_micro_bias'] <= 3)
        )

        # ⚠️ RYZYKOWNY KONTR-TRADE (fade / sweep)
        df['allow_countertrend'] = (
                (df['micro_bias'] == 'countertrend_favorable') &
                (df['bars_in_micro_bias'] <= 2)
        )

        df['block_countertrend'] = (
            (df['micro_bias'] != 'countertrend_favorable') |
            (df['bars_in_micro_bias'] > 2) |
            (df['bars_since_flip'] < 4)
        )

        # =============================================================
        # (OPCJONALNE) PREMIUM CONTEXT
        # =============================================================

        df['premium_context'] = (
                (df['micro_bias'] == 'momentum_favorable') &
                (df['bars_in_micro_bias'] <= 2)
        )
        return df

    def calculate_structural_volatility(self, df):

        mask = (
                df["pa_event_type"].isin(["mss", "bos"]) &
                df["pa_event_dir"].isin(["bull", "bear"])
        )

        df["struct_target_dist"] = np.nan
        df["struct_target_dist_atr"] = np.nan

        bull = mask & (df["pa_event_dir"] == "bull")
        bear = mask & (df["pa_event_dir"] == "bear")

        # ===== BULL (LONG context) =====
        bull_ll = df['close'] - df['LL']
        bear_HH = df['HH'] - df['close']

        MAX_STRUCT_AGE = 200  # do testów

        df["struct_age"] = np.nan
        df.loc[bull, "struct_age"] = df["idx"] - df["LL_idx"]
        df.loc[bear, "struct_age"] = df["idx"] - df["HH_idx"]

        valid_struct = df["struct_age"] <= MAX_STRUCT_AGE

        df.loc[bull & valid_struct, "struct_target_dist"] = bull_ll
        df.loc[bear & valid_struct, "struct_target_dist"] = bear_HH

        # ===== BEAR (SHORT context) =====

        df["struct_target_dist_atr"] = df["struct_target_dist"] / df["atr"]

        return df

    # =============================================================
    # 5️⃣ PIPELINE – całość
    # =============================================================
    def apply(self, df: pd.DataFrame):
        self.detect_peaks(df)
        self.detect_eqh_eql_from_pivots(df)
        self.detect_fibo(df)
        self.detect_price_action(df)
        self.track_bos_follow_through(df)
        self.detect_trend_regime(df)
        self.generate_price_action_context(df)
        self.enrich_pa_context(df)
        self.detect_microstructure_regime(df)
        self.calculate_structural_volatility(df)

        return df
