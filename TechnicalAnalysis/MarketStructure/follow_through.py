import numpy as np
import pandas as pd

from TechnicalAnalysis.MarketStructure.utils.ensure_indicator import ensure_indicator


class PriceActionFollowThrough:
    """
    Follow-through evaluation for structural events (BOS or MSS),
    split by direction (bull / bear).

    Semantics:
    - Event happens at t
    - Follow-through is KNOWN at t + lookahead
    - Assigned at t + lookahead
    - NO look-ahead bias
    """

    def __init__(
        self,
        event_source: str = "bos",   # "bos" | "mss"
        atr_mult: float = 1.0,
        lookahead: int = 5,
        atr_period: int = 14,
    ):
        if event_source not in ("bos", "mss"):
            raise ValueError("event_source must be 'bos' or 'mss'")

        self.event_source = event_source
        self.atr_mult = atr_mult
        self.lookahead = lookahead
        self.atr_period = atr_period

    def apply(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        idx = df.index

        # =====================================================
        # 0️⃣ ENSURE ATR
        # =====================================================
        ensure_indicator(df, indicator="atr", period=self.atr_period)

        # =====================================================
        # 1️⃣ MAP EVENT SOURCE
        # =====================================================
        if self.event_source == "bos":
            bull_event = df["bos_bull_event"]
            bear_event = df["bos_bear_event"]
            bull_level = df["bos_bull_level"]
            bear_level = df["bos_bear_level"]
        else:  # MSS
            bull_event = df["mss_bull_event"]
            bear_event = df["mss_bear_event"]
            bull_level = df["mss_bull_level"]
            bear_level = df["mss_bear_level"]

        # =====================================================
        # 2️⃣ RANGE OVER LAST N BARS (LEGAL)
        # =====================================================
        high_N = df["high"].rolling(self.lookahead).max()
        low_N = df["low"].rolling(self.lookahead).min()

        # =====================================================
        # 3️⃣ EVENT AGING (PER DIRECTION)
        # =====================================================
        bull_eval = bull_event.shift(self.lookahead)
        bear_eval = bear_event.shift(self.lookahead)

        bull_level_eval = bull_level.shift(self.lookahead)
        bear_level_eval = bear_level.shift(self.lookahead)

        atr_eval = df["atr"].shift(self.lookahead)

        # =====================================================
        # 4️⃣ FOLLOW-THROUGH SIZE (ATR-NORMALIZED)
        # =====================================================
        ft_bull_atr = (high_N - bull_level_eval) / atr_eval
        ft_bear_atr = (bear_level_eval - low_N) / atr_eval

        ft_bull_atr = pd.Series(
            np.where(bull_eval, ft_bull_atr, np.nan),
            index=idx,
        )
        ft_bear_atr = pd.Series(
            np.where(bear_eval, ft_bear_atr, np.nan),
            index=idx,
        )

        # =====================================================
        # 5️⃣ VALID / WEAK (PER DIRECTION)
        # =====================================================
        bull_valid = ft_bull_atr >= self.atr_mult
        bull_weak = bull_eval & ~bull_valid

        bear_valid = ft_bear_atr >= self.atr_mult
        bear_weak = bear_eval & ~bear_valid

        # =====================================================
        # 6️⃣ OUTPUT
        # =====================================================
        p = self.event_source

        return {
            f"{p}_bull_ft_atr": ft_bull_atr,
            f"{p}_bull_ft_valid": bull_valid,
            f"{p}_bull_ft_weak": bull_weak,

            f"{p}_bear_ft_atr": ft_bear_atr,
            f"{p}_bear_ft_valid": bear_valid,
            f"{p}_bear_ft_weak": bear_weak,
        }


class PriceActionFollowThroughBatched:
    """
    1:1 replica of legacy PriceActionFollowThrough.

    Semantics:
    - event at t
    - follow-through evaluated at t + lookahead
    - assigned at t + lookahead
    - NO look-ahead bias
    """

    def __init__(
        self,
        *,
        event_source: str = "bos",  # "bos" | "mss"
        atr_mult: float = 1.0,
        lookahead: int = 5,
    ):
        if event_source not in ("bos", "mss"):
            raise ValueError("event_source must be 'bos' or 'mss'")

        self.event_source = event_source
        self.atr_mult = atr_mult
        self.lookahead = lookahead

    def apply(
        self,
        *,
        events: dict[str, pd.Series],
        levels: dict[str, pd.Series],
        high: pd.Series,
        low: pd.Series,
        atr: pd.Series,
    ) -> dict[str, pd.Series]:

        idx = high.index
        N = self.lookahead

        # =========================
        # EVENT / LEVEL MAP
        # =========================
        bull_event = events[f"{self.event_source}_bull_event"]
        bear_event = events[f"{self.event_source}_bear_event"]

        bull_level = levels[f"{self.event_source}_bull_level"]
        bear_level = levels[f"{self.event_source}_bear_level"]

        # =========================
        # RANGE OVER LAST N BARS
        # (LEGAL, NO LOOKAHEAD)
        # =========================
        high_N = high.rolling(N).max()
        low_N = low.rolling(N).min()

        # =========================
        # EVENT AGING
        # =========================
        bull_eval = (
            bull_event
            .shift(N)
            .fillna(False)
            .astype(bool)
        )

        bear_eval = (
            bear_event
            .shift(N)
            .fillna(False)
            .astype(bool)
        )

        bull_level_eval = bull_level.shift(N)
        bear_level_eval = bear_level.shift(N)

        atr_eval = atr.shift(N)

        # =========================
        # FOLLOW-THROUGH SIZE (ATR)
        # =========================
        ft_bull_atr = pd.Series(np.nan, index=idx)
        ft_bear_atr = pd.Series(np.nan, index=idx)

        ft_bull_atr[bull_eval] = (
                (high_N - bull_level_eval) / atr_eval
        )[bull_eval]

        ft_bear_atr[bear_eval] = (
                (bear_level_eval - low_N) / atr_eval
        )[bear_eval]

        # =========================
        # VALID / WEAK (PER DIRECTION)
        # =========================
        bull_ft_valid = ft_bull_atr >= self.atr_mult
        bull_ft_weak = bull_eval & ~bull_ft_valid

        bear_ft_valid = ft_bear_atr >= self.atr_mult
        bear_ft_weak = bear_eval & ~bear_ft_valid

        prefix = self.event_source

        return {
            f"{prefix}_bull_ft_atr": ft_bull_atr,
            f"{prefix}_bull_ft_valid": bull_ft_valid,
            f"{prefix}_bull_ft_weak": bull_ft_weak,

            f"{prefix}_bear_ft_atr": ft_bear_atr,
            f"{prefix}_bear_ft_valid": bear_ft_valid,
            f"{prefix}_bear_ft_weak": bear_ft_weak,
        }