from __future__ import annotations

from dataclasses import dataclass

from ..context import LintContext
from ..issue import Issue
from ..tex import make_command_pattern, mask_comments_and_math


@dataclass
class RefSpacingRule:
    commands: list[str]
    rule_id: str = "REF001"
    description: str = "References must use a single non-breaking space."

    def check(self, ctx: LintContext) -> list[Issue]:
        issues: list[Issue] = []
        pattern = make_command_pattern(self.commands)
        for tex_file in ctx.document.files:
            masked = mask_comments_and_math(tex_file.text)
            for match in pattern.finditer(masked):
                index = match.start()
                if index == 0:
                    issues.append(_issue(tex_file, index, self.rule_id, "missing '~' before reference"))
                    continue
                if masked[index - 1] != "~":
                    issues.append(_issue(tex_file, index, self.rule_id, "missing '~' before reference"))
                    continue
                if index >= 2 and masked[index - 2] == "~":
                    issues.append(_issue(tex_file, index - 1, self.rule_id, "use exactly one '~'"))
        return issues


@dataclass
class LinkPunctuationRule:
    commands: list[str]
    rule_id: str = "REF002"
    description: str = "Links must appear before sentence-ending punctuation."

    def check(self, ctx: LintContext) -> list[Issue]:
        issues: list[Issue] = []
        pattern = make_command_pattern(self.commands)
        for tex_file in ctx.document.files:
            masked = mask_comments_and_math(tex_file.text)
            for match in pattern.finditer(masked):
                index = match.start()
                prev_index = _previous_nonspace_index(masked, index - 1)
                prev_char = masked[prev_index] if prev_index >= 0 else ""
                prev_char = _skip_closing(masked, prev_index)
                if prev_char in {".", "!", "?"}:
                    issues.append(_issue(tex_file, index, self.rule_id, "link follows sentence-ending punctuation"))
        return issues


def _previous_nonspace_index(text: str, index: int) -> int:
    while index >= 0 and text[index].isspace():
        index -= 1
    return index


def _skip_closing(text: str, index: int) -> str:
    closers = {")", "]", "}", "\"", "'"}
    while index >= 0 and text[index] in closers:
        index -= 1
        while index >= 0 and text[index].isspace():
            index -= 1
    return text[index] if index >= 0 else ""


def _issue(tex_file, offset: int, rule_id: str, message: str) -> Issue:
    line, col = tex_file.line_col(offset)
    snippet = tex_file.line_text(line)
    return Issue(rule_id=rule_id, message=message, path=tex_file.path, line=line, col=col, snippet=snippet)
