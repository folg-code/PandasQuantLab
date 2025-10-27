import MetaTrader5 as mt5
import time
import traceback
import os
import sys
from datetime import datetime, timedelta, timezone
import config
from utils.tg_sender import send_telegram_log
from backtesting.utils.data_loader import get_live_data
from backtesting.utils.strategy_loader import load_strategy
from utils.position_manager import run_strategy_and_manage_position
from concurrent.futures import ProcessPoolExecutor
from zoneinfo import ZoneInfo  # Python 3.9+
import psutil
import gc

# Przekierowanie stdout do pliku logu
log_file = open("trading_log.txt", "a", encoding="utf-8")
sys.stdout = log_file


def initialize_mt5():
    if not mt5.initialize():
        print("❌ MT5 init error:", mt5.last_error())
        return False
    print("✅ MetaTrader5 zainicjalizowany.")
    return True


def shutdown_mt5():
    mt5.shutdown()
    print("📴 Połączenie z MetaTrader5 zostało zamknięte.")


def prepare_initial_data():
    data = {}
    start_dt = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=60)
    end_dt = datetime.now(config.SERVER_TIMEZONE)

    for symbol in config.SYMBOLS:
        df = get_live_data(
            symbol,
            config.TIMEFRAME_MAP[config.TIMEFRAME],
            25000
        )
        if df is not None and not df.empty:
            data[symbol] = df
        else:
            print(f"⚠️ Brak danych początkowych dla: {symbol}")
    return data


def fetch_and_recalculate_data(strategy, symbol):
    start_dt = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=60)
    now = datetime.now(config.SERVER_TIMEZONE)
    minute_rounded = now.minute - (now.minute % 5)
    end_dt = now.replace(minute=minute_rounded, second=0, microsecond=0)

    try:
        df_new = get_live_data(
            symbol,
            config.TIMEFRAME_MAP[config.TIMEFRAME],
            candle_lookback=25000,
        )

        if df_new is not None and not df_new.empty:
            strategy.df = df_new.reset_index(drop=True)
            # print("Dataframe updated")
            return True

        else:
            print(f"⏳ Brak danych dla {symbol} w podanym zakresie")
            return False
    except Exception as e:
        print(f"❌ Błąd podczas pobierania danych dla {symbol}: {e}")
        return False


def wait_for_next_minute():
    now = datetime.now(config.SERVER_TIMEZONE)
    seconds_to_wait = 60 - now.second
    if seconds_to_wait == 60:
        seconds_to_wait = 0
    time.sleep(seconds_to_wait + 1)


def process_symbol(symbol, strategy):
    logs = []
    tg_msgs = []

    updated = fetch_and_recalculate_data(strategy, symbol)
    if updated:
        try:
            # logs.append(f"🚀 Start processing {symbol}")
            strategy_start = time.perf_counter()

            run_strategy_and_manage_position(strategy, symbol, logs, tg_msgs)

            strategy_duration = time.perf_counter() - strategy_start
            logs.append(f"✅ Strategy time for {symbol}: {strategy_duration:.2f}s")

        except Exception as e:
            logs.append(f"❌ Błąd w strategii {symbol}: {e}")
            logs.append(traceback.format_exc())
            tg_msgs.append(f"❗ [{symbol}] Błąd w strategii: {e}")

    return logs, tg_msgs


def print_resource_usage(note=""):
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / (1024 * 1024)  # MB
    cpu = process.cpu_percent(interval=0.3)  # lepszy sampling
    print(f"📊 [{note}] CPU: {cpu:.1f}% | RAM: {mem:.2f} MB")


def run_live_loop(strategies):
    while True:
        print("\n🟢 NEW LOOP")

        wait_for_next_minute()

        all_logs = []
        all_tg_msgs = []
        logs_set = set()
        msgs_set = set()

        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            print_resource_usage("🔁 Początek pętli")
            futures = [executor.submit(process_symbol, symbol, strategy) for symbol, strategy in strategies.items()]
            print_resource_usage("🔚 Koniec pętli")

            for future in futures:
                try:
                    logs, tg_msgs = future.result()

                    for log in logs:
                        if log not in logs_set:
                            all_logs.append(log)
                            logs_set.add(log)

                    for msg in tg_msgs:
                        if msg not in msgs_set:
                            all_tg_msgs.append(msg)
                            msgs_set.add(msg)

                except Exception as e:
                    err_log = f"❌ Błąd w przyszłości: {e}"
                    if err_log not in logs_set:
                        all_logs.append(err_log)
                        logs_set.add(err_log)

        print("\n=== 📝 Zebrane logi (posortowane) ===")
        for log in all_logs:
            print(log)

        print("\n=== 📬 Wiadomości Telegram (posortowane) ===")
        for msg in all_tg_msgs:
            send_telegram_log(msg)


# Później w kodzie wywołujesz funkcję np.
# run_live_loop(strategies)

def prepare_strategies():
    strategies = {}
    start_dt = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=60)
    end_dt = datetime.strptime(config.TIMERANGE['end'], "%Y-%m-%d")

    for symbol in config.SYMBOLS:
        df = get_live_data(symbol, config.TIMEFRAME_MAP[config.TIMEFRAME], 25000)
        strategy = load_strategy(config.strategy, df, symbol, config.TIMEFRAME_MAP[config.TIMEFRAME])
        strategies[symbol] = strategy
    return strategies


def main():
    if not initialize_mt5():
        print("mt5 error")
        return

    try:
        print("start")
        strategies = prepare_strategies()
        print("end prepare_strategies")
        run_live_loop(strategies)
    except KeyboardInterrupt:
        print("🛌 Zatrzymano przez użytkownika")
    finally:
        shutdown_mt5()
        log_file.close()


if __name__ == "__main__":
    main()