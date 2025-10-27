# WSTĘPNA CZĘŚĆ KODU NIE WYMAGA ZMIAN
import config
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from tg_sender import flush_telegram_logs, send_position_log
from file_manager import (
    load_active_trades, record_trade_entry, record_trade_exit,
    save_active_trades, mark_tp1_hit, load_blocked_tags, save_blocked_tags, find_deal_by_order, load_executed_trades,
    save_executed_trades
)
from trade_executor import send_order, close_position, modify_stop_loss

last_warning_time = {}
warning_cooldown = timedelta(minutes=15)


def run_strategy_and_manage_position(strategy, symbol, logs, tg_msgs):
    now = datetime.utcnow()

    signals = strategy.run()

    if signals is None:
        return

    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        logs.append(f"❌ Nie można pobrać informacji o symbolu: {symbol}")
        return

    latest_row = strategy.df.iloc[-1]
    previous_row = strategy.df.iloc[-2]

    signal_entry = previous_row.get("signal_entry")
    signal_exit = latest_row.get("signal_exit")

    open_positions = mt5.positions_get() or []
    active_trades = load_active_trades()
    executed_trades = load_executed_trades()
    blocked_tags = load_blocked_tags()
    open_trade_ids = [p.ticket for p in open_positions]

    candle_range = previous_row['high'] - previous_row['low']
    lower_shadow = previous_row[['close', 'open']].min() - previous_row['high']
    upper_shadow = previous_row['high'] - previous_row[['close', 'open']].max()
    is_green = previous_row['close'] > previous_row['open']
    is_red = previous_row['close'] < previous_row['open']
    small_upper_shadow = (upper_shadow / candle_range) < 0.2 if candle_range != 0 else False
    small_lower_shadow = (lower_shadow / candle_range) < 0.2 if candle_range != 0 else False

    no_exit_long = is_green & small_upper_shadow
    no_exit_short = is_red & small_lower_shadow

    # --- Usuwanie zamkniętych trade_id z active_trades z obsługą executed_trades ---

    to_remove = [tid for tid in active_trades if int(tid) not in open_trade_ids]

    check = [id for id in active_trades if int(id) in open_trade_ids]

    for id in check:
        deal = find_deal_by_order(int(id))
        # logs.append(f"[deal] {deal}")

    for tid in to_remove:
        logs.append(f"Pozycja z trade_id {tid} jest zamknięta, sprawdzam powód i usuwam z active_trades")

        trade_data = active_trades[tid]
        deal = find_deal_by_order(int(tid))
        # logs.append(f"TID typ: {type(tid)} | Klucze active_trades: {[type(k) for k in active_trades.keys()]}")
        # Jeśli trade nie osiągnął TP1, blokuj jego (symbol, enter_tag)
        if not trade_data.get("tp1_hit", True):
            enter_tag = trade_data.get("entry_tag")
            symbol = trade_data.get("symbol")
            if enter_tag and symbol:
                blocked_tags[symbol] = blocked_tags.get(symbol, {})
                blocked_tags[symbol][enter_tag] = "blocked"
                tg_msgs.append(f"🚫Tag {enter_tag} zablokowany dla {symbol} – trade {tid} nie osiągnął TP1.")
                logs.append(f"🚫 Tag {enter_tag} zablokowany dla {symbol} – trade {tid} nie osiągnął TP1.")
                save_blocked_tags(blocked_tags)

        if deal and deal.reason == mt5.DEAL_REASON_TP:
            # Zamknięte na TP → przenieś do executed_trades
            executed_trades[tid] = trade_data.copy()
            executed_trades[tid]["close_time"] = datetime.fromtimestamp(deal.time).isoformat()
            executed_trades[tid]["close_reason"] = "TP"
            logs.append(executed_trades[tid])
            tg_msgs.append(f"✅ Trade {tid} przeniesiony do executed trades po zamknięciu na TP.")

        else:
            tg_msgs.append(f"❌ Trade  {executed_trades[tid]['symbol']} {executed_trades[tid]['tag']} zamknięty,/ ")

        active_trades.pop(tid)
        save_active_trades(active_trades)

    if to_remove:
        save_active_trades(active_trades)
        save_executed_trades(executed_trades)

    # --- Sygnały wejścia i pozostała logika bez zmian ---

    if isinstance(signal_entry, tuple):
        direction, tag = signal_entry
        entry_tag = f"{tag}"

        if blocked_tags.get(symbol, {}).get(tag) == "blocked":
            # tg_msgs.append(f"❌ Tag {tag} dla symbolu {symbol} jest zablokowany po SL.")
            return

        recent_trade_time = None
        for t in active_trades.values():
            if t["symbol"] == symbol:
                try:
                    entry_time = datetime.fromisoformat(t["entry_time"])
                    if (now - entry_time) < timedelta(minutes=30):
                        recent_trade_time = entry_time
                except Exception:
                    continue

        if recent_trade_time:
            logs.append(f"⏱️ Ostatnia pozycja na {symbol} była o {recent_trade_time}, odczekaj 30 minut.")
            # tg_msgs.append(f"⏱️ Ostatnia pozycja na {symbol} była o {recent_trade_time}, odczekaj 30 minut.")
            return

        levels = previous_row.get("levels")
        if not isinstance(levels, tuple) or len(levels) != 3:
            logs.append(f"❌ Nieprawidłowe poziomy wejścia dla {symbol}")
            return

        sl, tp1, tp2 = levels[0][1], levels[1][1], levels[2][1]
        sl_exit_tag, tp1_exit_tag, tp2_exit_tag = levels[0][2], levels[1][2], levels[2][2]

        # symbol_in_active_trades = any((trade["symbol"] == symbol) and (trade.get("entry_tag") == entry_tag) for trade in active_trades.values())
        symbol_in_active_trades = False
        if not symbol_in_active_trades:
            result = send_order(
                symbol=symbol,
                direction=direction,
                volume=config.INITIAL_SIZE,
                sl=sl,
                tp1=tp1,
                tp2=tp2,
                comment=entry_tag
            )
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logs.append(result)
                open_price = latest_row['close']
                candle_form = previous_row['candle_form']
                trade_id = str(result.order)

                msg = send_position_log(direction, symbol, open_price, entry_tag, sl_exit_tag, sl, tp1_exit_tag,
                                        tp2_exit_tag, 2, tp1, 4, tp2, candle_form)
                tg_msgs.append(msg)

                active_trades[trade_id] = {
                    "symbol": symbol,
                    "trade_id": int(trade_id),
                    "open_price": open_price,
                    "entry_time": now.isoformat(),
                    "direction": direction,
                    "sl": sl,
                    "tp1": tp1,
                    "tp2": tp2,
                    "volume": config.INITIAL_SIZE,
                    "tp1_hit": False,
                    "tp2_closed": tp2_exit_tag,
                    "entry_tag": entry_tag
                }
                save_active_trades(active_trades)

                record_trade_entry(
                    tag=entry_tag,
                    symbol=symbol,
                    direction=direction,
                    price=previous_row["close"],
                    volume=config.INITIAL_SIZE,
                    entry_time=now.isoformat(),
                    sl=sl,
                    tp1=tp1,
                    tp2=tp2,
                    trade_id=int(trade_id),
                    open_price=open_price
                )
            else:
                msg = getattr(result, 'comment', 'brak odpowiedzi')
                tg_msgs.append(f"❌ {now} Błąd wysyłania zlecenia: {msg}")
        else:
            logs.append(f"⚠️ Pozycja z tagiem '{entry_tag}' już istnieje — pomijam wejście.")

    # --- Zarządzanie pozycjami i sygnał wyjścia pozostaje bez zmian ---

    # [... tu cała reszta Twojej logiki - TP1, TP2, exit ręczny ...]

    # Zarządzanie otwartymi pozycjami
    for trade_id, trade in list(active_trades.items()):
        pos = next((p for p in open_positions if p.ticket == int(trade_id)), None)
        if not pos:
            continue

        direction = trade["direction"]
        trade_volume = trade.get("volume", pos.volume)
        tag = trade.get("entry_tag")

        wait = (direction == "long" and no_exit_long) or (direction == "short" and no_exit_short)

        SL_to_BE = (trade["open_price"] + ((trade["tp1"] - trade["open_price"]) / 2)) < pos.price_current

        if SL_to_BE and trade["sl"] < trade["open_price"]:
            modify_stop_loss(int(trade_id), trade["open_price"])
            trade["sl"] = trade["open_price"]
            tg_msgs.append(
                f"⏳ SL  dla {trade['symbol']} przesunięty nas BE."
            )
            save_active_trades(active_trades)

        if not trade.get("tp1_hit") and trade_volume == config.INITIAL_SIZE:
            tp1_price = trade["tp1"]

            tp1_hit_condition = (
                    (pos.type == mt5.ORDER_TYPE_BUY and pos.price_current >= tp1_price) or
                    (pos.type == mt5.ORDER_TYPE_SELL and pos.price_current <= tp1_price)
            )

            if tp1_hit_condition:
                if wait:
                    tg_msgs.append(
                        f"⏳ TP1 osiągnięty dla {trade['symbol']}, ale czekamy — może lecieć wyżej 🚀."
                    )
                else:
                    volume_to_close = round(trade_volume / 2, 2)
                    result = close_position(pos, volume=volume_to_close)
                    if result.retcode == mt5.TRADE_RETCODE_DONE:
                        trade["volume"] -= volume_to_close
                        trade["tp1_hit"] = True
                        modify_stop_loss(int(trade_id), trade["open_price"])
                        save_active_trades(active_trades)
                        mark_tp1_hit(trade_id)

                        tg_msgs.append(
                            f"✅ Częściowe zamknięcie pozycji {direction} (TP1) {trade['symbol']} (volume {volume_to_close})"
                        )

                        if blocked_tags:
                            blocked_tags = {
                                key: status
                                for key, status in blocked_tags.items()
                                if not key.startswith(f"{symbol}__")  # usuwamy tylko wpisy danego symbolu
                            }
                            save_blocked_tags(blocked_tags)
                            tg_msgs.append(f"🔓 Odblokowano wszystkie tagi po TP1 dla symbolu {symbol}.")
                    else:
                        tg_msgs.append(f"❌ Błąd przy TP1: {result.comment}")
        """
        if not trade.get("tp2_closed", False):
            tp2_price = trade["tp2"]
            if (pos.type == mt5.ORDER_TYPE_BUY and pos.price_current >= tp2_price) or \
               (pos.type == mt5.ORDER_TYPE_SELL and pos.price_current <= tp2_price):
                result = close_position(pos, volume=trade["volume"])
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    tg_msgs.append(f"✅ Zamknięto pozycję {direction} (TP2) dla {trade['symbol']}")
                    record_trade_exit(
                        trade_id=int(trade_id),
                        price=pos.price_current,
                        time=now.isoformat(),
                        reason="TP2",
                        exit_tag=tag
                    )
                    active_trades.pop(trade_id, None)
                    save_active_trades(active_trades)


                else:
                    tg_msgs.append(f"❌ Nie udało się zamknąć TP2: {result.comment}")


    if isinstance(signal_exit, tuple):
        exit_dir, exit_tags, exit_reason = signal_exit
        for trade_id, trade in list(active_trades.items()):
            tag = trade.get("entry_tag")
            if tag not in exit_tags:
                continue

            pos = next((p for p in open_positions if p.ticket == int(trade_id)), None)
            if pos and pos.volume > 0:
                result = close_position(pos)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    record_trade_exit(
                        trade_id=int(trade_id),
                        price=pos.price_current,
                        time=now.isoformat(),
                        reason=exit_reason,
                        exit_tag=tag
                    )
                    tg_msgs.append(f"✅ Zamknięto pozycję {exit_dir} ({exit_reason}) dla {trade['symbol']}")
                    active_trades.pop(trade_id, None)
                    save_active_trades(active_trades)

                    if exit_reason.lower() == "sl":
                        blocked_tags[tag] = "blocked"
                        save_blocked_tags(blocked_tags)
                        tg_msgs.append(f"🚫 Zablokowano tag '{tag}' po SL.")
                else:
                    tg_msgs.append(f"❌ Błąd zamknięcia: {result.comment}")"""

