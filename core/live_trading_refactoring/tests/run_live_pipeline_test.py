# scripts/run_live_pipeline.py

from datetime import datetime
import time

import MetaTrader5 as mt5
import pandas as pd

from core.live_trading_refactoring.engine import LiveEngine
from core.live_trading_refactoring.strategy_adapter import LiveStrategyAdapter

# === CONFIG ==================================================

SYMBOL = "EURUSD"
TIMEFRAME = "M5"
BARS = 500

STRATEGY_NAME = "Hts"   # np. "liquidity_sweep"
TICK_INTERVAL_SEC = 1.0

DRY_RUN = False          # False = REAL ORDERS
VOLUME = 0.1

MT5_LOGIN = "1512326396"        # opcjonalnie
MT5_PASSWORD = "B8?1TRis"
MT5_SERVER = "FTMO-Demo"

# ============================================================

from config import TIMEFRAME_MAP
from core.strategy.strategy_loader import load_strategy

from core.live_trading_refactoring.position_manager import PositionManager
from core.live_trading_refactoring.mt5_adapter import MT5Adapter
from core.live_trading_refactoring.trade_repo import TradeRepo

from core.strategy.trade_plan import TradePlan


# ============================================================
# MT5 INIT
# ============================================================

def init_mt5():
    if not mt5.initialize():
        raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")

    print("🟢 MT5 initialized")

    info = mt5.account_info()
    print(
        f"👤 Account: {info.login} | "
        f"Balance: {info.balance} | "
        f"Server: {info.server}"
    )


# ============================================================
# MARKET DATA PROVIDER (LIVE)
# ============================================================

def fetch_market_state(symbol: str, timeframe: str, bars: int):

    tf = TIMEFRAME_MAP[timeframe]
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)

    if rates is None:
        return None

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)

    last = df.iloc[-1]

    return {
        "price": last["close"],
        "time": datetime.utcnow(),
        "df": df,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    init_mt5()

    # --- adapter / repo / pm ---
    adapter = MT5Adapter(
        login=MT5_LOGIN,
        password=MT5_PASSWORD,
        server=MT5_SERVER,
        dry_run=DRY_RUN,
    )

    repo = TradeRepo()
    pm = PositionManager(repo=repo, adapter=adapter)

    # --- load initial data ---
    state = fetch_market_state(SYMBOL, TIMEFRAME, BARS)
    df = state["df"]

    # --- load strategy ---
    strategy = load_strategy(
        name=STRATEGY_NAME,
        df=df,
        symbol=SYMBOL,
        startup_candle_count=200,
        provider=None,  # MT5 already used here
    )

    adapter_strategy = LiveStrategyAdapter(
        strategy=strategy,
        volume=VOLUME,
    )

    # --- providers for engine ---
    def market_data_provider():
        state = fetch_market_state(SYMBOL, TIMEFRAME, BARS)
        if state is None:
            return None
        return {
            "price": state["price"],
            "time": state["time"],
        }

    def tradeplan_provider() -> TradePlan | None:
        plan = adapter_strategy.get_trade_plan()
        if plan:
            print("📦 TRADE PLAN GENERATED:")
            print(plan)
        return plan

    engine = LiveEngine(
        position_manager=pm,
        market_data_provider=market_data_provider,
        tradeplan_provider=tradeplan_provider,
        tick_interval_sec=TICK_INTERVAL_SEC,
    )

    print("🚀 LIVE PIPELINE STARTED")
    print(f"SYMBOL={SYMBOL} TF={TIMEFRAME} DRY_RUN={DRY_RUN}")

    engine.start()


# ============================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("🛑 Stopped by user")
    finally:
        mt5.shutdown()
        print("🔴 MT5 shutdown")