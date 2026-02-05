from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Dict, Any

Executor = Literal["ENGINE", "BROKER", "DISABLED"]


@dataclass(frozen=True)
class ExitExecution:
    tp1: Executor = "ENGINE"
    tp2: Executor = "BROKER"
    be_on_tp1: bool = True

    @staticmethod
    def from_config(cfg: Dict[str, Any]) -> "ExitExecution":
        raw = (cfg or {}).get("EXIT_EXECUTION", {}) or {}

        return ExitExecution(
            tp1=raw.get("TP1", "ENGINE"),
            tp2=raw.get("TP2", "BROKER"),
            be_on_tp1=bool(raw.get("BE_ON_TP1", True)),
        )