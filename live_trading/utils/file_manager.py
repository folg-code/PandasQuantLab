import json
import os
from datetime import datetime, timedelta, timezone
import MetaTrader5 as mt5

# === ACTIVE TRADES ===

def load_active_trades():
    try:
        with open("active_trades.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_active_trades(trades):
    with open("active_trades.json", "w") as f:
        json.dump(trades, f, indent=4)

BLOCKED_TAGS_PATH = "blocked_tags.json"

def load_blocked_tags():
    try:
        with open(BLOCKED_TAGS_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_blocked_tags(data):
    with open(BLOCKED_TAGS_PATH, 'w') as f:
        json.dump(data, f, indent=2)


# === EXECUTED TRADES ===

TRADES_FILE = "executed_trades.json"

def load_executed_trades():
    if not os.path.exists(TRADES_FILE):
        return {}
    try:
        with open(TRADES_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            else:
                print("⚠️ Błąd struktury pliku executed_trades.json — spodziewano się słownika.")
                return {}
    except json.JSONDecodeError:
        print("⚠️ Błąd dekodowania JSON — pusty lub uszkodzony plik.")
        return {}

def save_executed_trades(trades):
    with open(TRADES_FILE, "w") as f:
        json.dump(trades, f, indent=4)


# === TRADE ENTRY ===

def record_trade_entry(tag, symbol, direction, price, volume, entry_time, sl, tp1, tp2, trade_id, open_price):
    trades = load_executed_trades()
    trades[str(trade_id)] = {
        "tag": tag,
        "symbol": symbol,
        "direction": direction,
        "entry_price": price,
        "open_price": open_price,
        "entry_time": entry_time,
        "entry_tag": tag,
        "volume": volume,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp1_hit": False,
        "exit_price": None,
        "exit_time": None,
        "exit_reason": None,
        "exit_tag": None,
        "trade_id": trade_id
    }
    save_executed_trades(trades)


# === TRADE EXIT ===

def record_trade_exit(trade_id, price, time, reason, exit_tag):
    trades = load_executed_trades()
    trade_id = str(trade_id)
    if trade_id in trades:
        trades[trade_id]["exit_price"] = price
        trades[trade_id]["exit_time"] = time
        trades[trade_id]["exit_reason"] = reason
        trades[trade_id]["exit_tag"] = exit_tag
        save_executed_trades(trades)
    else:
        print(f"⚠️ Nie znaleziono pozycji z trade_id '{trade_id}' przy próbie zapisu wyjścia.")


# === MARK TP1 HIT ===

def mark_tp1_hit(trade_id):
    trades = load_executed_trades()
    trade_id = str(trade_id)
    if trade_id in trades:
        trades[trade_id]["tp1_hit"] = True
        save_executed_trades(trades)
    else:
        print(f"⚠️ Nie znaleziono pozycji z trade_id '{trade_id}' przy próbie oznaczenia TP1 jako trafionego.")


def find_deal_by_order(trade_id):
    utc_to = datetime.utcnow()
    utc_from = utc_to - timedelta(days=30)
    deals = mt5.history_deals_get(utc_from, utc_to)
    if not deals:
        print("❌ Nie udało się pobrać historii dealów MT5.")
        return None
    for deal in deals:
        if deal.order == trade_id:
            #print(f'[deal]{deal}')
            #print(deal.order)
            return deal
    return None