"""LaTeX linting package for GOST-styled documents."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


try:
    __version__ = version("lint-gost-tex")
except PackageNotFoundError:  # pragma: no cover - fallback for editable installs
    __version__ = "0.0.0"

__all__ = ["__version__"]
