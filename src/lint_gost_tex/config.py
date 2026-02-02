from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib

DEFAULT_CONFIG_FILENAME = "lint-gost-tex.toml"
DEFAULT_DOCUMENT_ROOT = "main.tex"
DEFAULT_CUSTOM_DICT = "dictionaries/custom.txt"
DEFAULT_RU_DICTS = ["dictionaries/ru.txt"]
DEFAULT_SKIP_COMMANDS = [
    "include",
    "input",
    "cite",
    "citep",
    "citet",
    "citealp",
    "citeauthor",
    "citeyear",
    "citeyearpar",
    "ref",
    "eqref",
    "autoref",
    "pageref",
    "cref",
    "Cref",
    "label",
    "url",
    "href",
    "hyperref",
    "includegraphics",
    "includepdf",
    "graphicspath",
]
DEFAULT_TWO_ARG_COMMANDS = ["href", "hyperref"]
DEFAULT_ABBREV_WORDS = [
    "\u0441\u043c",
    "\u0440\u0438\u0441",
    "\u0442\u0430\u0431\u043b",
    "\u0441\u0442\u0440",
    "\u0433\u043b",
    "\u0440\u0430\u0437\u0434",
    "\u043f\u0440\u0438\u043b",
]
DEFAULT_ABBREV_PATTERNS = [
    "\\b\\u0442\\.\\s*\\u0434\\.",
    "\\b\\u0442\\.\\s*\\u043f\\.",
    "\\b\\u0438\\s+\\u0442\\.\\s*\\u0434\\.",
    "\\b\\u0438\\s+\\u0442\\.\\s*\\u043f\\.",
    "\\b\\u0442\\.\\s*\\u0435\\.",
    "\\b\\u0442\\.\\s*\\u043a\\.",
    "\\b\\u0442\\.\\s*\\u043e\\.",
    "\\b\\u0438\\s+\\u0434\\u0440\\.",
]

