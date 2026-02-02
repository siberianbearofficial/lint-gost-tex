from __future__ import annotations

import argparse
import os
from pathlib import Path

from .config import DEFAULT_CONFIG_FILENAME, Config, DocumentConfig
from .context import LintContext
from .document import load_document
from .rules import build_rules


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint LaTeX sources.")
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_FILENAME,
        help="Path to lint-gost-tex config file.",
    )
    parser.add_argument("--root", help="Override root .tex file path.")
    args = parser.parse_args(argv)

    base_dir = Path.cwd()
    config_path = Path(args.config) if args.config else None
    config = Config.load(config_path, base_dir)
    if args.root:
        root_path = Path(args.root)
        if not root_path.is_absolute():
            root_path = base_dir / root_path
        config = _override_root(config, root_path)

    document = load_document(config.document, base_dir)
    ctx = LintContext(document=document, config=config, base_dir=base_dir, config_path=config_path)
    issues = []
    for rule in build_rules(config):
        issues.extend(rule.check(ctx))

    path_index = document.path_index()
    issues.sort(key=lambda item: (path_index.get(item.path, 9999), item.line, item.col, item.rule_id))

    for issue in issues:
        print(_format_issue(issue, base_dir))

    if issues:
        print(f"{len(issues)} issue(s) found.")
        return 1
    print("No issues found.")
    return 0


def _override_root(config: Config, root: Path) -> Config:
    document = DocumentConfig(root=root, exclude=config.document.exclude)
    return Config(
        document=document,
        images=config.images,
        refs=config.refs,
        links=config.links,
        styles=config.styles,
        lists=config.lists,
        captions=config.captions,
        illustrations=config.illustrations,
        abbrev=config.abbrev,
        unicode=config.unicode,
        list_items=config.list_items,
        spellcheck=config.spellcheck,
    )


def _format_issue(issue, base_dir: Path) -> str:
    path = _rel_path(issue.path, base_dir)
    location = f"{path}:{issue.line}:{issue.col}"
    lines = [f"{location} [{issue.rule_id}] {issue.message}"]
    if issue.snippet:
        lines.append(f"  | {issue.snippet}")
        if issue.col > 0:
            caret = " " * (issue.col - 1)
            lines.append(f"  | {caret}^")
    return "\n".join(lines)


def _rel_path(path: Path, base_dir: Path) -> str:
    try:
        return os.path.relpath(path, base_dir)
    except ValueError:
        return str(path)
