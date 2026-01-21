import numpy as np
import pandas as pd


class PriceActionStateEngine:
    """
    Stateful price action engine.
    Produces structural events and extended states.
    """

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
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


        return df