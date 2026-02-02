from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:-[A-Za-zА-Яа-яЁё]+)*")
ENV_TOKEN_RE = re.compile(r"\\(begin|end)\s*\{([^}]+)\}")


def is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    pos = index - 1
    while pos >= 0 and text[pos] == "\\":
        backslashes += 1
        pos -= 1
    return (backslashes % 2) == 1


def strip_comments_keep_length(text: str) -> str:
    chars = list(text)
    index = 0
    while index < len(chars):
        if chars[index] == "%" and not is_escaped(text, index):
            while index < len(chars) and chars[index] != "\n":
                chars[index] = " "
                index += 1
            continue
        index += 1
    return "".join(chars)


def mask_math_keep_length(text: str) -> str:
    chars = list(text)
    index = 0
    while index < len(chars):
        if chars[index] == "$" and not is_escaped(text, index):
            if index + 1 < len(chars) and chars[index + 1] == "$":
                end = _find_next(text, "$$", index + 2)
                if end is None:
                    break
                _mask_range(chars, index, end + 2)
                index = end + 2
                continue
            end = _find_next(text, "$", index + 1)
            if end is None:
                break
            _mask_range(chars, index, end + 1)
            index = end + 1
            continue
        if text.startswith("\\(", index):
            end = text.find("\\)", index + 2)
            if end == -1:
                break
            _mask_range(chars, index, end + 2)
            index = end + 2
            continue
        if text.startswith("\\[", index):
            end = text.find("\\]", index + 2)
            if end == -1:
                break
            _mask_range(chars, index, end + 2)
            index = end + 2
            continue
        index += 1
    return "".join(chars)


def mask_comments_and_math(text: str) -> str:
    masked = strip_comments_keep_length(text)
    return mask_math_keep_length(masked)


