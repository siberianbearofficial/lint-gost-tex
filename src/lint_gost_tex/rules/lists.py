from __future__ import annotations

import re
from dataclasses import dataclass

from ..context import LintContext
from ..issue import Issue
from ..tex import (
    WordScanner,
    find_matching_bracket,
    iter_env_tokens,
    mask_command_arguments,
    mask_comments_and_math,
)


@dataclass
class CustomListRule:
    allowed_envs: list[str]
    list_envs: list[str]
    disallow_begin_optional: bool
    disallow_item_optional: bool
    rule_id: str = "LST001"
    description: str = "Only default itemize/enumerate lists are allowed."

    def check(self, ctx: LintContext) -> list[Issue]:
        issues: list[Issue] = []
        allowed = set(self.allowed_envs)
        list_envs = {env.rstrip("*") for env in self.list_envs}
        begin_optional = re.compile(r"\\begin\s*\{(itemize|enumerate)\}\s*\[")
        item_optional = re.compile(r"\\item\s*\[")
        for tex_file in ctx.document.files:
            masked = mask_comments_and_math(tex_file.text)
            for kind, env, offset in iter_env_tokens(masked):
                if kind != "begin":
                    continue
                base_env = env.rstrip("*")
                if base_env in list_envs and env not in allowed:
                    issues.append(_issue(tex_file, offset, self.rule_id, "custom list environment used"))
            if self.disallow_begin_optional:
                for match in begin_optional.finditer(masked):
                    issues.append(_issue(tex_file, match.start(), self.rule_id, "list has custom begin options"))
            if self.disallow_item_optional:
                for match in item_optional.finditer(masked):
                    issues.append(_issue(tex_file, match.start(), self.rule_id, "list item uses custom label"))
        return issues


@dataclass
class NestedListRule:
    list_envs: list[str]
    rule_id: str = "LST002"
    description: str = "Nested lists are not allowed."

    def check(self, ctx: LintContext) -> list[Issue]:
        issues: list[Issue] = []
        list_envs = {env.rstrip("*") for env in self.list_envs}
        for tex_file in ctx.document.files:
            masked = mask_comments_and_math(tex_file.text)
            stack: list[str] = []
            for kind, env, offset in iter_env_tokens(masked):
                base_env = env.rstrip("*")
                if base_env not in list_envs:
                    continue
                if kind == "begin":
                    if stack:
                        issues.append(_issue(tex_file, offset, self.rule_id, "nested list detected"))
                    stack.append(base_env)
                else:
                    if stack and stack[-1] == base_env:
                        stack.pop()
        return issues


@dataclass
class ListItemPunctuationRule:
    list_envs: list[str]
    skip_commands: list[str]
    two_arg_commands: list[str]
    sentence_endings: list[str]
    last_end: str
    non_last_end: str
    rule_id_end: str = "LST003"
    rule_id_sentence: str = "LST004"
    description: str = "List items must use semicolons and single sentences."

    def check(self, ctx: LintContext) -> list[Issue]:
        issues: list[Issue] = []
        list_envs = {env.rstrip("*") for env in self.list_envs}
        endings = set(self.sentence_endings)
        two_arg = set(self.two_arg_commands)
        for tex_file in ctx.document.files:
            masked = mask_comments_and_math(tex_file.text)
            masked = mask_command_arguments(masked, self.skip_commands, two_arg)
            lists = _collect_list_items(masked, list_envs)
            for items in lists:
                for index, item in enumerate(items):
                    if item.end is None:
                        continue
                    last_index = _last_nonspace_index(masked, item.content_start, item.end)
                    if last_index < item.content_start:
                        continue
                    last_char = masked[last_index]
                    expected = self.last_end if index == len(items) - 1 else self.non_last_end
                    if last_char != expected:
                        issues.append(
                            _issue(
                                tex_file,
                                last_index,
                                self.rule_id_end,
                                f"list item must end with '{expected}'",
                            )
                        )
                    sentence_positions = _sentence_end_positions(
                        masked, item.content_start, item.end, endings
                    )
                    if any(pos < last_index for pos in sentence_positions):
                        issues.append(
                            _issue(
                                tex_file,
                                sentence_positions[0],
                                self.rule_id_sentence,
                                "list item contains multiple sentences",
                            )
                        )
        return issues


