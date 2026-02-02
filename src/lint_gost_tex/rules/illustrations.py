from __future__ import annotations

import re
from dataclasses import dataclass

from ..context import LintContext
from ..issue import Issue
from ..tex import iter_command_spans, iter_env_tokens, mask_comments_and_math

LABEL_RE = re.compile(r"\\label\s*\{([^}]+)\}")


@dataclass
class IllustrationOrderRule:
    envs: list[str]
    ref_commands: list[str]
    rule_id_missing: str = "ILL002"
    rule_id_order: str = "ILL001"
    description: str = "Illustrations must appear after their first reference."

    def check(self, ctx: LintContext) -> list[Issue]:
        issues: list[Issue] = []
        envs = {env for env in self.envs}
        ref_positions = _collect_ref_positions(ctx, self.ref_commands)

        for file_index, tex_file in enumerate(ctx.document.files):
            masked = mask_comments_and_math(tex_file.text)
            for env_name, start_offset, end_offset in _collect_env_blocks(masked, envs):
                labels = _collect_labels(masked[start_offset:end_offset])
                for label in labels:
                    ref_pos = ref_positions.get(label)
                    if ref_pos is None:
                        issues.append(
                            _issue(
                                tex_file,
                                start_offset,
                                self.rule_id_missing,
                                f"no reference found for label '{label}'",
                            )
                        )
                        continue
                    if ref_pos >= (file_index, start_offset):
                        issues.append(
                            _issue(
                                tex_file,
                                start_offset,
                                self.rule_id_order,
                                f"illustration appears before first reference to '{label}'",
                            )
                        )
        return issues


def _collect_env_blocks(text: str, envs: set[str]) -> list[tuple[str, int, int]]:
    blocks: list[tuple[str, int, int]] = []
    stack: list[tuple[str, int]] = []
    for kind, env, offset in iter_env_tokens(text):
        if env not in envs:
            continue
        if kind == "begin":
            stack.append((env, offset))
        else:
            for index in range(len(stack) - 1, -1, -1):
                if stack[index][0] == env:
                    _, start = stack.pop(index)
                    blocks.append((env, start, offset))
                    break
    return blocks


def _collect_labels(text: str) -> list[str]:
    return [match.group(1).strip() for match in LABEL_RE.finditer(text) if match.group(1).strip()]


def _collect_ref_positions(ctx: LintContext, commands: list[str]) -> dict[str, tuple[int, int]]:
    positions: dict[str, tuple[int, int]] = {}
    for file_index, tex_file in enumerate(ctx.document.files):
        masked = mask_comments_and_math(tex_file.text)
        for command in commands:
            for span in iter_command_spans(masked, command):
                if span.argument is None:
                    continue
                for label in span.argument.split(","):
                    label = label.strip()
                    if not label:
                        continue
                    pos = (file_index, span.start)
                    if label not in positions or pos < positions[label]:
                        positions[label] = pos
    return positions


def _issue(tex_file, offset: int, rule_id: str, message: str) -> Issue:
    line, col = tex_file.line_col(offset)
    snippet = tex_file.line_text(line)
    return Issue(rule_id=rule_id, message=message, path=tex_file.path, line=line, col=col, snippet=snippet)
