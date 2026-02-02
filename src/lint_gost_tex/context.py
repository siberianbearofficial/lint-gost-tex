from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .document import Document


@dataclass
class LintContext:
    document: Document
    config: Config
    base_dir: Path
    config_path: Path | None
