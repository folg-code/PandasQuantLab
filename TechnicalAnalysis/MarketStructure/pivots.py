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

        pivot = pivot.where(pivot >= 3)

        # ================= OUTPUT =================

        return {
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


class PivotDetectorBatched:
    """
    Batch / engine-style pivot detector.
    No DataFrame mutation. Returns dict[str, pd.Series].
    """

    def __init__(self, pivot_range: int = 15):
        self.pivot_range = pivot_range

    def apply(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        idx = df.index
        pr = self.pivot_range

        high = df["high"]
        low = df["low"]
        open_ = df["open"]
        close = df["close"]

        # =====================================================
        # 1️⃣ LOCAL EXTREMA (PURE GEOMETRY)
        # =====================================================
        local_high = (
            (high.rolling(pr).max().shift(pr + 1) <= high.shift(pr)) &
            (high.rolling(pr).max() <= high.shift(pr))
        )

        local_low = (
            (low.rolling(pr).min().shift(pr + 1) >= low.shift(pr)) &
            (low.rolling(pr).min() >= low.shift(pr))
        )

        # =====================================================
        # 2️⃣ BASE SERIES
        # =====================================================
        pivot = pd.Series(np.nan, index=idx)
        pivotprice = pd.Series(np.nan, index=idx)
        pivot_body = pd.Series(np.nan, index=idx)

        pivot[local_high] = 1
        pivot[local_low] = 2

        pivotprice[local_high] = high.shift(pr)[local_high]
        pivotprice[local_low] = low.shift(pr)[local_low]

        body_high = open_.combine(close, max)
        body_low = open_.combine(close, min)

        pivot_body[local_high] = (
            body_high
            .rolling(pr)
            .max()
            .shift(pr // 2)
        )[local_high]

        pivot_body[local_low] = (
            body_low
            .rolling(pr)
            .min()
            .shift(pr // 2)
        )[local_low]

        # =====================================================
        # 3️⃣ STRUCTURAL CLASSIFICATION
        # =====================================================
        prev_high = (
            pivotprice
            .where(local_high)
            .ffill()
            .shift(1)
        )

        prev_low = (
            pivotprice
            .where(local_low)
            .ffill()
            .shift(1)
        )

        HH = local_high & (pivotprice > prev_high)
        LH = local_high & (pivotprice < prev_high)

        LL = local_low & (pivotprice < prev_low)
        HL = local_low & (pivotprice > prev_low)

        pivot[HH] = 3
        pivot[LL] = 4
        pivot[LH] = 5
        pivot[HL] = 6

        # =====================================================
        # 4️⃣ LEVEL SERIES (STATEFUL)
        # =====================================================
        HH_val = pivotprice.where(pivot == 3).ffill()
        LL_val = pivotprice.where(pivot == 4).ffill()
        LH_val = pivotprice.where(pivot == 5).ffill()
        HL_val = pivotprice.where(pivot == 6).ffill()

        # =====================================================
        # 5️⃣ INDEX SERIES
        # =====================================================
        idx_series = pd.Series(np.arange(len(idx)), index=idx)

        HH_idx = idx_series.where(pivot == 3).ffill()
        LL_idx = idx_series.where(pivot == 4).ffill()
        LH_idx = idx_series.where(pivot == 5).ffill()
        HL_idx = idx_series.where(pivot == 6).ffill()

        # =====================================================
        # 6️⃣ SHIFTED (PREVIOUS STRUCTURE)
        # =====================================================
        HH_shift = HH_val.shift(1)
        LL_shift = LL_val.shift(1)
        LH_shift = LH_val.shift(1)
        HL_shift = HL_val.shift(1)

        HH_idx_shift = HH_idx.shift(1)
        LL_idx_shift = LL_idx.shift(1)
        LH_idx_shift = LH_idx.shift(1)
        HL_idx_shift = HL_idx.shift(1)

        pivot = pivot.where(pivot >= 3)

        # =====================================================
        # 7️⃣ OUTPUT
        # =====================================================
        return {
            "pivot": pivot,
            "pivotprice": pivotprice,
            "pivot_body": pivot_body,

            "HH": HH_val,
            "LL": LL_val,
            "LH": LH_val,
            "HL": HL_val,

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