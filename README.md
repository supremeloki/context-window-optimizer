# context-optimizer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Context-window budget management for LLM apps: priority-ranked block selection, pinned blocks that always survive, heuristic compression for borderline content, and a rolling buffer that never exceeds the budget.

## 🚀 Overview

When the prompt doesn't fit, something must go — but *what* goes decides whether your app works. `context-optimizer` treats context as typed blocks with priorities (`CRITICAL` → `FILLER`): it packs highest-priority content first, compresses borderline blocks by stripping filler phrases ("basically", "please note that") before dropping them, keeps **pinned** blocks unconditionally, and preserves original ordering in the output. A rolling buffer variant auto-trims as new messages arrive.

## ✨ Features

- **Priority packing:** CRITICAL/HIGH/NORMAL/LOW/FILLER — low value drops first
- **Pinned blocks:** system prompts and instructions survive any squeeze
- **Compression pass:** filler-phrase + whitespace reduction applied before eviction; only compressed if it actually helps
- **Order preservation:** optimized output stays in the author's original sequence
- **RollingContextBuffer:** append-only stream that self-trims under budget
- **OptimizationReport:** original vs optimized tokens, dropped IDs, compressed IDs, savings ratio
- **Hard-fail mode:** optional strict mode raising instead of silently dropping
- **Zero dependencies**

## 🚧 Structure

```
context-window-optimizer/
├── src/context_optimizer/
│   ├── __init__.py
│   └── core.py
├── tests/
│   └── test_core.py
├── README.md
└── pyproject.toml
```

## 📦 Installation

```bash
git clone https://github.com/supremeloki/context-window-optimizer.git
cd context-window-optimizer
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## 📋 Requirements

- Python 3.11+
- No runtime dependencies

## 🏃 Quick Start

```python
from context_optimizer import (
    ContextBlock, ContextWindowOptimizer,
    Priority, RollingContextBuffer,
)

optimizer = ContextWindowOptimizer(token_budget=4096)
blocks = [
    ContextBlock("system", "You are helpful.", Priority.CRITICAL, pinned=True),
    ContextBlock("history", "long chat transcript...", Priority.LOW),
    ContextBlock("question", "What is BM25?", Priority.HIGH),
]

optimized, report = optimizer.optimize(blocks)
print(report.savings_ratio, report.dropped_block_ids)

rolling = RollingContextBuffer(optimizer)
rolling.append(ContextBlock("m1", "user message", Priority.NORMAL))
```

## 🔧 Error Handling

```text
ContextOptimizerError   # invalid token budget
BudgetExceededError     # hard-fail mode: content couldn't fit even after drops
```

## 🧪 Testing

```bash
pytest tests/ -v
```

## 📝 Code Quality

- Full type hints (`X | None` style), frozen blocks/reports
- Zero comments — names carry the meaning
- Order preservation and budget ceilings asserted in tests

## 📄 License

MIT — see [LICENSE](LICENSE).

## 👤 Author

**Kooroush Masoumi** - [kooroushmasoumi@gmail.com](mailto:kooroushmasoumi@gmail.com)

---

⭐ Star this repo if you find it useful!
