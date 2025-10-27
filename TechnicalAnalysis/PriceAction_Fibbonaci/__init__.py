import pandas as pd


class LiquidityDetector:
    def __init__(self, df: pd.DataFrame, pivot_range: int = 14, min_percentage_change: float = 0.01):
        self.df = df.copy()
        self.pivot_range = pivot_range
        self.min_percentage_change = min_percentage_change
        self.pivots = {}  # tu zapiszemy HH, LL, LH, HL oraz ich idx