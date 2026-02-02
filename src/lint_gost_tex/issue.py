from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Issue:
    rule_id: str
    message: str
    path: Path
    line: int
    col: int
    snippet: str
