import config
from core.backtesting.runner import BacktestRunner

if __name__ == "__main__":
    BacktestRunner(config).run()