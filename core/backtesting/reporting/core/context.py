from dataclasses import dataclass
from typing import Optional, Set

@dataclass(frozen=True)
class ContextSpec:
    name: str
    column: str
    allowed_values: Optional[Set] = None