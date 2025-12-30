from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Sequence


class ContextOptimizerError(Exception):
    pass


class BudgetExceededError(ContextOptimizerError):
    pass


TOKEN_ESTIMATE_PATTERN: re.Pattern[str] = re.compile(r"\S+")


class Priority(IntEnum):
    CRITICAL = 100
    HIGH = 75
    NORMAL = 50
    LOW = 25
    FILLER = 10


@dataclass(frozen=True)
class ContextBlock:
    block_id: str
    content: str
    priority: Priority
    pinned: bool = False

    @property
    def tokens(self) -> int:
        return estimate_tokens(self.content)


def estimate_tokens(text: str) -> int:
    return len(TOKEN_ESTIMATE_PATTERN.findall(text))


@dataclass(frozen=True)
class OptimizationReport:
    original_tokens: int
    optimized_tokens: int
    dropped_block_ids: tuple[str, ...]
    compressed_block_ids: tuple[str, ...]

    @property
    def saved_tokens(self) -> int:
        return self.original_tokens - self.optimized_tokens

    @property
    def savings_ratio(self) -> float:
        if self.original_tokens == 0:
            return 0.0
