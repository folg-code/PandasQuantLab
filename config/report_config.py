from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class StdoutMode(str, Enum):
    OFF = "off"
    CONSOLE = "console"
    FILE = "file"
    BOTH = "both"


@dataclass(frozen=True)
class ReportConfig:
    """
    Runtime configuration for report generation.

    Controls:
    - stdout rendering
    - dashboard generation
    - persistence
    """

    # ==================================================
    # STDOUT
    # ==================================================

    stdout_mode: StdoutMode = StdoutMode.CONSOLE

    # Used only if FILE or BOTH
    stdout_file: Path | None = None

    # ==================================================
    # DASHBOARD / FILE OUTPUT
    # ==================================================

    generate_dashboard: bool = True
    persist_report: bool = True

    # ==================================================
    # SAFETY / RESEARCH
    # ==================================================

    fail_on_empty: bool = True