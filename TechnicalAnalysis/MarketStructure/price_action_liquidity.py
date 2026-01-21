import numpy as np
import pandas as pd

from TechnicalAnalysis.MarketStructure.utils.detect_level_reaction import detect_level_reaction
from TechnicalAnalysis.MarketStructure.utils.ensure_indicator import ensure_indicator


class PriceActionLiquidityResponse:
    """
    Final liquidity response classifier based on:
    - explicit level reaction (detect_level_reaction)
    - time since structural event
    - ATR-normalized distance from level

    Supports:
    - event_source: "bos" | "mss"
    - direction: "bull" | "bear"
    """

    def __init__(
        self,
        *,
        event_source: str = "bos",      # "bos" | "mss"
        direction: str = "bull",         # "bull" | "bear"
        reaction_window: int = 5,
        early_window: int = 5,
        late_window: int = 5,
        atr_distance: float = 1.0,
        atr_period: int = 14,
    ):
        if event_source not in ("bos", "mss"):
            raise ValueError("event_source must be 'bos' or 'mss'")
        if direction not in ("bull", "bear"):
            raise ValueError("direction must be 'bull' or 'bear'")

        self.event_source = event_source
        self.direction = direction
        self.reaction_window = reaction_window
        self.early_window = early_window
        self.late_window = late_window
        self.atr_distance = atr_distance
        self.atr_period = atr_period

    # ==========================================================
    # MAIN
    # ==========================================================
    def apply(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        idx = df.index
        p = self.event_source
        d = self.direction

        # ======================================================
        # 0️⃣ ENSURE ATR
        # ======================================================
        ensure_indicator(df, indicator="atr", period=self.atr_period)

        # ======================================================
        # 1️⃣ MAP EVENT + LEVEL
        # ======================================================
        event_col = f"{p}_{d}_event"
        level_col = f"{p}_{d}_level"

        if event_col not in df or level_col not in df:
            raise ValueError(f"Missing columns: {event_col}, {level_col}")

        event = df[event_col]
        level = df[level_col]

        # follow-through quality (if exists)
        ft_valid = df.get(f"{p}_{d}_ft_valid", pd.Series(False, index=idx))
        ft_weak = df.get(f"{p}_{d}_ft_weak", pd.Series(False, index=idx))

        # ======================================================
        # 2️⃣ EVENT INDEX + TIME SINCE EVENT
        # ======================================================
        event_idx = pd.Series(
            np.where(event, idx, np.nan),
            index=idx,
        ).ffill()

        bars_since_event = idx - event_idx

        # ======================================================
        # 3️⃣ DISTANCE FROM LEVEL (ATR NORMALIZED)
        # ======================================================
        dist_atr = (df["close"] - level).abs() / df["atr"]
        max_dist_atr = dist_atr.groupby(event_idx).cummax()

        # ======================================================
        # 4️⃣ EXPLICIT LEVEL REACTION
        # ======================================================
        reaction = detect_level_reaction(
            df,
            level=level,
            direction=d,
            window=self.reaction_window,
        )

        reaction_type = reaction["reaction_type"]
        reaction_strength = reaction["reaction_strength"]

        # ======================================================
        # 5️⃣ LIQUIDITY GRAB
        # ======================================================
        liq_grab = (
            ft_weak
            & (bars_since_event <= self.early_window)
            & (max_dist_atr <= self.atr_distance)
            & reaction_type.isin(["reclaim", "weak_reject"])
        )

        # ======================================================
        # 6️⃣ S/R FLIP (BREAKOUT–RETEST)
        # ======================================================
        sr_flip = (
            ft_valid
            & (bars_since_event >= self.late_window)
            & (max_dist_atr >= self.atr_distance)
            & reaction_type.isin(["reclaim", "strong_candle"])
        )

        # ======================================================
        # 7️⃣ OUTPUT
        # ======================================================
        prefix = f"{p}_{d}"

        return {
            f"liq_grab_{prefix}": liq_grab,
            f"sr_flip_{prefix}": sr_flip,
            f"{prefix}_bars_since_event": bars_since_event,
            f"{prefix}_max_dist_atr": max_dist_atr,
            f"{prefix}_reaction_type": reaction_type,
            f"{prefix}_reaction_strength": reaction_strength,
        }