@dataclass
class ListItemCaseRule:
    list_envs: list[str]
    skip_commands: list[str]
    two_arg_commands: list[str]
    rule_id: str = "LST005"
    description: str = "List items must not start with uppercase letters."

    def check(self, ctx: LintContext) -> list[Issue]:
        issues: list[Issue] = []
        list_envs = {env.rstrip("*") for env in self.list_envs}
        scanner = WordScanner(
            ignore_envs=set(),
            skip_commands=set(self.skip_commands),
            keep_commands=set(),
            skip_two_args=set(self.two_arg_commands),
        )
        for tex_file in ctx.document.files:
            masked = mask_comments_and_math(tex_file.text)
            lists = _collect_list_items(masked, list_envs)
            for items in lists:
                for item in items:
                    if item.end is None:
                        continue
                    content = tex_file.text[item.content_start : item.end]
                    first_word = None
                    first_offset = None
                    for word, rel_offset in scanner.iter_words(content):
                        first_word = word
                        first_offset = item.content_start + rel_offset
                        break
                    if not first_word:
                        continue
                    if first_word[0].isupper():
                        issues.append(
                            _issue(
                                tex_file,
                                first_offset if first_offset is not None else item.start,
                                self.rule_id,
                                "list item starts with uppercase letter",
                            )
                        )
        return issues


@dataclass
class _ListItem:
    start: int
    content_start: int
    end: int | None


def _collect_list_items(text: str, list_envs: set[str]) -> list[list[_ListItem]]:
    events: list[tuple[int, str, str | None]] = []
    for kind, env, offset in iter_env_tokens(text):
        base_env = env.rstrip("*")
        if base_env in list_envs:
            events.append((offset, kind, env))
    for match in re.finditer(r"\\item\b", text):
        events.append((match.start(), "item", None))
    events.sort(key=lambda item: item[0])

    stack: list[str] = []
    lists: list[list[_ListItem]] = []
    current_items: list[_ListItem] | None = None
    current_item: _ListItem | None = None

    for offset, kind, env in events:
        if kind in {"begin", "end"} and env is not None:
            base_env = env.rstrip("*")
            if kind == "begin":
                stack.append(base_env)
                if len(stack) == 1:
                    current_items = []
                    lists.append(current_items)
                    current_item = None
            else:
                if stack and stack[-1] == base_env:
                    stack.pop()
                elif base_env in stack:
                    while stack and stack[-1] != base_env:
                        stack.pop()
                    if stack:
                        stack.pop()
                if len(stack) == 0 and current_items is not None:
                    if current_item is not None and current_item.end is None:
                        current_item.end = offset
                    current_items = None
                    current_item = None
            continue
        if kind == "item":
            if not stack or len(stack) != 1 or current_items is None:
                continue
            if current_item is not None and current_item.end is None:
                current_item.end = offset
            content_start = _item_content_start(text, offset)
            current_item = _ListItem(start=offset, content_start=content_start, end=None)
            current_items.append(current_item)
    if current_items is not None and current_item is not None and current_item.end is None:
        current_item.end = len(text)
    return lists


def _item_content_start(text: str, offset: int) -> int:
    index = offset + len("\\item")
    index = _skip_space(text, index)
    if index < len(text) and text[index] == "[":
        end = find_matching_bracket(text, index)
        if end is not None:
            index = end + 1
    return index


def _skip_space(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def _last_nonspace_index(text: str, start: int, end: int) -> int:
    index = end - 1
    while index >= start and text[index].isspace():
        index -= 1
    return index


def _sentence_end_positions(text: str, start: int, end: int, endings: set[str]) -> list[int]:
    positions: list[int] = []
    index = start
    while index < end:
        char = text[index]
        if char in endings:
            if char == "." and _is_decimal_point(text, index, start, end):
                index += 1
                continue
            positions.append(index)
        index += 1
    return positions


def _is_decimal_point(text: str, index: int, start: int, end: int) -> bool:
    if index <= start or index + 1 >= end:
        return False
    return text[index - 1].isdigit() and text[index + 1].isdigit()


def _issue(tex_file, offset: int, rule_id: str, message: str) -> Issue:
    line, col = tex_file.line_col(offset)
    snippet = tex_file.line_text(line)
    return Issue(rule_id=rule_id, message=message, path=tex_file.path, line=line, col=col, snippet=snippet)
