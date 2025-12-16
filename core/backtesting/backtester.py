import traceback
from typing import List, Optional
import pandas as pd
import config
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

from core.utils.position_sizer import position_sizer
from core.backtesting.trade import Trade


class Backtester:
    """Backtester dla wielu symboli."""

    def __init__(self, slippage: float = 0.0):
        self.slippage = slippage

    def run_backtest(self, df: pd.DataFrame, symbol: Optional[str] = None) -> pd.DataFrame:
        """Backtest dla jednego symbolu lub wielu symboli."""
        if symbol:
            return self._backtest_single_symbol(df, symbol)

        all_trades = []
        for sym, group_df in df.groupby('symbol'):
            trades = self._backtest_single_symbol(group_df, sym)
            all_trades.append(trades)

        return pd.concat(all_trades).sort_values(by='exit_time') if all_trades else pd.DataFrame()

    def _backtest_single_symbol(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        trades: List[dict] = []
        blocked_tags = set()
        active_tags = set()

        for direction in ['long', 'short']:
            entries_pos = df.index[df['signal_entry'].apply(
                lambda x: isinstance(x, dict) and x.get('direction') == direction
            )].tolist()

            executed_trades = []

            for entry_pos in entries_pos:
                row = df.loc[entry_pos]
                entry_signal = row['signal_entry']
                entry_tag = entry_signal.get("tag") if isinstance(entry_signal, dict) else str(entry_signal)
                entry_time = row['time']
                levels = row.get('levels', {})

                if not isinstance(levels, dict):
                    continue

                sl = levels.get("SL") or levels.get("sl") or levels.get("stop") or levels.get(0)
                tp1 = levels.get("TP1") or levels.get("tp1") or levels.get(1)
                tp2 = levels.get("TP2") or levels.get("tp2") or levels.get(2)

                if any(t['enter_tag'] == entry_tag and t['exit_time'] > entry_time for t in executed_trades):
                    continue

                entry_price = row['close'] * (1 + self.slippage) if direction == 'long' else row['close'] * (1 - self.slippage)
                position_size = position_sizer(entry_price, sl["level"], max_risk=0.005, account_size=config.INITIAL_BALANCE, symbol=symbol)

                trade = Trade(symbol, direction, entry_time, entry_price, position_size, sl["level"], tp1["level"], tp2["level"], entry_tag)

                # --- Pętla po świecach ---
                for i in range(entry_pos + 1, len(df)):
                    candle = df.iloc[i]
                    high, low, close, time = candle['high'], candle['low'], candle['close'], candle['time']
                    atr = candle.get('atr', 0.0)

                    candle_range = high - low
                    lower_shadow = min(candle['close'], candle['open']) - low
                    upper_shadow = high - max(candle['close'], candle['open'])
                    is_green = close > candle['open']
                    is_red = close < candle['open']

                    small_upper_shadow = (upper_shadow / candle_range) < 0.35 if candle_range != 0 else False
                    small_lower_shadow = (lower_shadow / candle_range) < 0.35 if candle_range != 0 else False

                    no_exit_long = is_green and small_upper_shadow
                    no_exit_short = is_red and small_lower_shadow

                    # Aktualizacja SL po TP1
                    if trade.tp1_executed:
                        trade.sl = trade.entry_price

                    # LONG
                    if direction == 'long':
                        if not trade.tp1_executed and high >= trade.tp1 and not no_exit_long:
                            trade.tp1_price = close
                            trade.tp1_time = time
                            trade.tp1_exit_reason = tp1['tag']
                            trade.tp1_pnl = (trade.tp1_price - trade.entry_price) * (trade.position_size * 0.5)
                            trade.tp1_executed = True
                            trade.position_size *= 0.5

                        if low <= trade.sl:
                            trade.close_trade(trade.sl, time, 'BE after TP1' if trade.tp1_executed else sl['tag'])
                            break

                        if high >= trade.tp2 and not no_exit_long:
                            trade.close_trade(close, time, tp2['tag'])
                            break

                    # SHORT
                    elif direction == 'short':
                        if not trade.tp1_executed and low <= trade.tp1 and not no_exit_short:
                            trade.tp1_price = close
                            trade.tp1_time = time
                            trade.tp1_exit_reason = tp1['tag']
                            trade.tp1_pnl = (trade.entry_price - trade.tp1_price) * (trade.position_size * 0.5)
                            trade.tp1_executed = True
                            trade.position_size *= 0.5

                        if high >= trade.sl:
                            trade.close_trade(trade.sl, time, 'BE after TP1' if trade.tp1_executed else sl['tag'])
                            break

                        if low <= trade.tp2 and not no_exit_short:
                            trade.close_trade(close, time, tp2['tag'])
                            break

                # Jeśli nie zamknięto, zamykamy na ostatniej świecy
                if trade.exit_price is None:
                    last_candle = df.iloc[-1]
                    exit_price = last_candle['close'] * (1 - self.slippage) if direction == 'long' else last_candle['close'] * (1 + self.slippage)
                    trade.close_trade(exit_price, last_candle['time'], 'end_of_data')

                # Blokada tagów
                if trade.pnl < 0:
                    blocked_tags.add(entry_tag)
                elif trade.pnl > 0 and blocked_tags:
                    blocked_tags.clear()

                active_tags.discard(entry_tag)
                trades.append(trade.to_dict())
                executed_trades.append({'enter_tag': entry_tag, 'exit_time': trade.exit_time})

        print(f"✅ Finished backtest for {symbol}, {len(trades)} trades.")
        return pd.DataFrame(trades)

    def run(self) -> pd.DataFrame:
        """Uruchamia backtest. Jeśli symbol=None, robi go równolegle po wszystkich symbolach."""
        if self.symbol is not None:
            return self._backtest_single_symbol(self.df, self.symbol)

        all_trades = []
        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = []
            for sym, group_df in self.df.groupby('symbol'):
                futures.append(executor.submit(self._backtest_single_symbol, group_df.copy(), sym))
            for future in as_completed(futures):
                try:
                    trades = future.result()
                    all_trades.append(trades)
                except Exception as e:
                    print(f"❌ Błąd w backteście: {e}")
                    traceback.print_exc()

        return pd.concat(all_trades).sort_values(by='exit_time') if all_trades else pd.DataFrame()