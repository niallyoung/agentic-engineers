---
name: task-orchestration
description: >
  Encodes the autonomous task execution framework principle: maximize throughput by
  parallelizing all independent tasks, and pause only for genuine decisions (not
  task sequencing). Provides task classification, parallelization analysis, and
  decision shorthand helpers for all agentic-engineers agents.
license: Proprietary
compatibility: agentic-engineers framework v5.10+. Requires Python 3.7+
metadata:
  author: agentic-engineers
  version: "1.0.0"
  category: framework
  role: orchestrator
  trigger: on-demand | planning | task-routing
  tdd_phase: GREEN  # All 64 tests passing
---

# task-orchestration

## Overview

`task-orchestration` is a **framework-level meta-skill** that encodes the canonical
autonomous task execution principle used across every agent in the agentic-engineers
platform:

> **Maximize throughput by parallelizing all independent tasks.**  
> **Pause only for genuine decisions — never for task sequencing.**

It provides:

1. **Task classification** — distinguish work the agent should execute autonomously
   from work that needs a genuine user decision.
2. **Parallelization analysis** — determine whether a set of tasks is safe to
   dispatch concurrently (dependency and git-safety checks).
3. **Decision shorthand generation** — format multi-option choices for fast user
   responses (`1a`, `2c`, `3b`).
4. **Decision response parsing** — convert a shorthand response back to a
   structured dict for downstream routing.

---

## The Core Principle

### Decision Points vs. Task Sequencing

These two categories look similar but demand **opposite** agent behaviour:

| Category | Definition | Agent behaviour |
|----------|-----------|-----------------|
| **Task sequencing** | Questions about *ordering*, *which to do first*, or *what sequence to follow* among independent items. | **Always autonomous** — the agent decides, never asks. |
| **Genuine decision** | An *irreversible* or *design-level* choice where the correct answer depends on context only the user knows (technology selection, breaking-change approval, architectural trade-offs). | **Always pause** — present shorthand and wait for user input. |

**Why the distinction matters:**  
Asking the user "which task should I start first?" wastes a round-trip, adds
latency, and teaches the user not to trust the agent's autonomy.  
Asking "should we use Redis or in-memory caching?" respects the user's authority
over architectural choices.

---

## Decision Shorthand Format

When a genuine decision must be presented, use compact shorthand so the user can
respond in a single token:

```
1a. Use Redis
1b. Use in-memory cache
1c. Use Memcached

2a. Deprecate the role for 2 releases
2b. Remove it immediately
2c. Rename and repurpose it
```

The user responds: `1b, 2a`

Rules:
- Questions are numbered starting at **1**: `1(a-z)`, `2(a-z)`, …
- Each option gets the next letter in the alphabet: `a`, `b`, `c`, …
- Multiple decisions can be batched in one message; user responds with all
  choices separated by spaces or commas: `1a, 2c, 3b`
- Parse responses with `task_orchestration.parse_decision_response()`

---

## Examples

### ❌ Never Ask (Task Sequencing)

These are sequencing questions — the agent resolves them autonomously:

| Question | Why it's sequencing |
|----------|-------------------|
| "Should I start task A or task B?" | Both are independent → parallelize |
| "Which order should I implement these features?" | Implementation order is the agent's call |
| "Which task should I tackle first?" | No external context needed |
| "Should I start with the tests or the implementation?" | Standard TDD order — agent knows |

### ✅ Always Ask (Genuine Decisions)

These require user input because the answer is context-dependent:

| Question | Shorthand format |
|----------|-----------------|
| "Should we use Redis or in-memory caching?" | `1a. Redis  /  1b. In-memory  /  1c. Memcached` |
| "Should we remove this feature or deprecate it?" | `1a. Remove immediately  /  1b. Deprecate (2 releases)` |
| "Should we use render A or render B?" | `1a. Render A  /  1b. Render B` |
| "This will break the public API — should we proceed?" | `1a. Proceed with break  /  1b. Add compat shim  /  1c. Defer` |
| "Should we use OAuth or API keys?" | `1a. OAuth  /  1b. API keys  /  1c. Both` |
| "Monolith or microservices?" | `1a. Monolith  /  1b. Microservices  /  1c. Modular monolith` |