def find_matching_brace(text: str, start: int) -> int | None:
    if start >= len(text) or text[start] != "{":
        return None
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char == "{" and not is_escaped(text, index):
            depth += 1
        elif char == "}" and not is_escaped(text, index):
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def find_matching_bracket(text: str, start: int) -> int | None:
    if start >= len(text) or text[start] != "[":
        return None
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char == "[" and not is_escaped(text, index):
            depth += 1
        elif char == "]" and not is_escaped(text, index):
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def split_options(options: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in options:
        if char == "{" and depth >= 0:
            depth += 1
        elif char == "}" and depth > 0:
            depth -= 1
        elif char == "," and depth == 0:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue
        current.append(char)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def iter_env_tokens(text: str) -> Iterable[tuple[str, str, int]]:
    for match in ENV_TOKEN_RE.finditer(text):
        yield match.group(1), match.group(2).strip(), match.start()


def make_command_pattern(commands: list[str]) -> re.Pattern[str]:
    escaped = [re.escape(command) for command in commands if command]
    if not escaped:
        return re.compile(r"a^")
    joined = "|".join(escaped)
    return re.compile(rf"\\(?:{joined})\s*\{{")


def _mask_range(chars: list[str], start: int, end: int) -> None:
    for index in range(start, min(end, len(chars))):
        if chars[index] != "\n":
            chars[index] = " "


def _find_next(text: str, needle: str, start: int) -> int | None:
    index = start
    while True:
        index = text.find(needle, index)
        if index == -1:
            return None
        if not is_escaped(text, index):
            return index
        index += len(needle)


@dataclass
class CommandSpan:
    name: str
    start: int
    end: int
    optional: str | None
    argument: str | None
    argument_start: int | None
    argument_end: int | None


def iter_command_spans(text: str, command: str) -> Iterable[CommandSpan]:
    pattern = re.compile(rf"\\{re.escape(command)}\b")
    for match in pattern.finditer(text):
        index = match.end()
        optional, index = _parse_optional(text, index)
        argument, arg_start, arg_end = _parse_braced(text, index)
        end = arg_end + 1 if arg_end is not None else index
        yield CommandSpan(
            name=command,
            start=match.start(),
            end=end,
            optional=optional,
            argument=argument,
            argument_start=arg_start,
            argument_end=arg_end,
        )


def _parse_optional(text: str, index: int) -> tuple[str | None, int]:
    index = _skip_whitespace(text, index)
    if index < len(text) and text[index] == "[":
        end = find_matching_bracket(text, index)
        if end is None:
            return None, index
        return text[index + 1 : end], end + 1
    return None, index


def _parse_braced(text: str, index: int) -> tuple[str | None, int | None, int | None]:
    index = _skip_whitespace(text, index)
    if index < len(text) and text[index] == "{":
        end = find_matching_brace(text, index)
        if end is None:
            return None, None, None
        return text[index + 1 : end], index + 1, end
    return None, None, None


def _skip_whitespace(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def mask_command_arguments(
    text: str,
    commands: list[str],
    two_arg_commands: set[str] | None = None,
) -> str:
    if not commands:
        return text
    two_arg_commands = two_arg_commands or set()
    chars = list(text)
    for command in commands:
        for span in iter_command_spans(text, command):
            if span.argument_start is not None and span.argument_end is not None:
                _mask_range(chars, span.argument_start, span.argument_end)
            if command in two_arg_commands and span.argument_end is not None:
                index = _skip_whitespace(text, span.argument_end + 1)
                if index < len(text) and text[index] == "{":
                    end = find_matching_brace(text, index)
                    if end is not None:
                        _mask_range(chars, index + 1, end)
    return "".join(chars)


class WordScanner:
    def __init__(
        self,
        ignore_envs: set[str],
        skip_commands: set[str],
        keep_commands: set[str],
        skip_two_args: set[str] | None = None,
        second_arg_commands: set[str] | None = None,
    ) -> None:
        self.ignore_envs = ignore_envs
        self.skip_commands = skip_commands
        self.keep_commands = keep_commands
        self.skip_two_args = skip_two_args or set()
        self.second_arg_commands = second_arg_commands or set()

    def iter_words(self, text: str, start: int = 0, end: int | None = None):
        if end is None:
            end = len(text)
        yield from self._scan_range(text, start, end)

    def _scan_range(self, text: str, start: int, end: int):
        index = start
        while index < end:
            char = text[index]
            if char == "%" and not is_escaped(text, index):
                index = _scan_skip_comment(text, index)
                continue
            if _scan_is_math_start(text, index):
                index = _scan_skip_math(text, index)
                continue
            if text.startswith("\\begin", index):
                next_index = self._handle_begin(text, index)
                if next_index != index:
                    index = next_index
                    continue
            if char == "\\":
                cmd, next_index = _scan_parse_command(text, index)
                index = next_index
                if not cmd:
                    continue
                if cmd in {"begin", "end"}:
                    index = _scan_skip_command_args(text, index, cmd, self.skip_two_args)
                    continue
                if cmd in self.skip_commands and cmd not in self.keep_commands:
                    index = _scan_skip_command_args(text, index, cmd, self.skip_two_args)
                    continue
                if cmd in self.second_arg_commands:
                    index = _scan_skip_optional(text, index)
                    index = _scan_skip_first_braced(text, index)
                    if index < end and text[index] == "{":
                        arg_end = find_matching_brace(text, index)
                        if arg_end is None:
                            index += 1
                            continue
                        yield from self._scan_range(text, index + 1, arg_end)
                        index = arg_end + 1
                    continue
                index = _scan_skip_optional(text, index)
                if index < end and text[index] == "{":
                    arg_end = find_matching_brace(text, index)
                    if arg_end is None:
                        index += 1
                        continue
                    yield from self._scan_range(text, index + 1, arg_end)
                    index = arg_end + 1
                continue

            next_special = _scan_next_special(text, index, end)
            segment = text[index:next_special]
            for match in WORD_RE.finditer(segment):
                yield match.group(0), index + match.start()
            index = next_special

    def _handle_begin(self, text: str, index: int) -> int:
        cmd, next_index = _scan_parse_command(text, index)
        if cmd != "begin":
            return index
        next_index = _scan_skip_optional(text, next_index)
        if next_index >= len(text) or text[next_index] != "{":
            return next_index
        env_end = find_matching_brace(text, next_index)
        if env_end is None:
            return next_index + 1
        env_name = text[next_index + 1 : env_end].strip()
        if env_name in self.ignore_envs:
            return _scan_skip_environment(text, env_name, env_end + 1)
        return env_end + 1


def _scan_parse_command(text: str, index: int) -> tuple[str, int]:
    if index >= len(text) or text[index] != "\\":
        return "", index
    index += 1
    if index >= len(text):
        return "", index
    if text[index].isalpha():
        start = index
        while index < len(text) and text[index].isalpha():
            index += 1
        return text[start:index], index
    return text[index], index + 1


def _scan_skip_optional(text: str, index: int) -> int:
    index = _skip_whitespace(text, index)
    if index < len(text) and text[index] == "[":
        end = find_matching_bracket(text, index)
        if end is None:
            return index
        return end + 1
    return index


def _scan_skip_command_args(text: str, index: int, command: str, skip_two_args: set[str]) -> int:
    index = _scan_skip_optional(text, index)
    args_to_skip = 2 if command in skip_two_args else 1
    for _ in range(args_to_skip):
        index = _skip_whitespace(text, index)
        if index < len(text) and text[index] == "{":
            end = find_matching_brace(text, index)
            if end is None:
                return index + 1
            index = end + 1
        else:
            break
    return index


def _scan_skip_environment(text: str, env_name: str, index: int) -> int:
    pattern = re.compile(r"\\(begin|end)\s*\{" + re.escape(env_name) + r"\}")
    depth = 1
    for match in pattern.finditer(text, index):
        if match.group(1) == "begin":
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return match.end()
    return len(text)


def _scan_skip_comment(text: str, index: int) -> int:
    while index < len(text) and text[index] != "\n":
        index += 1
    return index


def _scan_is_math_start(text: str, index: int) -> bool:
    if text[index] == "$" and not is_escaped(text, index):
        return True
    return text.startswith("\\(", index) or text.startswith("\\[", index)


def _scan_skip_math(text: str, index: int) -> int:
    if text[index] == "$" and not is_escaped(text, index):
        if index + 1 < len(text) and text[index + 1] == "$":
            end = _find_next(text, "$$", index + 2)
            return end + 2 if end is not None else len(text)
        end = _find_next(text, "$", index + 1)
        return end + 1 if end is not None else len(text)
    if text.startswith("\\(", index):
        end = text.find("\\)", index + 2)
        return end + 2 if end != -1 else len(text)
    if text.startswith("\\[", index):
        end = text.find("\\]", index + 2)
        return end + 2 if end != -1 else len(text)
    return index + 1


def _scan_skip_first_braced(text: str, index: int) -> int:
    index = _skip_whitespace(text, index)
    if index < len(text) and text[index] == "{":
        end = find_matching_brace(text, index)
        if end is None:
            return index + 1
        return end + 1
    return index


def _scan_next_special(text: str, index: int, end: int) -> int:
    while index < end:
        if text[index] in {"\\", "%", "$"}:
            return index
        index += 1
    return end
