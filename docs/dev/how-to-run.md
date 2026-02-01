# Developer setup

This document describes a minimal local setup for running the framework.

---

## Requirements

- Python 3.10+ (recommended)
- Windows + MetaTrader 5 (for live trading via MT5)
- Any OS (for backtests, research, reporting)

---

## Install

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate

pip install -U pip
pip install -r requirements.txt
```
## Backtest run (minimal)

Run a small backtest first to validate the environment.
Use a small timerange and a single symbol to reduce debug surface.
```bash
python backtest_run.py
```

