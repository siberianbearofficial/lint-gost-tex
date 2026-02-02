from __future__ import annotations

import re
from dataclasses import dataclass

from ..context import LintContext
from ..issue import Issue
from ..tex import mask_comments_and_math


@dataclass
class TextStyleRule:
    commands: list[str]
    rule_id: str = "TXT001"
    description: str = "Underline and italics are not allowed."

    def check(self, ctx: LintContext) -> list[Issue]:
        issues: list[Issue] = []
        pattern = _make_pattern(self.commands)
        for tex_file in ctx.document.files:
            masked = mask_comments_and_math(tex_file.text)
            for match in pattern.finditer(masked):
                line, col = tex_file.line_col(match.start())
                snippet = tex_file.line_text(line)
                issues.append(
                    Issue(
                        rule_id=self.rule_id,
                        message="underline/italic command used",
                        path=tex_file.path,
                        line=line,
                        col=col,
                        snippet=snippet,
                    )
                )
        return issues


def _make_pattern(commands: list[str]) -> re.Pattern[str]:
    escaped = [re.escape(command) for command in commands if command]
    if not escaped:
        return re.compile(r"a^")
    joined = "|".join(escaped)
    return re.compile(rf"\\(?:{joined})\b")
