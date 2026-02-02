from __future__ import annotations

import re
from dataclasses import dataclass

from ..context import LintContext
from ..issue import Issue
from ..tex import mask_comments_and_math, mask_command_arguments


@dataclass
class AbbreviationRule:
    banned_words: list[str]
    banned_patterns: list[str]
    allow_words: list[str]
    skip_commands: list[str]
    two_arg_commands: list[str]
    rule_id: str = "ABBR001"
    description: str = "Abbreviations are not allowed."

    def check(self, ctx: LintContext) -> list[Issue]:
        issues: list[Issue] = []
        allow = {word.casefold() for word in self.allow_words}
        patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.banned_patterns]
        word_patterns: list[re.Pattern[str]] = []
        for word in self.banned_words:
            normalized = word.strip().rstrip(".")
            if not normalized:
                continue
            if normalized.casefold() in allow:
                continue
            word_patterns.append(re.compile(rf"(?i)\b{re.escape(normalized)}\."))
        two_arg = set(self.two_arg_commands)
        for tex_file in ctx.document.files:
            masked = mask_comments_and_math(tex_file.text)
            masked = mask_command_arguments(masked, self.skip_commands, two_arg)
            seen: set[int] = set()
            for pattern in word_patterns:
                for match in pattern.finditer(masked):
                    if match.start() in seen:
                        continue
                    seen.add(match.start())
                    issues.append(
                        _issue(
                            tex_file,
                            match.start(),
                            self.rule_id,
                            f"abbreviation '{match.group(0)}' is not allowed",
                        )
                    )
            for pattern in patterns:
                for match in pattern.finditer(masked):
                    if match.start() in seen:
                        continue
                    seen.add(match.start())
                    issues.append(
                        _issue(
                            tex_file,
                            match.start(),
                            self.rule_id,
                            f"abbreviation '{match.group(0)}' is not allowed",
                        )
                    )
        return issues


def _issue(tex_file, offset: int, rule_id: str, message: str) -> Issue:
    line, col = tex_file.line_col(offset)
    snippet = tex_file.line_text(line)
    return Issue(rule_id=rule_id, message=message, path=tex_file.path, line=line, col=col, snippet=snippet)
