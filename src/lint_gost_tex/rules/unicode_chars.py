from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from ..context import LintContext
from ..issue import Issue


@dataclass
class UnicodeCharRule:
    allowed_extra: list[str]
    rule_id: str = "UNIC001"
    description: str = "Non-keyboard characters are not allowed."

    def check(self, ctx: LintContext) -> list[Issue]:
        issues: list[Issue] = []
        allowed_extra = set("".join(self.allowed_extra))
        for tex_file in ctx.document.files:
            for offset, char in enumerate(tex_file.text):
                if _is_allowed_char(char, allowed_extra):
                    continue
                code = f"U+{ord(char):04X}"
                name = unicodedata.name(char, "UNKNOWN")
                message = f"non-keyboard character {code} ({name})"
                issues.append(_issue(tex_file, offset, self.rule_id, message))
        return issues


def _is_allowed_char(char: str, allowed_extra: set[str]) -> bool:
    if char in {"\n", "\r", "\t"}:
        return True
    if char.isascii():
        return 32 <= ord(char) <= 126
    if char in allowed_extra:
        return True
    return _is_russian_letter(char)


def _is_russian_letter(char: str) -> bool:
    code = ord(char)
    return code == 0x0401 or code == 0x0451 or 0x0410 <= code <= 0x044F


def _issue(tex_file, offset: int, rule_id: str, message: str) -> Issue:
    line, col = tex_file.line_col(offset)
    snippet = tex_file.line_text(line)
    return Issue(rule_id=rule_id, message=message, path=tex_file.path, line=line, col=col, snippet=snippet)
