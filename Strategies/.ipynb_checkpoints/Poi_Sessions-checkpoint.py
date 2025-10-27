import pandas as pd

from Strategies.utils.decorators import informative
from TechnicalAnalysis.PointOfInterestSMC.core import SmartMoneyConcepts


class Poi:
    def __init__(self, df: pd.DataFrame, symbol, startup_candle_count: int = 600):
        self.startup_candle_count = startup_candle_count
        self.df = df.copy()
        self.symbol = symbol
        self.informative_dataframes = {}
        # Inicjalizacja klasy SmartMoneyConcepts
        self.smc = SmartMoneyConcepts(self.df)

    @informative('H1')
    def populate_indicators_H1(self, df: pd.DataFrame):
        # Podstawowe wskaźniki i HA

        # Znajdowanie i walidacja stref na H1
        self.smc.df = df
        self.smc.find_zones(tf="H1")
        return self.smc.df

    def populate_indicators(self):
        # Podstawowe wskaźniki i HA

        # Znajdowanie i walidacja stref na M5 (domyślny TF)
        self.smc.df = self.df
        self.smc.find_zones(tf="")  # M5 nie ma suffixu
        self.smc.process_secondary_zones()
        return self.smc.df