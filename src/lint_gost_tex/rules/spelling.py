from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import DEFAULT_CONFIG_FILENAME
from ..context import LintContext
from ..issue import Issue
from ..tex import WORD_RE, WordScanner

SYSTEM_EN_WORDLISTS = [Path("/usr/share/dict/words"), Path("/usr/dict/words")]
SKIP_TWO_ARGS = {"href", "hyperref"}
SECOND_ARG_COMMANDS = {"captionof"}
PIXEL_FORMS = {
    "пиксель",
    "пикселя",
    "пикселю",
    "пикселем",
    "пикселе",
    "пиксели",
    "пикселей",
    "пикселям",
    "пикселями",
    "пикселях",
}
PIXEL_ALLOWED_FORMS = {
    "пиксел",
    "пиксела",
    "пикселу",
    "пикселом",
    "пикселе",
    "пикселы",
    "пикселов",
    "пикселам",
    "пикселами",
    "пикселах",
}


@dataclass
class SpellcheckRule:
    custom_dict: Path
    extra_ru_dicts: list[Path]
    extra_en_dicts: list[Path]
    ignore_envs: list[str]
    skip_commands: list[str]
    keep_commands: list[str]
    min_word_length: int
    ignore_uppercase_acronyms: bool
    rule_id_unknown: str = "SPELL001"
    rule_id_banned: str = "SPELL002"
    rule_id_yo: str = "SPELL003"
    rule_id_dict: str = "SPELL000"

    def check(self, ctx: LintContext) -> list[Issue]:
        issues: list[Issue] = []
        custom_words = _load_wordlists([self.custom_dict])
        ru_words = _load_wordlists(self.extra_ru_dicts)
        en_words = _load_wordlists(self.extra_en_dicts + _system_wordlists())

        if not ru_words:
            issues.append(_config_issue(ctx, self.rule_id_dict, "missing Russian dictionary"))
        if not en_words:
            issues.append(_config_issue(ctx, self.rule_id_dict, "missing English dictionary"))

        scanner = WordScanner(
            ignore_envs=set(self.ignore_envs),
            skip_commands=set(self.skip_commands),
            keep_commands=set(self.keep_commands),
            skip_two_args=SKIP_TWO_ARGS,
            second_arg_commands=SECOND_ARG_COMMANDS,
        )

        for tex_file in ctx.document.files:
            for word, offset in scanner.iter_words(tex_file.text):
                for part, part_offset in _split_hyphenated(word, offset):
                    _check_word(
                        part,
                        part_offset,
                        tex_file,
                        issues,
                        custom_words,
                        ru_words,
                        en_words,
                        self.min_word_length,
                        self.ignore_uppercase_acronyms,
                        self.rule_id_banned,
                        self.rule_id_yo,
                        self.rule_id_unknown,
                    )

        return issues


def _system_wordlists() -> list[Path]:
    return [path for path in SYSTEM_EN_WORDLISTS if path.exists()]


def _load_wordlists(paths: list[Path]) -> set[str]:
    words: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        try:
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                lowered = stripped.casefold()
                if WORD_RE.fullmatch(lowered):
                    words.add(lowered)
        except OSError:
            continue
    return words


def _split_hyphenated(word: str, offset: int) -> list[tuple[str, int]]:
    if "-" not in word:
        return [(word, offset)]
    parts: list[tuple[str, int]] = []
    current = offset
    for part in word.split("-"):
        if part:
            parts.append((part, current))
        current += len(part) + 1
    return parts


def _check_word(
    word: str,
    offset: int,
    tex_file,
    issues: list[Issue],
    custom_words: set[str],
    ru_words: set[str],
    en_words: set[str],
    min_word_length: int,
    ignore_uppercase_acronyms: bool,
    rule_id_banned: str,
    rule_id_yo: str,
    rule_id_unknown: str,
) -> None:
    if len(word) < min_word_length:
        return
    if ignore_uppercase_acronyms and word.isupper() and len(word) <= 5:
        return
    if any(char.isdigit() for char in word):
        return
    if _is_mixed_script(word):
        return

    lowered = word.casefold()
    if lowered in PIXEL_FORMS:
        issues.append(_issue(tex_file, offset, rule_id_banned, "use 'пиксел' without soft sign"))
        return
    if lowered in PIXEL_ALLOWED_FORMS:
        return

    if _is_cyrillic(word):
        if ru_words:
            if lowered in custom_words or lowered in ru_words:
                if _requires_yo(lowered, ru_words | custom_words):
                    issues.append(_issue(tex_file, offset, rule_id_yo, "use 'ё' instead of 'е'"))
                return
            issues.append(_issue(tex_file, offset, rule_id_unknown, f"unknown word '{word}'"))
        return

    if _is_latin(word):
        if en_words:
            if lowered in custom_words or lowered in en_words:
                return
            issues.append(_issue(tex_file, offset, rule_id_unknown, f"unknown word '{word}'"))


def _requires_yo(word: str, dictionary: set[str]) -> bool:
    if "е" not in word or "ё" in word:
        return False
    positions = [index for index, char in enumerate(word) if char == "е"]
    if not positions:
        return False
    max_variants = 128
    found = False
    checked = 0

    def dfs(pos_index: int, chars: list[str], replaced: bool) -> None:
        nonlocal found, checked
        if found or checked >= max_variants:
            return
        if pos_index == len(positions):
            if replaced:
                checked += 1
                candidate = "".join(chars)
                if candidate in dictionary:
                    found = True
            return
        dfs(pos_index + 1, chars, replaced)
        chars[positions[pos_index]] = "ё"
        dfs(pos_index + 1, chars, True)
        chars[positions[pos_index]] = "е"

    dfs(0, list(word), False)
    return found


def _is_cyrillic(word: str) -> bool:
    return all("а" <= char.casefold() <= "я" or char in {"ё", "Ё"} or char == "-" for char in word)


def _is_latin(word: str) -> bool:
    return all("a" <= char.casefold() <= "z" or char == "-" for char in word)


def _is_mixed_script(word: str) -> bool:
    has_cyrillic = any("а" <= char.casefold() <= "я" or char in {"ё", "Ё"} for char in word)
    has_latin = any("a" <= char.casefold() <= "z" for char in word)
    return has_cyrillic and has_latin


def _issue(tex_file, offset: int, rule_id: str, message: str) -> Issue:
    line, col = tex_file.line_col(offset)
    snippet = tex_file.line_text(line)
    return Issue(rule_id=rule_id, message=message, path=tex_file.path, line=line, col=col, snippet=snippet)


def _config_issue(ctx: LintContext, rule_id: str, message: str) -> Issue:
    path = ctx.config_path or ctx.document.base_dir / DEFAULT_CONFIG_FILENAME
    line = 1
    col = 1
    snippet = ""
    if path.exists():
        text = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if text:
            snippet = text[0]
    return Issue(rule_id=rule_id, message=message, path=path, line=line, col=col, snippet=snippet)
