import pandas as pd


class PriceActionTrendRegime:
    """
    Structural trend regime based on:
    - BOS / MSS dominance
    - follow-through quality
    - structural volatility
    - pivot structure (HH/HL vs LL/LH)

    Output:
    - trend_regime   : categorical
    - trend_bias     : +1 / 0 / -1
    - trend_strength: 0..1
    """

    def __init__(
        self,
        vol_required: bool = True,
    ):
        self.vol_required = vol_required

    def apply(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        idx = df.index

        # =====================================================
        # 1️⃣ STRUCTURAL BIAS (PIVOT-BASED)
        # =====================================================
        bullish_structure = (
            (df["pivot"] == 3) |  # HH
            (df["pivot"] == 6)    # HL
        )

        bearish_structure = (
            (df["pivot"] == 4) |  # LL
            (df["pivot"] == 5)    # LH
        )

        struct_bias = pd.Series(0, index=idx)
        struct_bias[bullish_structure] = 1
        struct_bias[bearish_structure] = -1
        struct_bias = struct_bias.ffill().fillna(0)

        # =====================================================
        # 2️⃣ EVENT DOMINANCE (BOS / MSS)
        # =====================================================
        bull_events = (
            df["bos_bull_event"] | df["mss_bull_event"]
        )

        bear_events = (
            df["bos_bear_event"] | df["mss_bear_event"]
        )

        event_bias = pd.Series(0, index=idx)
        event_bias[bull_events] = 1
        event_bias[bear_events] = -1
        event_bias = event_bias.ffill().fillna(0)

        # =====================================================
        # 3️⃣ FOLLOW-THROUGH CONFIRMATION
        # =====================================================
        bull_ft = (
            df.get("bos_bull_ft_valid", False) |
            df.get("mss_bull_ft_valid", False)
        )

        bear_ft = (
            df.get("bos_bear_ft_valid", False) |
            df.get("mss_bear_ft_valid", False)
        )

        ft_bias = pd.Series(0, index=idx)
        ft_bias[bull_ft] = 1
        ft_bias[bear_ft] = -1
        ft_bias = ft_bias.ffill().fillna(0)

        # =====================================================
        # 4️⃣ STRUCTURAL VOLATILITY FILTER
        # =====================================================
        if self.vol_required:
            high_vol = (
                (df.get("bos_bull_struct_vol") == "high") |
                (df.get("bos_bear_struct_vol") == "high") |
                (df.get("mss_bull_struct_vol") == "high") |
                (df.get("mss_bear_struct_vol") == "high")
            )
        else:
            high_vol = pd.Series(True, index=idx)

        # =====================================================
        # 5️⃣ FINAL REGIME DECISION
        # =====================================================
        trend_bias = struct_bias + event_bias + ft_bias

        regime = pd.Series("range", index=idx)

        regime[(trend_bias >= 1) & high_vol] = "trend_up"
        regime[(trend_bias <= -1) & high_vol] = "trend_down"

        # transition if bias exists but no vol
        regime[(trend_bias.abs() >= 1) & ~high_vol] = "transition"

        # =====================================================
        # 6️⃣ STRENGTH (NORMALIZED)
        # =====================================================
        trend_strength = trend_bias.abs() / 3.0
        trend_strength = trend_strength.clip(0, 1)

        return {
            "trend_regime": regime,
            "trend_bias": trend_bias,
            "trend_strength": trend_strength,
        }