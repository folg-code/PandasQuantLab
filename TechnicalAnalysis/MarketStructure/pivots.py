import numpy as np
import pandas as pd


class PivotDetector:
    def __init__(self, pivot_range: int):
        self.pivot_range = pivot_range

    def apply(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        pivot_range = self.pivot_range
        n = len(df)

        idx = np.arange(n)

        # ================= DETECT PIVOTS =================

        local_high_price = (
                (df["high"].rolling(window=pivot_range).max().shift(pivot_range + 1)
                 <= df["high"].shift(pivot_range))
                &
                (df["high"].rolling(window=pivot_range).max()
                 <= df["high"].shift(pivot_range))
        )

        local_low_price = (
                (df["low"].rolling(window=pivot_range).min().shift(pivot_range + 1)
                 >= df["low"].shift(pivot_range))
                &
                (df["low"].rolling(window=pivot_range).min()
                 >= df["low"].shift(pivot_range))
        )

        pivotprice = pd.Series(np.nan, index=df.index)
        pivot_body = pd.Series(np.nan, index=df.index)
        pivot = pd.Series(np.nan, index=df.index)

        pivotprice[local_high_price] = df["high"].shift(pivot_range)[local_high_price]
        pivotprice[local_low_price] = df["low"].shift(pivot_range)[local_low_price]

        pivot_body[local_high_price] = (
            df[["open", "close"]].max(axis=1)
            .rolling(pivot_range)
            .max()
            .shift(pivot_range // 2)
        )[local_high_price]

        pivot_body[local_low_price] = (
            df[["open", "close"]].min(axis=1)
            .rolling(pivot_range)
            .min()
            .shift(pivot_range // 2)
        )[local_low_price]

        high_pivots = pivotprice[local_high_price]
        low_pivots = pivotprice[local_low_price]

        prev_high = high_pivots.shift(1).reindex(df.index)
        prev_low = low_pivots.shift(1).reindex(df.index)

        HH_cond = local_high_price & (pivotprice  > prev_high)
        LH_cond = local_high_price & (pivotprice  < prev_high)
        LL_cond = local_low_price & (pivotprice  < prev_low)
        HL_cond = local_low_price & (pivotprice  > prev_low)

        pivot[local_high_price] = 1
        pivot[local_low_price] = 2
        pivot[HH_cond] = 3
        pivot[LL_cond] = 4
        pivot[LH_cond] = 5
        pivot[HL_cond] = 6

        # ================= INDEX TRACKING =================

        HH_idx = pd.Series(np.nan, index=df.index)
        LL_idx = pd.Series(np.nan, index=df.index)
        LH_idx = pd.Series(np.nan, index=df.index)
        HL_idx = pd.Series(np.nan, index=df.index)

        for code, series in [
            (3, HH_idx),
            (4, LL_idx),
            (5, LH_idx),
            (6, HL_idx),
        ]:
            mask = pivot == code
            series[mask] = idx[mask]
            series.ffill(inplace=True)

        # ================= VALUE TRACKING =================

        HH = pd.Series(np.nan, index=df.index)
        LL = pd.Series(np.nan, index=df.index)
        LH = pd.Series(np.nan, index=df.index)
        HL = pd.Series(np.nan, index=df.index)

        for code, series in [
            (3, HH),
            (4, LL),
            (5, LH),
            (6, HL),
        ]:
            mask = pivot == code
            series[mask] = pivotprice[mask]
            series.ffill(inplace=True)

        # ================= SHIFTS =================

        HH_shift = HH.where(pivot == 3).shift(1).ffill()
        LL_shift = LL.where(pivot == 4).shift(1).ffill()
        LH_shift = LH.where(pivot == 5).shift(1).ffill()
        HL_shift = HL.where(pivot == 6).shift(1).ffill()

        HH_idx_shift = HH_idx.where(pivot == 3).shift(1).ffill()
        LL_idx_shift = LL_idx.where(pivot == 4).shift(1).ffill()
        LH_idx_shift = LH_idx.where(pivot == 5).shift(1).ffill()
        HL_idx_shift = HL_idx.where(pivot == 6).shift(1).ffill()

        # ================= OUTPUT =================

        return {
            "idx": idx,
            "pivot": pivot,
            "pivotprice": pivotprice,
            "pivot_body": pivot_body,
            "HH": HH,
            "LL": LL,
            "LH": LH,
            "HL": HL,
            "HH_idx": HH_idx,
            "LL_idx": LL_idx,
            "LH_idx": LH_idx,
            "HL_idx": HL_idx,
            "HH_shift": HH_shift,
            "LL_shift": LL_shift,
            "LH_shift": LH_shift,
            "HL_shift": HL_shift,
            "HH_idx_shift": HH_idx_shift,
            "LL_idx_shift": LL_idx_shift,
            "LH_idx_shift": LH_idx_shift,
            "HL_idx_shift": HL_idx_shift,
        }