import numpy as np
import pandas as pd


class PivotDetector:
    def __init__(self, pivot_range: int):
        self.pivot_range = pivot_range

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        pivot_range = self.pivot_range

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

        return df