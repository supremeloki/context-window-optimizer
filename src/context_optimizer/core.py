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