---

## Python API

```python
from src.skills._meta.task_orchestration.scripts.task_orchestrator import (
    Task, TaskType,
    classify_task,
    can_parallelize,
    generate_decision_shorthand,
    parse_decision_response,
)

# ── Classify a task ──────────────────────────────────────────────────────────
classify_task("Implement the login endpoint")
# → TaskType.AUTONOMOUS

classify_task("Should we use Redis or in-memory caching?")
# → TaskType.DECISION_NEEDED

classify_task("Run database migrations, then run tests")
# → TaskType.SEQUENTIAL_ONLY

# ── Check if tasks can be parallelized ──────────────────────────────────────
tasks = [
    Task(id="tests-auth",    description="Write auth tests",     dependencies=[]),
    Task(id="tests-billing", description="Write billing tests",  dependencies=[]),
    Task(id="update-docs",   description="Update README",        dependencies=[]),
]
can_parallelize(tasks)   # → True  (no deps, no file conflicts)

conflicting = [
    Task(id="feat-a", description="Feature A", dependencies=[], touches_files=["src/auth.py"]),
    Task(id="feat-b", description="Feature B", dependencies=[], touches_files=["src/auth.py"]),
]
can_parallelize(conflicting)   # → False  (same file → git conflict)

# ── Generate decision shorthand ──────────────────────────────────────────────
print(generate_decision_shorthand(["Use Redis", "Use in-memory", "Use Memcached"]))
# 1a. Use Redis
# 1b. Use in-memory
# 1c. Use Memcached

# Multiple questions in one message:
q1 = generate_decision_shorthand(["Redis", "In-memory"], question_number=1)
q2 = generate_decision_shorthand(["Remove immediately", "Deprecate"], question_number=2)
print(q1 + "\n\n" + q2)

# ── Parse decision response ──────────────────────────────────────────────────
parse_decision_response("1b")               # → {1: 'b'}
parse_decision_response("1a, 2c, 3b")       # → {1: 'a', 2: 'c', 3: 'b'}
parse_decision_response("1a2b3c")           # → {1: 'a', 2: 'b', 3: 'c'}
```

---

## Agent Integration Guide

All agents should apply this skill during planning:

```
STEP 1 — Build your task list
  Enumerate every concrete sub-task from the work item.

STEP 2 — Classify each task
  for task in tasks:
      task_type = classify_task(task.description)

STEP 3 — Identify dependencies and file conflicts
  parallelizable = can_parallelize(tasks)

STEP 4 — Collect genuine decisions
  decisions = [t for t in tasks if task_type(t) == DECISION_NEEDED]
  if decisions:
      present_all_decisions_in_one_message_using_shorthand()
      wait_for_user_response()
      answers = parse_decision_response(user_input)

STEP 5 — Execute
  if parallelizable:
      dispatch_all_tasks_simultaneously()
  else:
      execute_in_dependency_order()
```

**Key rules:**
- Never create a separate message to ask "which task first?" — that's a sequencing
  question. Always decide autonomously.
- Batch all decision shorthand into a **single** message to minimize round-trips.
- Sequential-only tasks (build→test, migrate→seed) run in order; no user input needed.

---

## Architecture

