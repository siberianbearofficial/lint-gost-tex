from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .config import DocumentConfig
from .tex import strip_comments_keep_length

INCLUDE_RE = re.compile(r"\\(?:include|input)\s*\{([^}]+)\}")


@dataclass
class TexFile:
    path: Path
    text: str
    line_offsets: list[int]

    @staticmethod
    def from_path(path: Path) -> "TexFile":
        text = path.read_text(encoding="utf-8")
        return TexFile(path=path, text=text, line_offsets=_build_line_offsets(text))

    def line_col(self, offset: int) -> tuple[int, int]:
        if offset < 0:
            return 1, 1
        line_index = _bisect_line(self.line_offsets, offset)
        line_start = self.line_offsets[line_index]
        return line_index + 1, offset - line_start + 1

    def line_text(self, line: int) -> str:
        if line < 1:
            return ""
        start = self.line_offsets[line - 1]
        if line < len(self.line_offsets):
            end = self.line_offsets[line]
            return self.text[start:end].rstrip("\n")
        return self.text[start:].rstrip("\n")


@dataclass
class Document:
    files: list[TexFile]
    base_dir: Path

    def path_index(self) -> dict[Path, int]:
        return {file.path: idx for idx, file in enumerate(self.files)}


def load_document(config: DocumentConfig, base_dir: Path) -> Document:
    root = config.root
    paths = [root]
    for include_path in _collect_includes(root):
        paths.append(include_path)
    unique_paths = _unique_paths(paths)
    files: list[TexFile] = []
    for path in unique_paths:
        if config.is_excluded(path):
            continue
        if not path.exists():
            continue
        files.append(TexFile.from_path(path))
    return Document(files=files, base_dir=base_dir)


def _collect_includes(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    text = root.read_text(encoding="utf-8")
    masked = strip_comments_keep_length(text)
    base = root.parent
    results: list[Path] = []
    for match in INCLUDE_RE.finditer(masked):
        raw = match.group(1).strip()
        if not raw:
            continue
        candidate = Path(raw)
        if candidate.suffix == "":
            candidate = candidate.with_suffix(".tex")
        results.append(base / candidate)
    return results


def _unique_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        result.append(path)
    return result


def _build_line_offsets(text: str) -> list[int]:
    offsets = [0]
    for index, char in enumerate(text):
        if char == "\n":
            offsets.append(index + 1)
    return offsets


def _bisect_line(offsets: list[int], offset: int) -> int:
    low = 0
    high = len(offsets) - 1
    while low <= high:
        mid = (low + high) // 2
        if offsets[mid] <= offset:
            low = mid + 1
        else:
            high = mid - 1
    return max(high, 0)
