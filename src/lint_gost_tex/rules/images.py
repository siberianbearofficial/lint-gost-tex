from __future__ import annotations

from dataclasses import dataclass

from ..context import LintContext
from ..issue import Issue
from ..tex import mask_comments_and_math, split_options, iter_command_spans


@dataclass
class ImageWidthRule:
    required_width: str
    rule_id: str = "IMG001"
    description: str = "Images must use a fixed width."

    def check(self, ctx: LintContext) -> list[Issue]:
        issues: list[Issue] = []
        required_norm = _normalize_tex(self.required_width)
        for tex_file in ctx.document.files:
            masked = mask_comments_and_math(tex_file.text)
            for span in iter_command_spans(masked, "includegraphics"):
                if span.optional is None:
                    issues.append(_issue(tex_file, span.start, self.rule_id, required_norm))
                    continue
                options = _parse_options(span.optional)
                width = options.get("width")
                if width is None or _normalize_tex(width) != required_norm:
                    issues.append(_issue(tex_file, span.start, self.rule_id, required_norm))
        return issues


def _parse_options(optional: str) -> dict[str, str]:
    options: dict[str, str] = {}
    for item in split_options(optional):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        options[key.strip()] = value.strip()
    return options


def _normalize_tex(value: str) -> str:
    normalized = "".join(value.split())
    if normalized.startswith("{") and normalized.endswith("}"):
        return normalized[1:-1]
    return normalized


def _issue(tex_file, offset: int, rule_id: str, required_norm: str) -> Issue:
    line, col = tex_file.line_col(offset)
    snippet = tex_file.line_text(line)
    message = f"includegraphics width must be {required_norm}"
    return Issue(rule_id=rule_id, message=message, path=tex_file.path, line=line, col=col, snippet=snippet)
