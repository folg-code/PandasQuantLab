class TelegramHandler(logging.Handler):
    def emit(self, record):
        send_to_telegram(self.format(record))