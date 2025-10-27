import requests

def send_telegram_log(message):

    TOKEN = '7780127253:AAEJdRLJfo5jc5Ys-hx0FtxAXqYKvBd4v_0'
    CHAT_ID = '5339523184'
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'

    payload = {
    "chat_id": -1002563533470,
    "text": message
}
    requests.post(url, data=payload)
    requests.post(url, data={'chat_id': CHAT_ID, 'text': message})

sent_logs_set = set()
logs_buffer = []

def buffered_send_telegram_log(message):
    if message not in sent_logs_set:
        logs_buffer.append(message)
        sent_logs_set.add(message)

def flush_telegram_logs():
    for msg in logs_buffer:
        send_telegram_log(msg)
    logs_buffer.clear()
    sent_logs_set.clear()

def round_significant(x, sig=5):
    return float(f"{x:.{sig}g}")

def send_position_log(direction, symbol, open_price, entry_tag, sl_exit_tag, sl, tp1_exit_tag,tp2_exit_tag, tp1_rr, tp1, tp2_rr, tp2, candle_formation):
    message = (
        f"✅ Pozycja {direction.upper()} {symbol}\n"
        f"   Cena otwarcia: {round_significant(open_price)}\n"
        f"   Źródło: {entry_tag}\n"
        f"   {sl_exit_tag} : {round_significant(sl)}\n"
        f"   {tp1_exit_tag}): {round_significant(tp1)}\n"
        f"   {tp2_exit_tag}): {round_significant(tp2)}\n"
        f"   Formacja świecowa {candle_formation}"
    )
    return message