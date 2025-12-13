import time
import pandas as pd
import MetaTrader5 as mt5


class MT5Backend:
    def __init__(self):
        self.initialized = False

    def initialize(self):
        if not self.initialized:
            if not mt5.initialize():
                raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")
            self.initialized = True

    def shutdown(self):
        if self.initialized:
            mt5.shutdown()
            self.initialized = False

    def _select_symbol(self, symbol):
        if not mt5.symbol_select(symbol, True):
            time.sleep(0.3)
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Cannot select symbol: {symbol}")

    def load_range(self, symbol, timeframe, start, end):
        self.initialize()
        self._select_symbol(symbol)

        rates = mt5.copy_rates_range(symbol, timeframe, start, end)
        if rates is None or len(rates) == 0:
            raise ValueError(f"No MT5 data for {symbol}")

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        return df.reset_index(drop=True)

    def load_live(self, symbol, timeframe, lookback):
        self.initialize()
        self._select_symbol(symbol)

        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, lookback)
        if rates is None or len(rates) == 0:
            raise ValueError(f"No live MT5 data for {symbol}")

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        return df.reset_index(drop=True)