DEFAULT_CONFIG: dict[str, Any] = {
    "document": {
        "root": DEFAULT_DOCUMENT_ROOT,
        "exclude": [],
    },
    "rules": {
        "images": {
            "required_width": "0.9\\textwidth",
        },
        "refs": {
            "commands": ["ref", "eqref", "autoref", "pageref", "cref", "Cref"],
        },
        "links": {
            "commands": [
                "ref",
                "eqref",
                "autoref",
                "pageref",
                "cref",
                "Cref",
                "cite",
                "citep",
                "citet",
                "citealp",
                "citeauthor",
                "citeyear",
                "citeyearpar",
                "url",
                "href",
                "hyperref",
            ],
        },
        "styles": {
            "commands": ["underline", "uline", "ul", "textit", "textsl", "emph", "em", "itshape", "it"],
        },
        "lists": {
            "allowed_envs": ["itemize", "enumerate"],
            "list_envs": ["itemize", "enumerate", "description", "list"],
            "disallow_begin_optional": True,
            "disallow_item_optional": True,
        },
        "captions": {
            "commands": ["caption", "captionof"],
            "forbid_trailing": [".", ",", ";", ":", "!", "?"],
        },
        "illustrations": {
            "envs": ["figure", "table", "figure*", "table*"],
            "ref_commands": ["ref", "autoref", "cref", "Cref", "pageref", "eqref"],
        },
        "abbrev": {
            "banned_words": DEFAULT_ABBREV_WORDS,
            "banned_patterns": DEFAULT_ABBREV_PATTERNS,
            "allow_words": [],
            "skip_commands": DEFAULT_SKIP_COMMANDS,
            "two_arg_commands": DEFAULT_TWO_ARG_COMMANDS,
        },
        "unicode": {
            "allowed_extra": ["\u2116", "\u00ab", "\u00bb"],
        },
        "list_items": {
            "skip_commands": DEFAULT_SKIP_COMMANDS,
            "two_arg_commands": DEFAULT_TWO_ARG_COMMANDS,
            "sentence_endings": [".", "!", "?"],
            "last_end": ".",
            "non_last_end": ";",
        },
    },
    "spellcheck": {
        "custom_dict": DEFAULT_CUSTOM_DICT,
        "extra_ru_dicts": DEFAULT_RU_DICTS,
        "extra_en_dicts": [],
        "ignore_envs": [
            "lstlisting",
            "verbatim",
            "verbatim*",
            "minted",
            "tikzpicture",
            "equation",
            "equation*",
            "align",
            "align*",
            "gather",
            "gather*",
            "multline",
            "multline*",
        ],
        "skip_commands": DEFAULT_SKIP_COMMANDS,
        "keep_commands": ["textbf", "textrm", "textsf", "texttt", "textsc"],
        "min_word_length": 2,
        "ignore_uppercase_acronyms": True,
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _resolve_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


@dataclass(frozen=True)
class DocumentConfig:
    root: Path
    exclude: list[str]

    def is_excluded(self, path: Path) -> bool:
        for pattern in self.exclude:
            pattern_path = Path(pattern)
            if pattern_path.name == pattern and path.name == pattern:
                return True
            if path.match(pattern):
                return True
        return False


@dataclass(frozen=True)
class ImagesRuleConfig:
    required_width: str


@dataclass(frozen=True)
class RefsRuleConfig:
    commands: list[str]


@dataclass(frozen=True)
class LinksRuleConfig:
    commands: list[str]


@dataclass(frozen=True)
class StylesRuleConfig:
    commands: list[str]


@dataclass(frozen=True)
class ListsRuleConfig:
    allowed_envs: list[str]
    list_envs: list[str]
    disallow_begin_optional: bool
    disallow_item_optional: bool


@dataclass(frozen=True)
class CaptionsRuleConfig:
    commands: list[str]
    forbid_trailing: list[str]


@dataclass(frozen=True)
class IllustrationsRuleConfig:
    envs: list[str]
    ref_commands: list[str]


@dataclass(frozen=True)
class AbbrevRuleConfig:
    banned_words: list[str]
    banned_patterns: list[str]
    allow_words: list[str]
    skip_commands: list[str]
    two_arg_commands: list[str]


@dataclass(frozen=True)
class UnicodeRuleConfig:
    allowed_extra: list[str]


@dataclass(frozen=True)
class ListItemsRuleConfig:
    skip_commands: list[str]
    two_arg_commands: list[str]
    sentence_endings: list[str]
    last_end: str
    non_last_end: str


@dataclass(frozen=True)
class SpellcheckConfig:
    custom_dict: Path
    extra_ru_dicts: list[Path]
    extra_en_dicts: list[Path]
    ignore_envs: list[str]
    skip_commands: list[str]
    keep_commands: list[str]
    min_word_length: int
    ignore_uppercase_acronyms: bool


@dataclass(frozen=True)
class Config:
    document: DocumentConfig
    images: ImagesRuleConfig
    refs: RefsRuleConfig
    links: LinksRuleConfig
    styles: StylesRuleConfig
    lists: ListsRuleConfig
    captions: CaptionsRuleConfig
    illustrations: IllustrationsRuleConfig
    abbrev: AbbrevRuleConfig
    unicode: UnicodeRuleConfig
    list_items: ListItemsRuleConfig
    spellcheck: SpellcheckConfig

    @staticmethod
    def load(config_path: Path | None, base_dir: Path) -> "Config":
        data = copy.deepcopy(DEFAULT_CONFIG)
        if config_path and config_path.exists():
            with config_path.open("rb") as handle:
                override = tomllib.load(handle)
            _deep_merge(data, override)
        return Config.from_dict(data, base_dir)

    @staticmethod
    def from_dict(data: dict[str, Any], base_dir: Path) -> "Config":
        document = data.get("document", {})
        rules = data.get("rules", {})
        spell = data.get("spellcheck", {})
        return Config(
            document=DocumentConfig(
                root=_resolve_path(base_dir, document.get("root", "report.tex")),
                exclude=list(document.get("exclude", [])),
            ),
            images=ImagesRuleConfig(
                required_width=rules.get("images", {}).get("required_width", "0.9\\textwidth"),
            ),
            refs=RefsRuleConfig(
                commands=list(rules.get("refs", {}).get("commands", [])),
            ),
            links=LinksRuleConfig(
                commands=list(rules.get("links", {}).get("commands", [])),
            ),
            styles=StylesRuleConfig(
                commands=list(rules.get("styles", {}).get("commands", [])),
            ),
            lists=ListsRuleConfig(
                allowed_envs=list(rules.get("lists", {}).get("allowed_envs", [])),
                list_envs=list(rules.get("lists", {}).get("list_envs", [])),
                disallow_begin_optional=bool(
                    rules.get("lists", {}).get("disallow_begin_optional", True)
                ),
                disallow_item_optional=bool(
                    rules.get("lists", {}).get("disallow_item_optional", True)
                ),
            ),
            captions=CaptionsRuleConfig(
                commands=list(rules.get("captions", {}).get("commands", [])),
                forbid_trailing=list(rules.get("captions", {}).get("forbid_trailing", [])),
            ),
            illustrations=IllustrationsRuleConfig(
                envs=list(rules.get("illustrations", {}).get("envs", [])),
                ref_commands=list(rules.get("illustrations", {}).get("ref_commands", [])),
            ),
            abbrev=AbbrevRuleConfig(
                banned_words=list(rules.get("abbrev", {}).get("banned_words", [])),
                banned_patterns=list(rules.get("abbrev", {}).get("banned_patterns", [])),
                allow_words=list(rules.get("abbrev", {}).get("allow_words", [])),
                skip_commands=list(rules.get("abbrev", {}).get("skip_commands", [])),
                two_arg_commands=list(rules.get("abbrev", {}).get("two_arg_commands", [])),
            ),
            unicode=UnicodeRuleConfig(
                allowed_extra=list(rules.get("unicode", {}).get("allowed_extra", [])),
            ),
            list_items=ListItemsRuleConfig(
                skip_commands=list(rules.get("list_items", {}).get("skip_commands", [])),
                two_arg_commands=list(rules.get("list_items", {}).get("two_arg_commands", [])),
                sentence_endings=list(rules.get("list_items", {}).get("sentence_endings", [])),
                last_end=str(rules.get("list_items", {}).get("last_end", ".")),
                non_last_end=str(rules.get("list_items", {}).get("non_last_end", ";")),
            ),
            spellcheck=SpellcheckConfig(
                custom_dict=_resolve_path(base_dir, spell.get("custom_dict", "")),
                extra_ru_dicts=[
                    _resolve_path(base_dir, value)
                    for value in spell.get("extra_ru_dicts", [])
                ],
                extra_en_dicts=[
                    _resolve_path(base_dir, value)
                    for value in spell.get("extra_en_dicts", [])
                ],
                ignore_envs=list(spell.get("ignore_envs", [])),
                skip_commands=list(spell.get("skip_commands", [])),
                keep_commands=list(spell.get("keep_commands", [])),
                min_word_length=int(spell.get("min_word_length", 2)),
                ignore_uppercase_acronyms=bool(spell.get("ignore_uppercase_acronyms", True)),
            ),
        )
