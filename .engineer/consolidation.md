# Kando — Consolidation Backlog

**Goal:** every row all-✅. A feature is fully ATDD-covered when its
`features/NNN-slug/` folder has `feature.md`, `acs.md`, `spec.md`
(+ `.build/spec.json` IR), and generated acceptance tests that pass.

Tracker: [Linear](https://linear.app/ucalyptus/project/kando-f02dfdc278fb/overview)
(DAE Linear driver not yet implemented — feature folders are canonical DAE state.)

---

## Coverage table

| # | Feature | status | Linear | code location | feature.md | acs.md | spec.md | acc. tests |
|---|---------|--------|--------|---------------|:---:|:---:|:---:|:---:|
| 001 | world | shipped | [SAY-5](https://linear.app/ucalyptus/issue/SAY-5) | `kando/world/` | ✅ | ❌ | ❌ | ❌ |
| 002 | ledger | shipped | [SAY-6](https://linear.app/ucalyptus/issue/SAY-6) | `kando/ledger/` | ❌ | ❌ | ❌ | ❌ |
| 003 | runtime | shipped | [SAY-7](https://linear.app/ucalyptus/issue/SAY-7) | `kando/runtime.py` | ✅ | ❌ | ❌ | ❌ |
| 004 | research-kit | shipped | [SAY-8](https://linear.app/ucalyptus/issue/SAY-8) | `kits/research/` | ❌ | ❌ | ❌ | ❌ |
| 005 | llm-executor | shipped | [SAY-9](https://linear.app/ucalyptus/issue/SAY-9) | `kando/responders/llm_executor.py` + backends | ❌ | ❌ | ❌ | ❌ |
| 006 | diligence-kit | shipped | [SAY-10](https://linear.app/ucalyptus/issue/SAY-10) | `kits/diligence/` | ❌ | ❌ | ❌ | ❌ |
| 007 | branch | shipped | [SAY-11](https://linear.app/ucalyptus/issue/SAY-11) | `kando/branch/` | ❌ | ❌ | ❌ | ❌ |
| 008 | cache | shipped | [SAY-12](https://linear.app/ucalyptus/issue/SAY-12) | `kando/cache/` | ❌ | ❌ | ❌ | ❌ |
| 009 | trace | shipped | [SAY-13](https://linear.app/ucalyptus/issue/SAY-13) | `kando/trace/` | ❌ | ❌ | ❌ | ❌ |
| 010 | budget-enforcer | shipped | [SAY-14](https://linear.app/ucalyptus/issue/SAY-14) | `kando/responders/budget.py` | ❌ | ❌ | ❌ | ❌ |
| 011 | cli | shipped | [SAY-15](https://linear.app/ucalyptus/issue/SAY-15) | `kando/cli/main.py` | ❌ | ❌ | ❌ | ❌ |
| 012 | mcp-server | shipped | [SAY-16](https://linear.app/ucalyptus/issue/SAY-16) | `kando/mcp/server.py` | ❌ | ❌ | ❌ | ❌ |
| 013 | delivery-bus | shipped | [SAY-17](https://linear.app/ucalyptus/issue/SAY-17) | `kando/responders/delivery.py` | ❌ | ❌ | ❌ | ❌ |

**Note:** `features/*.feature` and `features/steps/` exist as BDD infrastructure
but are flat (not DAE-layout). They serve as raw material for reverse-engineering
ACS + spec.md during consolidation — do not delete them.

---

## Consolidation tasks (priority order)

Each task: `/engineer.prime-context` → `/engineer.discover-acs` (reverse-engineer
mode) → write `spec.md` → `/atdd.atdd` → pipeline generation.
All tasks are bounded and dispatchable to a remote agent.

### TASK-001 — Bring `world` to full ATDD coverage
- **Inputs:** `kando/world/` (graph.py, projection.py, snapshot.py),
  `tests/test_snapshot.py`, `features/world.feature`, `features/steps/world_steps.py`
- **Execution:** remote-agent dispatch recommended
- **Acceptance:** `features/001-world/` all-✅

### TASK-002 — Bring `ledger` to full ATDD coverage
- **Inputs:** `kando/ledger/` (interface.py, memory.py, stream.py),
  `tests/test_ledger.py`, `features/ledger.feature`, `features/steps/ledger_steps.py`
- **Execution:** remote-agent dispatch recommended
- **Acceptance:** `features/002-ledger/` all-✅

### TASK-003 — Bring `runtime` to full ATDD coverage
- **Inputs:** `kando/runtime.py`, `tests/test_runtime.py`,
  `features/runtime.feature`, `features/steps/runtime_steps.py`
- **Execution:** remote-agent dispatch recommended
- **Acceptance:** `features/003-runtime/` all-✅

### TASK-004 — Bring `research-kit` to full ATDD coverage
- **Inputs:** `kits/research/kit.py`, `tests/test_research_kit.py`
- **Execution:** remote-agent dispatch recommended
- **Acceptance:** `features/004-research-kit/` all-✅

### TASK-005 — Bring `llm-executor` to full ATDD coverage
- **Inputs:** `kando/responders/llm_executor.py`, `kando/responders/openrouter_llm.py`,
  `kando/responders/anthropic_llm.py`; no existing tests
- **Execution:** remote-agent dispatch recommended (needs mock LLM fn)
- **Acceptance:** `features/005-llm-executor/` all-✅

### TASK-006 — Bring `diligence-kit` to full ATDD coverage
- **Inputs:** `kits/diligence/kit.py`, `tests/test_diligence_kit.py`
- **Execution:** remote-agent dispatch recommended
- **Acceptance:** `features/006-diligence-kit/` all-✅

### TASK-007 — Bring `branch` to full ATDD coverage
- **Inputs:** `kando/branch/` (diff.py, fork.py, replay.py), `tests/test_branch.py`,
  `features/branch.feature`, `features/steps/branch_steps.py`
- **Execution:** remote-agent dispatch recommended
- **Acceptance:** `features/007-branch/` all-✅

### TASK-008 — Bring `cache` to full ATDD coverage
- **Inputs:** `kando/cache/llm.py`, `tests/test_cache.py`,
  `features/cache.feature`, `features/steps/cache_steps.py`
- **Execution:** remote-agent dispatch recommended
- **Acceptance:** `features/008-cache/` all-✅

### TASK-009 — Bring `trace` to full ATDD coverage
- **Inputs:** `kando/trace/lineage.py`, `tests/test_trace.py`,
  `features/trace.feature`, `features/steps/trace_steps.py`
- **Execution:** remote-agent dispatch recommended
- **Acceptance:** `features/009-trace/` all-✅

### TASK-010 — Bring `budget-enforcer` to full ATDD coverage
- **Inputs:** `kando/responders/budget.py`, `tests/test_budget_full.py`
- **Execution:** remote-agent dispatch recommended
- **Acceptance:** `features/010-budget-enforcer/` all-✅

### TASK-011 — Bring `cli` to full ATDD coverage
- **Inputs:** `kando/cli/main.py`; no existing tests
- **Execution:** remote-agent dispatch recommended (CLI integration tests)
- **Acceptance:** `features/011-cli/` all-✅

### TASK-012 — Bring `mcp-server` to full ATDD coverage
- **Inputs:** `kando/mcp/server.py`, `tests/test_mcp_dispatch.py`
- **Execution:** remote-agent dispatch recommended
- **Acceptance:** `features/012-mcp-server/` all-✅

### TASK-013 — Bring `delivery-bus` to full ATDD coverage
- **Inputs:** `kando/responders/delivery.py`, `tests/test_delivery.py`
- **Execution:** remote-agent dispatch recommended
- **Acceptance:** `features/013-delivery-bus/` all-✅
