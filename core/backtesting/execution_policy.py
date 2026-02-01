EXEC_MARKET = "market"
EXEC_LIMIT = "limit"


class ExecutionPolicy:

    def __init__(
        self,
        entry_type: str = EXEC_MARKET,
        tp_type: str = EXEC_LIMIT,
        exit_default_type: str = EXEC_LIMIT,
        exit_signal_column: str = "exit_signal",
    ):
        self.entry_type = entry_type
        self.tp_type = tp_type
        self.exit_default_type = exit_default_type
        self.exit_signal_column = exit_signal_column

    def classify_exit_type(self, exit_reason: str, has_exit_signal: bool = False, exit_signal_value: bool = False) -> str:
        if has_exit_signal and exit_signal_value:
            return EXEC_MARKET

        r = (exit_reason or "").upper()
        if r in ("SL", "BE", "EOD"):
            return EXEC_MARKET
        if r in ("TP2",):
            return EXEC_LIMIT

        return self.exit_default_type