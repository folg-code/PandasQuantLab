import config.backtest as cfg
from core.backtesting.runner import BacktestRunner


if __name__ == "__main__":
    import cProfile
    from pathlib import Path
    from datetime import datetime

    run_path = Path(
        f"results/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    run_path.mkdir(parents=True, exist_ok=True)

    profile_path = run_path / "profile_full.prof"

    profiler = cProfile.Profile()
    profiler.enable()

    BacktestRunner(cfg).run()

    profiler.disable()
    profiler.dump_stats(profile_path)

    print(f"[PROFILE] saved to {profile_path}")

