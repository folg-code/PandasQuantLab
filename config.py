import MetaTrader5 as mt5
from zoneinfo import ZoneInfo  # Python 3.9+
SERVER_TIMEZONE = ZoneInfo("UTC")

MODE = "BACKTEST"

# ====== Strategia =====
strategy = "Poi_Sessions"

# === Parametry rynku ===
SYMBOLS = [
    'GOLD',
    #'EUGERMANY40', 'US500', 'USTECH100',
    #'GBPJPY', 'EURJPY', 'EURGBP', 'EURCHF', 'USDPLN',
    #'GBPUSD', 'EURUSD', 'AUDUSD', 'NZDUSD', 'USDCHF','USDCAD','USDJPY',
    #'BTC/USD', 'ETH/USD'
]
TIMEFRAME = 'M5'
TIMERANGE = {
    'start': '2025-12-05',
    'end': '2025-12-09',
}

STARTUP_CANDLES = 600

# === Kapitał początkowy ===
INITIAL_BALANCE = 10_000.0  # USD

# === Parametry strategii ===
SLIPPAGE = 0.00

RISK_PER_TRADE = 0.005
INITIAL_SIZE = 0.1
MAX_SIZE = 3.0

CANDLE_SLEEP = 300


# === Inne opcje ===
SAVE_TRADES_CSV = True

TELEGRAM_TOKEN = '7780127253:AAEJdRLJfo5jc5Ys-hx0FtxAXqYKvBd4v_0'
TELEGRAM_CHAT_ID = '5339523184'
TELEGRAM_CHANNEL_ID = '-1002563533470'

TICK_VALUE = 10  # Dla EURUSD 1 lot = $10/pips
TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1
}

# ile danych REALNIE potrzebujemy per TF
LOOKBACK_CONFIG = {
    "M1": "24h",
    "M5": "7d",
    "H1": "30d",
    "H4": "180d",
}

lookbacks = {
    "M1": 24 * 60,  # 24h w minutach -> 1440 świec
    "M5": 7 * 24 * 12,  # 7 dni po 12 świec na godzinę (5min TF)
    "H1": 30 * 24,  # 1 miesiąc po 30 dni (1 świeca na godzinę)
    "H4": 180 * 6  # 6 miesięcy po 180 dni * 1 świeca na 4h
}

