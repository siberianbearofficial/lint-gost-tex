from __future__ import annotations

from typing import Protocol

from ..context import LintContext
from ..issue import Issue


class Rule(Protocol):
    rule_id: str
    description: str

    def check(self, ctx: LintContext) -> list[Issue]:
        ...
