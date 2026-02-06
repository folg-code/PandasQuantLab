from dataclasses import dataclass
from pathlib import Path
import logging
from contextlib import contextmanager
from time import perf_counter
import cProfile
import pstats


LOG_PREFIX = {
    "DATA":    "📈 DATA PREPARER |",
    "BT":      "🧪 BACKTEST |",
    "STRAT":   "📐 STRATEGY |",
    "REPORT":  "📊 REPORT |",
    "RUNNER":  "🚀 RUN |",
}

@dataclass
class LoggerConfig:
    stdout: bool = True
    file: bool = False
    timing: bool = True
    profiling: bool = False
    log_dir: Path | None = None


class RunLogger:
    def __init__(self, name: str, cfg: LoggerConfig, prefix: str = ""):
        self.cfg = cfg
        self.name = name
        self.prefix = prefix

        self._t0 = perf_counter()
        self._t_last = self._t0

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()
        self.logger.propagate = False
        self._timings: dict[str, float] = {}

        if cfg.stdout:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(h)

        if cfg.file:
            if cfg.log_dir is None:
                raise ValueError("LoggerConfig.file=True requires log_dir")

            cfg.log_dir.mkdir(parents=True, exist_ok=True)
            path = cfg.log_dir / f"{name}.log"

            fh = logging.FileHandler(path, encoding="utf-8")
            fh.setFormatter(
                logging.Formatter("%(asctime)s | %(message)s")
            )
            self.logger.addHandler(fh)

    # --------------------
    # BASIC LOG
    # --------------------
    def log(self, msg: str):
        if self.prefix:
            self.logger.info(f"{self.prefix} {msg}")
        else:
            self.logger.info(msg)

    # --------------------
    # TIMED STEP
    # --------------------
    def step(self, label: str):
        if not self.cfg.timing:
            return

        now = perf_counter()
        delta = now - self._t_last
        total = now - self._t0

        msg = f"⏱️ {label:<30} +{delta:6.2f}s | total {total:6.2f}s"
        self.log(msg)

        self._t_last = now

    def get_timings(self) -> dict[str, float]:
        """
        Return collected timing sections.
        """
        return dict(self._timings)

    # --------------------
    # CONTEXT TIMER
    # --------------------
    @contextmanager
    def time(self, label: str):
        if not self.cfg.timing:
            yield
            return

        t0 = perf_counter()
        yield
        dt = perf_counter() - t0
        self.logger.info(f"⏱️ {label:<30} {dt:6.3f}s")

    @contextmanager
    def section(self, name: str):
        t0 = perf_counter()
        yield
        dt = perf_counter() - t0
        self._timings[name] = self._timings.get(name, 0.0) + dt


@contextmanager
def profiling(enabled: bool, path):
    if not enabled:
        yield
        return

    pr = cProfile.Profile()
    pr.enable()
    yield
    pr.disable()
    stats = pstats.Stats(pr)
    stats.sort_stats("cumtime")
    stats.dump_stats(path)


class NullLogger:
    @contextmanager
    def section(self, name: str):
        yield

    def log(self, msg: str):
        pass

    def get_timings(self) -> dict[str, float]:
        return {}