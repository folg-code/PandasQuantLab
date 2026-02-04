from core.orchestration.strategy_execution import execute_strategy


class LiveStrategyAdapter:
    def __init__(
        self,
        *,
        strategy,
        provider,
        symbol,
        startup_candle_count,
        df_execution,
    ):
        self.strategy = strategy
        self.provider = provider
        self.symbol = symbol
        self.startup_candle_count = startup_candle_count
        self.df_execution = df_execution

    def on_new_candle(self):
        df_plot = execute_strategy(
            strategy=self.strategy,
            df=self.df_execution,
            provider=self.provider,
            symbol=self.symbol,
            startup_candle_count=self.startup_candle_count,
        )

        last_row = df_plot.iloc[-1]
        return self.strategy.build_trade_plan(row=last_row)