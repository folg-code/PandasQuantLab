import logging

logging.basicConfig(level=logging.INFO)

# ==================================================
# DATA
# ==================================================

MARKET_DATA_PATH = "market_data"
BACKTEST_DATA_BACKEND = "dukascopy"   # "dukascopy"

TIMERANGE = {
    "start": "2025-01-01",
    "end":   "2025-12-31",
}

BACKTEST_MODE = "single"  # "single" | "split"

BACKTEST_WINDOWS = {
    "OPT":   ("2025-12-01", "2025-12-15"),
    "VAL":   ("2025-12-16", "2025-12-23"),
    "FINAL": ("2025-12-24", "2025-12-31"),
}

# Missing data handling metadata (report/UI)
# Examples:
# - "Forward-fill OHLC gaps"
# - "Drop candles with gaps"
# - "Leave gaps (no fill)"
MISSING_DATA_HANDLING = "Forward-fill OHLC gaps"

SERVER_TIMEZONE = "UTC"

# ==================================================
# STRATEGY
# ==================================================

# If None, report will fall back to STRATEGY_CLASS.
STRATEGY_NAME = "Sample "

# Optional short description (used in BacktestConfigSection)
STRATEGY_DESCRIPTION = "Sample strategy for dashboard showcase"

# Strategy class locator (string used by your loader)
STRATEGY_CLASS = "Samplestrategy"
STARTUP_CANDLE_COUNT = 600

SYMBOLS = [
    "XAUUSD",
]

TIMEFRAME = "M5"


# ==================================================
# EXECUTION (SIMULATED)
# ==================================================

INITIAL_BALANCE = 10_000

# Slippage assumed in "pips" for FX-like instruments in current convention.
SLIPPAGE = 0.1

# Optional: separate slippage for entry/exit (metadata now; logic later)
SLIPPAGE_ENTRY = None  # if None -> use SLIPPAGE
SLIPPAGE_EXIT = None   # if None -> use SLIPPAGE

MAX_RISK_PER_TRADE = 0.005

# Execution delay metadata (not implemented yet)
# Could be "None", "1 bar", "200ms", etc.
EXECUTION_DELAY = "None"

# Order types (metadata now; logic later)
# Use: "market" | "limit"
ENTRY_ORDER_TYPE_DEFAULT = "market"
EXIT_ORDER_TYPE_DEFAULT = "limit"
TP_ORDER_TYPE_DEFAULT = "limit"


# explanation for report (avoid wrong claims)
EXIT_OVERRIDES_DESC = "SL/BE/EOD treated as market exits; TP exits treated as limit (strategy-dependent)."

# Spread model metadata:
# - "fixed_cost_overlay" (current reality: compute spread_usd_* from per-instrument fixed spreads)
# - "bid_ask_simulation" (future: actual bid/ask price simulation in fills)
SPREAD_MODEL = "fixed_cost_overlay"




# ==================================================
# CAPITAL MODEL (REPORT / FUTURE CONTROLS)
# ==================================================

# Position sizing model label for report
POSITION_SIZING_MODEL = "Risk-based sizing (position_sizer)"

# (FUTURE  IDEA)Leverage is metadata unless you  model margin / leverage constraints
LEVERAGE = "1x"

# (FUTURE  IDEA) Concurrency
MAX_CONCURRENT_POSITIONS = None  # None => Unlimited (diagnostic)

# (FUTURE  IDEA) Kill-switch / capital floor
CAPITAL_FLOOR = None  # e.g. 5000, or None

# ==================================================
# OUTPUT / UI
# ==================================================

SAVE_TRADES_CSV = False
PLOT_ONLY = False