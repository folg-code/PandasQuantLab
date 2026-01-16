from datetime import datetime
import itertools

from core.live_trading_refactoring.trade_repo import TradeRepo
from core.live_trading_refactoring.position_manager import PositionManager
from core.live_trading_refactoring.mt5_adapter import MT5Adapter
from core.live_trading_refactoring.engine import LiveEngine


# --- mock market ---
prices = iter([1.1000, 1.1025, 1.1060])

def market_data_provider():
    try:
        return {
            "price": next(prices),
            "time": datetime.utcnow(),
        }
    except StopIteration:
        return None


# --- mock signals ---
sent = False

def signal_provider():
    global sent
    if sent:
        return []
    sent = True
    return [{
        "symbol": "EURUSD",
        "direction": "long",
        "entry_price": 1.1000,
        "volume": 0.1,
        "sl": 1.0950,
        "tp1": 1.1020,
        "tp2": 1.1050,
        "entry_time": datetime.utcnow(),
        "entry_tag": "engine_test",
    }]


repo = TradeRepo(data_dir="live_state_engine_test")
adapter = MT5Adapter(
    login=12345678,
    password="<PASSWORD>",
    server="FTMO-Demo",
    dry_run=False,
)
pm = PositionManager(repo, adapter)

engine = LiveEngine(
    position_manager=pm,
    market_data_provider=market_data_provider,
    signal_provider=signal_provider,
    tick_interval_sec=0.1,
)

engine.start()