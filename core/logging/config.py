from dataclasses import dataclass
from pathlib import Path


@dataclass
class LoggerConfig:
    stdout: bool = True
    file: bool = False
    timing: bool = True
    profiling: bool = False
    log_dir: Path | None = None
    level: int = 20  