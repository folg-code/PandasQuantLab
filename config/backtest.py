import logging
from enum import Enum
from pathlib import Path

from core.logging.config import LoggerConfig

logging.basicConfig(level=logging.INFO)

# ==================================================
# DATA SOURCE & TIME
# ==================================================

MARKET_DATA_PATH = "market_data"
BACKTEST_DATA_BACKEND = "dukascopy"   # "dukascopy", "csv", ...

SERVER_TIMEZONE = "UTC"

TIMERANGE = {
    "start": "2025-01-01",
    "end":   "2025-12-29",
}

BACKTEST_MODE = "single"  # "single" | "split"

BACKTEST_WINDOWS = {
    "OPT":   ("2025-12-01", "2025-12-15"),
    "VAL":   ("2025-12-16", "2025-12-23"),
    "FINAL": ("2025-12-24", "2025-12-31"),
}

# Metadata only (for reports / README)
MISSING_DATA_HANDLING = "Forward-fill OHLC gaps"

# ==================================================
# STRATEGY DEFINITION
# ==================================================

STRATEGY_CLASS = "Samplestrategyreport"

STRATEGY_NAME = "Sample Strategy"
STRATEGY_DESCRIPTION = "Sample strategy for dashboard showcase"

STARTUP_CANDLE_COUNT = 600

SYMBOLS = [
    "XAUUSD",
    "EURUSD"
]

TIMEFRAME = "M1"

# ==================================================
# EXECUTION MODEL (SIMULATED)
# ==================================================

INITIAL_BALANCE = 10_000

MAX_RISK_PER_TRADE = 0.005

# Slippage (metadata + future logic)
SLIPPAGE = 0.1
SLIPPAGE_ENTRY = None  # if None -> SLIPPAGE
SLIPPAGE_EXIT = None   # if None -> SLIPPAGE

# Execution / order semantics (metadata for now)
EXECUTION_DELAY = "None"  # e.g. "1 bar", "200ms"

ENTRY_ORDER_TYPE_DEFAULT = "market"   # "market" | "limit"
EXIT_ORDER_TYPE_DEFAULT = "limit"
TP_ORDER_TYPE_DEFAULT = "limit"

EXIT_OVERRIDES_DESC = (
    "SL/BE/EOD treated as market exits; "
    "TP exits treated as limit (strategy-dependent)."
)

SPREAD_MODEL = "fixed_cost_overlay"  # or "bid_ask_simulation"

# ==================================================
# CAPITAL & RISK MODEL (REPORTING / FUTURE)
# ==================================================

POSITION_SIZING_MODEL = "Risk-based sizing (position_sizer)"

LEVERAGE = "1x"

MAX_CONCURRENT_POSITIONS = None  # None = unlimited (diagnostic)

CAPITAL_FLOOR = None  # e.g. 5000

# ==================================================
# REPORTING & ANALYTICS
# ==================================================

# Enable / disable reporting entirely
ENABLE_REPORT = True

# ---- STDOUT rendering control ----
class StdoutMode(str, Enum):
    OFF = "off"
    CONSOLE = "console"
    FILE = "file"
    BOTH = "both"

REPORT_STDOUT_MODE = StdoutMode.OFF

# Used only if FILE or BOTH
REPORT_STDOUT_FILE = "results/stdout_report.txt"

# ---- Dashboard / persistence ----
GENERATE_DASHBOARD = True
PERSIST_REPORT = True

# Fail if no trades (research safety)
REPORT_FAIL_ON_EMPTY = True

# ==================================================
# RUNTIME / DEBUG
# ==================================================

PLOT_ONLY = False          # Skip backtest, just plots
SAVE_TRADES_CSV = False   # Legacy / debug only


LOGGER_CONFIG = LoggerConfig(
    stdout=True,
    file=True,
    timing=True,
    profiling=False,
    log_dir=Path("results/logs"),
)

PROFILING = True

USE_MULTIPROCESSING_STRATEGIES = False
USE_MULTIPROCESSING_BACKTESTS = True

MAX_WORKERS_STRATEGIES = None     # None = os.cpu_count()
MAX_WORKERS_BACKTESTS = None