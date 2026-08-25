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
        return round(1.0 - self.optimized_tokens / self.original_tokens, 4)


class Compressor:
    def __init__(self,
                 filler_patterns: Sequence[str] = (
                     r"^(um|uh|well|so|basically|actually)[,\s]+",
                     r"\b(please note that|it should be noted that|as you know)\b",
                 ),
                 collapse_whitespace: bool = True) -> None:
        self._patterns = [re.compile(p, re.IGNORECASE) for p in filler_patterns]
        self._collapse = collapse_whitespace

    def compress(self, text: str) -> str:
        result = text
        for pattern in self._patterns:
            result = pattern.sub("", result)
        if self._collapse:
            result = re.sub(r"[ \t]{2,}", " ", result)
            result = re.sub(r"\n{3,}", "\n\n", result).strip()
        return result

    @property
    def is_lossless_heuristic(self) -> bool:
        return True


class ContextWindowOptimizer:
    def __init__(self, token_budget: int,
                 compressor: Compressor | None = None,
                 hard_fail_on_overflow: bool = False) -> None:
        if token_budget < 1:
            raise ContextOptimizerError("token budget must be >= 1")
        self._budget = token_budget
        self._compressor = compressor or Compressor()
        self._hard_fail = hard_fail_on_overflow

    @property
    def budget(self) -> int:
        return self._budget

    def optimize(self, blocks: Sequence[ContextBlock]) -> tuple[list[ContextBlock], OptimizationReport]:
        original_tokens = sum(block.tokens for block in blocks)
        dropped: list[str] = []
        compressed_ids: list[str] = []
        working: list[ContextBlock] = []

        ordered = sorted(blocks, key=lambda b: (b.block_id not in {x.block_id for x in blocks}, b.priority), reverse=True)
        pinned_blocks = [b for b in blocks if b.pinned]
        ranked_rest = sorted(
            [b for b in blocks if not b.pinned],
            key=lambda b: (-b.priority, -b.tokens),
        )

        budget_used = 0
        for block in pinned_blocks + ranked_rest:
            candidate_tokens = block.tokens
            if budget_used + candidate_tokens <= self._budget:
                working.append(block)
                budget_used += candidate_tokens
                continue
            squeezed_content = self._compressor.compress(block.content)
            squeezed = ContextBlock(
                block_id=block.block_id,
                content=squeezed_content,
                priority=block.priority,
                pinned=block.pinned,
            )
            if squeezed.tokens < block.tokens and budget_used + squeezed.tokens <= self._budget:
                working.append(squeezed)
                budget_used += squeezed.tokens
                compressed_ids.append(block.block_id)
            else:
                dropped.append(block.block_id)

        kept_order = [b.block_id for b in blocks]
        working.sort(key=lambda b: kept_order.index(b.block_id))
        report = OptimizationReport(
            original_tokens=original_tokens,
            optimized_tokens=budget_used,
            dropped_block_ids=tuple(dropped),
            compressed_block_ids=tuple(compressed_ids),
        )
        if self._hard_fail and dropped:
            raise BudgetExceededError(
                f"blocks exceeded budget {self._budget}: dropped {dropped}"
            )
        return working, report

    def fits(self, blocks: Sequence[ContextBlock]) -> bool:
        return sum(b.tokens for b in blocks) <= self._budget

    def render_prompt(self, blocks: Sequence[ContextBlock]) -> str:
        optimized, _report = self.optimize(blocks)
        return "\n\n".join(block.content for block in optimized)


class RollingContextBuffer:
    def __init__(self, optimizer: ContextWindowOptimizer) -> None:
        self._optimizer = optimizer
        self._blocks: list[ContextBlock] = []

    def append(self, block: ContextBlock) -> None:
        self._blocks.append(block)
        if not self._optimizer.fits(self._blocks):
            self._blocks, _report = self._optimizer.optimize(self._blocks)

    @property
    def blocks(self) -> tuple[ContextBlock, ...]:
        return tuple(self._blocks)

    @property
    def total_tokens(self) -> int:
        return sum(block.tokens for block in self._blocks)
