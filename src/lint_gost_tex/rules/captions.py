from __future__ import annotations

import re
from dataclasses import dataclass

from ..context import LintContext
from ..issue import Issue
from ..tex import iter_command_spans, mask_comments_and_math

LABEL_RE = re.compile(r"\\label\s*\{[^}]*\}")


@dataclass
class CaptionPunctuationRule:
    commands: list[str]
    forbid_trailing: list[str]
    rule_id: str = "CAP001"
    description: str = "Captions must not end with punctuation."

    def check(self, ctx: LintContext) -> list[Issue]:
        issues: list[Issue] = []
        forbidden = set(self.forbid_trailing)
        for tex_file in ctx.document.files:
            masked = mask_comments_and_math(tex_file.text)
            for command in self.commands:
                for span in iter_command_spans(masked, command):
                    if span.argument is None:
                        continue
                    last_char = _last_visible_char(span.argument)
                    if last_char in forbidden:
                        issues.append(_issue(tex_file, span.start, self.rule_id, "caption ends with punctuation"))
        return issues


def _last_visible_char(text: str) -> str:
    cleaned = LABEL_RE.sub("", text).rstrip()
    index = len(cleaned) - 1
    while index >= 0 and cleaned[index] in {"}", "{", " "}:
        index -= 1
    return cleaned[index] if index >= 0 else ""


def _issue(tex_file, offset: int, rule_id: str, message: str) -> Issue:
    line, col = tex_file.line_col(offset)
    snippet = tex_file.line_text(line)
    return Issue(rule_id=rule_id, message=message, path=tex_file.path, line=line, col=col, snippet=snippet)
