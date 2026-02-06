from core.logging.run_logger import RunLogger
from core.logging.config import LoggerConfig
from core.logging.prefix import LOG_PREFIX


def create_live_logger(symbol: str) -> RunLogger:
    cfg = LoggerConfig(
        stdout=True,
        file=False,
        timing=False,
        profiling=False,
    )

    return (
        RunLogger(
            name="live",
            cfg=cfg,
            prefix=LOG_PREFIX["LIVE"],
        )
        .with_context(symbol=symbol)
    )