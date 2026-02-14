import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from context_optimizer import (
    BudgetExceededError,
    Compressor,
    ContextBlock,
    ContextOptimizerError,
    ContextWindowOptimizer,
    Priority,
    RollingContextBuffer,
    estimate_tokens,
)


def block(block_id: str, words: int, priority: Priority = Priority.NORMAL,
          pinned: bool = False) -> ContextBlock:
    return ContextBlock(
        block_id=block_id,
        content=" ".join(f"w{i}" for i in range(words)),
        priority=priority,
        pinned=pinned,
    )


def test_estimate_tokens_counts_words():
    assert estimate_tokens("hello world foo") == 3


def test_invalid_budget_rejected():
    with pytest.raises(ContextOptimizerError):
        ContextWindowOptimizer(token_budget=0)


def test_everything_fits_no_changes():
    optimizer = ContextWindowOptimizer(token_budget=100)
    blocks = [block("a", 10), block("b", 20)]
    optimized, report = optimizer.optimize(blocks)
    assert [b.block_id for b in optimized] == ["a", "b"]
    assert report.dropped_block_ids == ()
    assert report.compressed_block_ids == ()


def test_low_priority_dropped_first():
    optimizer = ContextWindowOptimizer(token_budget=30)
    blocks = [
        block("critical", 15, Priority.CRITICAL),
        block("low", 15, Priority.LOW),
        block("normal", 15, Priority.NORMAL),
    ]
    optimized, report = optimizer.optimize(blocks)
    kept_ids = {b.block_id for b in optimized}
    assert "critical" in kept_ids
    assert "low" not in kept_ids or "normal" not in kept_ids
    assert report.optimized_tokens <= 30


def test_pinned_blocks_survive():
    optimizer = ContextWindowOptimizer(token_budget=25)
    blocks = [
        block("pinned-system", 12, Priority.LOW, pinned=True),
        block("big", 20, Priority.CRITICAL),
    ]
    optimized, _report = optimizer.optimize(blocks)
    assert any(b.block_id == "pinned-system" for b in optimized)


def test_compression_applied_when_needed():
    optimizer = ContextWindowOptimizer(token_budget=18)
    filler = ContextBlock(
        block_id="chatty",
        content="Well basically the answer is forty-two",
        priority=Priority.HIGH,
    )
    essential = block("essential", 8, Priority.CRITICAL)
    optimized, report = optimizer.optimize([filler, essential])
    assert "chatty" in report.compressed_block_ids or "chatty" in {
        b.block_id for b in optimized
    }
    total = sum(b.tokens for b in optimized)
    assert total <= 18


def test_report_savings_ratio():
    optimizer = ContextWindowOptimizer(token_budget=30)
    _, report = optimizer.optimize([
        block("x", 25, Priority.HIGH),
        block("y", 20, Priority.LOW),
    ])
    assert report.saved_tokens > 0
    assert 0.0 < report.savings_ratio < 1.0


def test_original_order_preserved():
    optimizer = ContextWindowOptimizer(token_budget=60)
    blocks = [block("c", 5), block("a", 5), block("b", 5)]
    optimized, _report = optimizer.optimize(blocks)
    assert [b.block_id for b in optimized] == ["c", "a", "b"]


def test_fits_check():
    optimizer = ContextWindowOptimizer(token_budget=10)
    assert optimizer.fits([block("a", 9)])
    assert not optimizer.fits([block("a", 11)])


def test_render_prompt_joins_content():
    optimizer = ContextWindowOptimizer(token_budget=100)
    prompt = optimizer.render_prompt([
        ContextBlock("sys", "system rules here", Priority.CRITICAL),
        ContextBlock("user", "user question", Priority.HIGH),
    ])
    assert "system rules here" in prompt
    assert "user question" in prompt


def test_rolling_buffer_stays_under_budget():
    optimizer = ContextWindowOptimizer(token_budget=40)
    rolling = RollingContextBuffer(optimizer)
    for index in range(6):
        rolling.append(block(f"m{index}", 15))
    assert rolling.total_tokens <= 40
