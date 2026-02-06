import pandas as pd


class RiskDataPreparer:
    def __init__(self, initial_balance: float, timezone: str = "UTC"):
        self.initial_balance = initial_balance
        self.timezone = timezone

    def prepare(self, trades: pd.DataFrame) -> pd.DataFrame:
        trades = trades.copy()

        for col in ("entry_time", "exit_time"):
            if col not in trades.columns:
                continue

            if not pd.api.types.is_datetime64_any_dtype(trades[col]):
                trades[col] = pd.to_datetime(trades[col])

            if trades[col].dt.tz is None:
                trades[col] = trades[col].dt.tz_localize(self.timezone)

            else:
                trades[col] = trades[col].dt.tz_convert(self.timezone)

        trades = trades.sort_values("exit_time").reset_index(drop=True)


        trades["equity"] = self.initial_balance + trades["pnl_usd"].cumsum()

        running_max = trades["equity"].cummax()
        trades["drawdown"] = trades["equity"] - running_max

        return trades
