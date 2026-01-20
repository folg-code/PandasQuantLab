# config/live.py

# ==================================================
# DATA / EXECUTION
# ==================================================

LIVE_DATA_BACKEND = "mt5"

ACCOUNT_INFO = {
    "LOGIN": 123456789,
    "PASSWORD": "<PASSWORD>",
    "SERVER": "SERVER",
}

# ==================================================
# STRATEGY
# ==================================================

STRATEGY_CLASS = "Hts"

SYMBOLS = [
    "EURUSD",
]

TIMEFRAME = "M1"

STARTUP_CANDLE_COUNT = 600
MAX_RISK_PER_TRADE = 0.005

SERVER_TIMEZONE = "UTC"