```
src/skills/_meta/task-orchestration/
├── SKILL.md                                   # This file
├── scripts/
│   └── task_orchestrator.py                   # Core implementation
│       ├── TaskType (Enum)                    — AUTONOMOUS | DECISION_NEEDED | SEQUENTIAL_ONLY
│       ├── Task (dataclass)                   — id, description, dependencies, touches_files
│       ├── classify_task(description) → TaskType
│       ├── can_parallelize(tasks) → bool
│       ├── generate_decision_shorthand(options, question_number) → str
│       └── parse_decision_response(shorthand) → Dict[int, str]
└── tests/
    └── test_task_orchestration.py             # 64 tests (TDD GREEN)
        ├── TestTaskTypeEnum                   (4)  — enum values exist and are distinct
        ├── TestTaskDataclass                  (4)  — Task fields, defaults, dependencies
        ├── TestClassifyTaskAutonomous         (9)  — implementation, refactor, sequencing
        ├── TestClassifyTaskDecisionNeeded     (6)  — tech choice, arch, breaking change
        ├── TestClassifyTaskSequentialOnly     (2)  — migrate→test, build→deploy
        ├── TestCanParallelize                 (8)  — deps, file conflicts, empty list
        ├── TestGenerateDecisionShorthand      (8)  — format, letter ranges, ValueError
        ├── TestParseDecisionResponse         (11)  — single, multi, no-sep, ValueError
        └── TestFrameworkPrinciple            (12)  — 6 sequencing NEVER asked, 6 decisions ARE asked
```

---

## Test Coverage

```
64 tests — 9 test classes:

TestTaskTypeEnum                (4)  Enum values exist and are mutually distinct
TestTaskDataclass               (4)  Task fields, touches_files default, dependency list
TestClassifyTaskAutonomous      (9)  Implementation work, refactor, fix, docs, linting,
                                     plus 3 critical sequencing-is-autonomous cases
TestClassifyTaskDecisionNeeded  (6)  Technology choice, architecture, remove/deprecate,
                                     breaking change, security trade-off, render A vs B
TestClassifyTaskSequentialOnly  (2)  migrate→test, build→deploy pipelines
TestCanParallelize              (8)  Independent tasks, explicit deps, git file conflicts,
                                     single task, empty list, mixed list, no-file-overlap
TestGenerateDecisionShorthand   (8)  Two options, three options, single option, text in output,
                                     custom question_number, empty raises ValueError, compact lines
TestParseDecisionResponse      (11)  Single, multi, spaces, no-sep, mixed whitespace,
                                     invalid raises ValueError, empty raises ValueError,
                                     returns dict, multi-digit question number,
                                     keys are int, values are lowercase alpha
TestFrameworkPrinciple         (12)  6 × parametrized sequencing → AUTONOMOUS (PROHIBITED to ask)
                                     6 × parametrized genuine decisions → DECISION_NEEDED (REQUIRED to ask)
```

---

## Supported Sequential Dependency Patterns

The classifier recognises common explicit dependency chains:

| Pattern | Example |
|---------|---------|
| Build → deploy/test | "Build the project, then deploy" |
| Migrations → tests/seed | "Run database migrations, then run tests" |
| Multi-step pipelines | "do X, then Y, then Z" |

Everything else defaults to `AUTONOMOUS` — if in doubt, proceed autonomously.

---

## Parallelization Safety Checks

`can_parallelize()` performs two checks:

1. **Explicit dependencies** — if any task in the list has a `dependency` on
   another task in the list, parallelization is unsafe.
2. **File conflict detection** — if two or more tasks declare overlapping paths
   in `touches_files`, they would produce git conflicts if run concurrently.

If either check fails, the function returns `False` and the caller should run
tasks in dependency order.

---

## Constraints

- Does **not** modify or create tasks — classification only.
- Does **not** execute tasks — delegates that to the calling agent.
- Does **not** require network access.
- Does **not** require external NLP/ML models — uses rule-based regex patterns.
- Python 3.7+ compatible; no third-party dependencies.

## SPAN Capture

After planning with this skill, capture a SPAN with:
- `tasks_classified`: total tasks classified
- `autonomous_count`: tasks resolved as AUTONOMOUS
- `decision_needed_count`: tasks requiring user input
- `sequential_only_count`: tasks with explicit ordering dependencies
- `parallelizable`: boolean result of can_parallelize()
- `decisions_presented`: count of shorthand decision questions sent to user
