
import logging
from contextlib import contextmanager
from time import perf_counter


from core.logging.config import LoggerConfig


class RunLogger:
    """
    Unified logger for backtest and live.

    Features:
    - stdout / file logging
    - log levels (debug/info/warning/error)
    - structured context (symbol, trade_id, etc.)
    - timing (step, time, section)
    - optional profiling
    """

    def __init__(
        self,
        name: str,
        cfg: LoggerConfig,
        prefix: str = "",
        *,
        context: dict | None = None,
        logger: logging.Logger | None = None,
    ):
        self.cfg = cfg
        self.name = name
        self.prefix = prefix
        self.context = context or {}

        self._t0 = perf_counter()
        self._t_last = self._t0
        self._timings: dict[str, float] = {}

        if logger is not None:
            # child logger with shared handlers
            self.logger = logger
            return

        self.logger = logging.getLogger(name)
        self.logger.setLevel(cfg.level)
        self.logger.handlers.clear()
        self.logger.propagate = False

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

    # ==================================================
    # Core emit
    # ==================================================

    def _emit(self, level: int, msg: str):
        if self.prefix:
            msg = f"{self.prefix} {msg}"

        if self.context:
            ctx = " ".join(f"{k}={v}" for k, v in self.context.items())
            msg = f"{msg} | {ctx}"

        self.logger.log(level, msg)

    # ==================================================
    # Public log API
    # ==================================================

    def debug(self, msg: str):
        self._emit(logging.DEBUG, msg)

    def info(self, msg: str):
        self._emit(logging.INFO, msg)

    def warning(self, msg: str):
        self._emit(logging.WARNING, msg)

    def error(self, msg: str):
        self._emit(logging.ERROR, msg)

    # Backward compatibility
    def log(self, msg: str):
        self.info(msg)

    # ==================================================
    # Context
    # ==================================================

    def with_context(self, **ctx) -> "RunLogger":
        return RunLogger(
            name=self.name,
            cfg=self.cfg,
            prefix=self.prefix,
            context={**self.context, **ctx},
            logger=self.logger,
        )

    # ==================================================
    # Timing helpers
    # ==================================================

    def step(self, label: str):
        if not self.cfg.timing:
            return

        now = perf_counter()
        delta = now - self._t_last
        total = now - self._t0

        self.info(
            f"⏱️ {label:<30} +{delta:6.2f}s | total {total:6.2f}s"
        )
        self._t_last = now

    @contextmanager
    def time(self, label: str):
        if not self.cfg.timing:
            yield
            return

        t0 = perf_counter()
        yield
        dt = perf_counter() - t0
        self.info(f"⏱️ {label:<30} {dt:6.3f}s")

    @contextmanager
    def section(self, name: str):
        t0 = perf_counter()
        yield
        dt = perf_counter() - t0
        self._timings[name] = self._timings.get(name, 0.0) + dt
        self.info(f"⏱️ section {name} {dt:6.3f}s")

    def get_timings(self) -> dict[str, float]:
        return dict(self._timings)