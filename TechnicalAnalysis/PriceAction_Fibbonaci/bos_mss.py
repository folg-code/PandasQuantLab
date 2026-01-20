import numpy as np
import pandas as pd


def detect_bos_mss(df):
    """
    Detekcja BOS / MSS z użyciem kolumn HH/LL/HL/LH
    Zapisuje kolumny:
      bos_bull_{pivot_range}, bos_bear_{pivot_range}, mss_bull_{pivot_range}, mss_bear_{pivot_range}
      oraz indeksy: *_idx_{pivot_range}
    """
    df = df.copy()

    HH, LL, LH, HL = df['HH'], df['LL'], df['LH'], df['HL']

    actions = [
        {'name': 'bos_bull', 'level': HH, 'cond': (df['close'] > HH) & (df['close'].shift(1) > HH)},
        {'name': 'bos_bear', 'level': LL, 'cond': (df['close'] < LL) & (df['close'].shift(1) < LL)},
        {'name': 'mss_bull', 'level': LH, 'cond': (df['close'] > LH) & (df['close'].shift(1) > LH)},
        {'name': 'mss_bear', 'level': HL, 'cond': (df['close'] < HL) & (df['close'].shift(1) < HL)},
    ]

    for act in actions:
        name = act['name']
        level_col = f'{name}'
        idx_col = f'{name}_idx'

        df[level_col] = np.where(act['cond'], act['level'], np.nan)
        df[idx_col] = np.where(act['cond'], df.index, np.nan)
        df[level_col] = pd.Series(df[level_col]).ffill()
        df[idx_col] = pd.Series(df[idx_col]).ffill()

    return df