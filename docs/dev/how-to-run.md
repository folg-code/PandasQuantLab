# Developer setup

This document describes a **minimal local setup** required to run the framework
for backtesting, research and (optionally) live trading.

The project is designed to run deterministically in offline mode on any OS,
with live trading supported via MetaTrader 5 on Windows.

---

## Requirements

### Core
- Python **3.10+** (recommended)
- Git

### Backtesting / Research
- Any OS (Windows, macOS, Linux)

### Live trading (optional)
- Windows
- MetaTrader 5 terminal
- Broker account supported by MT5

---

## Environment setup

Create and activate a virtual environment:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

## Configuration

A default backtest configuration is provided in:
The configuration is **predefined and ready to use** for the first run:
- includes a sample strategy
- defines symbols, timeframes and timerange
- points to default data and results directories

No configuration changes are required to run the initial backtest.
The file serves both as a runnable default and as a reference
for further experimentation.
## Backtest run (minimal)

Start with a small backtest to validate the environment and data pipeline.

Using a limited timerange and a single symbol is recommended for the first run,
as historical data may need to be downloaded and cached.

```bash
python backtest_run.py
```