import MetaTrader5 as mt5
import json
from tg_sender import send_telegram_log


def send_order(symbol, direction, volume, sl, tp1, tp2, comment="", ):
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        print(f"❌ Nie można pobrać informacji o symbolu: {symbol}")
        return None

    point = symbol_info.point
    stops_level = symbol_info.trade_stops_level  # liczba punktów
    step = symbol_info.trade_tick_size
    min_stop_distance = (stops_level + 5) * point  # z buforem bezpieczeństwa

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"❌ Brak ticków dla {symbol}")
        return None

    order_type = mt5.ORDER_TYPE_BUY if direction == "long" else mt5.ORDER_TYPE_SELL
    order_price_ask = tick.ask if direction == "long" else tick.bid

    # 🟡 Kandydaci przed korektą
    sl = round(sl / step) * step
    tp2 = round(tp2 / step) * step

    order_price = tick.ask if direction == "long" else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": order_price_ask,
        "sl": sl,
        "tp": tp2,
        "deviation": 30,
        "magic": 234000,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    # print("REQUEST:", request)

    result = mt5.order_send(request)
    if result is None:
        print("Błąd wysłania zlecenia: brak odpowiedzi z MT5")
        print("MT5 last error:", mt5.last_error())  # ← to dopisz
        print(f'[52]{result}')
        send_telegram_log("Błąd wysłania zlecenia: brak odpowiedzi z MT5")
        return None
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Błąd zlecenia: {result.retcode} - {result.comment}")
        return result

    return result


def close_position(position, volume=None):
    direction = position.type
    symbol = position.symbol

    if volume is None:
        print(f"❌ Nie podano volume dla pozycji {symbol}")
        return None

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"❌ Brak ticków dla {symbol}")
        return None

    if tick.bid == 0 or tick.ask == 0:
        print(f"❌ Brak realnych cen (bid/ask = 0) dla {symbol}")
        return None

    price = tick.bid if direction == mt5.ORDER_TYPE_BUY else tick.ask
    order_type = mt5.ORDER_TYPE_SELL if direction == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "position": position.ticket,
        "price": price,
        "deviation": 20,
        "magic": 123456,
        "comment": "Auto-close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    print(f'[price] {price}')
    print(f'[request] {request}')

    result = mt5.order_send(request)

    if result is None:
        print("❌ Brak odpowiedzi z mt5.order_send()")
        return None

    print("✅ result:", result)
    print("retcode:", result.retcode)
    print("comment:", result.comment)

    return result


def get_open_positions(symbol):
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        return []
    return list(positions)


def load_active_trades():
    try:
        with open("active_trades.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def save_active_trades(trades):
    with open("active_trades.json", "w") as f:
        json.dump(trades, f, indent=4)


def modify_stop_loss(trade_id, new_sl):
    # Pobierz informacje o pozycji
    position = mt5.positions_get(ticket=trade_id)
    if not position:
        print(f"❌ Nie znaleziono pozycji o ID {trade_id}")
        return False
    position = position[0]

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": trade_id,
        "sl": new_sl,
        "tp": position.tp,
        "symbol": position.symbol,
    }

    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        return True
    else:
        print(f"❌ Błąd modyfikacji SL: {result.comment}")
        return False

