# Agentic Engineers

A production-ready multi-agent orchestration framework with 8 specialized AI roles, queue-based delegation, quality gates, and autonomous cost optimization feedback loops.

**Status:** ✅ **PRODUCTION READY** — Phases 1–6 complete, 1047+ tests passing, end-to-end queue protocol verified.

---

## What It Is

**Agentic Engineers** solves the multi-agent coordination problem:

- **How do you coordinate 8+ specialized AI agents** without spaghetti code?
- **How do you enforce quality gates** consistently across all agents?
- **How do you optimize cost** while maintaining quality?
- **How do you stay within token budgets** across unlimited work?

**The answer:** A queue-based ORCHESTRATOR-FIRST architecture:

1. All work enters a queue as DELEGATE tasks (SPEC-compliant YAML)
2. Orchestrator polls continuously and routes to the right specialist
3. Each agent returns a HANDBACK with results + metrics
4. Quality gates validate all work before moving to done
5. Metrics feed back into model selection and routing optimization

---

## 8 Specialized Roles

| Role | Model | Purpose |
|------|-------|---------|
| **Orchestrator** | Haiku | Routes all work via decision tree; never does work itself |
| **Engineer** | Haiku | Executes well-scoped, pre-planned tasks |
| **Senior Engineer** | Sonnet | Analyzes unscoped work; produces detailed plans |
| **Lead Engineer** | Sonnet | Code review (8-point checklist); architectural guidance |
| **Quality Engineer** | Sonnet | Post-implementation validation; model suitability assessment |
| **Security Engineer** | Opus | Threat modeling; vulnerability assessment |
| **Principal Engineer** | Opus | Cross-service architecture; major refactors |
| **Model Engineer** | Sonnet | Analyzes metrics; optimizes routing and model selection |

---

## Architecture

```
User Task
   ↓
[artifacts/queue/incoming/] ← DELEGATE
   ↓
[Orchestrator Agent]
   ├─ Routes via AGENTS.md decision tree
   ├─ Spawns appropriate specialist
   └─ Waits for HANDBACK
   ↓
[Specialist Agent]
   ├─ Executes task
   ├─ Measures quality + metrics
   └─ Returns HANDBACK
   ↓
[Quality Gates validate]
   └─ quality_score ≥ threshold → done/
      else → REWORK or ESCALATE
   ↓
[artifacts/queue/done/] ← Results + Metrics
```

### Queue States

```
incoming/      ← New DELEGATE tasks
  ↓ (Orchestrator picks up)
processing/    ← Tasks being worked on
  ↓ (agent completes)
done/          ← Completed tasks with full audit trail
```

---

## Quick Start

### Installation

```bash
git clone https://github.com/niallyoung/agentic-engineers.git
cd agentic-engineers

make install-opencode    # OpenCode → ~/.config/opencode/ (recommended)
make install-claude      # Claude Code → ~/.claude/
make install-copilot     # Copilot CLI → ~/.copilot/skills/
make install             # All harnesses
```

### Create a Task

```bash
cat > artifacts/queue/incoming/2026-05-17-my-task.yaml <<'EOF'
---
handoff_type: DELEGATE
task_id: 2026-05-17-my-task
role: Engineer
model: claude-haiku-4-5
effort: low
scope: |
  Add input validation to the API gateway.
context:
  - Key files: src/api.py
plan:
  - 1. Read current validation logic
  - 2. Add request header validation
  - 3. Write tests
  - 4. Commit
success_criteria:
  - All tests passing
  - New validation covered by tests
EOF
```

### Run the Orchestrator

**OpenCode:**
```
@orchestrator  # Invoke orchestrator agent
```

**Claude Code:**
```bash
claude ask "You are the Orchestrator. Begin polling artifacts/queue/incoming/ and delegate all tasks."
```

---

## Harness Support

| Feature | OpenCode | Claude Code | Copilot CLI | π.dev |
|---------|:--------:|:-----------:|:-----------:|:-----:|
| Agents rendered | ✅ 8 | ✅ 8 | ❌ | ⚠️ Static |
| Skills rendered | ✅ 14 | ✅ 14 | ✅ 14 | ❌ |
| Managed config | ✅ | ❌ | ❌ | ⚠️ |
| Install path | `~/.config/opencode/` | `~/.claude/` | `~/.copilot/skills/` | `~/.pi/agent/` |

**Recommended:** OpenCode — most complete implementation.

```bash
make install-opencode    # Install
make status-opencode     # Verify
make uninstall-opencode  # Remove (only removes agentic-engineers files)
```

See [docs/OPENCODE-INSTALL.md](docs/OPENCODE-INSTALL.md) and [docs/CLAUDE-INSTALL.md](docs/CLAUDE-INSTALL.md).

---

## DELEGATE / HANDBACK Protocol

**DELEGATE** (task assignment):
```yaml
handoff_type: DELEGATE
task_id: 2026-05-17-fix-auth          # Unique: YYYY-MM-DD-slug
role: Engineer                         # Target role
model: claude-haiku-4-5               # Optional override
effort: low|medium|high|max
scope: |
  Clear description of work needed.
context:
  - Key files: src/auth.py
plan:
  - 1. Read current auth logic
  - 2. Fix token validation
  - 3. Write tests
success_criteria:
  - All tests passing
  - Auth edge cases covered
```

**HANDBACK** (task result):
```yaml
handoff_type: HANDBACK
task_id: 2026-05-17-fix-auth
agent: Engineer
status: COMPLETE|ESCALATE|REWORK
quality_score: 95
metrics:
  tokens_used: 12500
  duration: 342s
  test_coverage: 94%
result: |
  Fixed token validation in src/auth.py.
  Added 3 test cases covering expiry edge cases.
```

---

## Token Visibility & Budget Checking (Phase 3)

Real-time token tracking across all agents and subagents:

```bash
# Real-time token usage by agent
opencode-tokens --session <session-id>

# Budget status check
opencode-budget --session <session-id> --limit 200000

# List all subagents in session
opencode-subagents --session <session-id>
```

**Key insight:** Orchestrator sees only ~27% of actual token usage. Subagents account for ~73%. Always monitor at the session level.

**Recommended token allocation:**

| Role | Tokens | % |
|------|--------|---|
| Orchestrator (Haiku, low) | 60k | 30% |
| Engineer (Haiku, high) | 80k | 40% |
| Quality Engineer (Sonnet, medium) | 30k | 15% |
| Senior Engineer (Sonnet, high) | 20k | 10% |
| Other roles | 10k | 5% |

See [docs/QUICK-START-TOKEN-VISIBILITY.md](docs/QUICK-START-TOKEN-VISIBILITY.md) and [docs/QUICK-START-BUDGET-CHECKING.md](docs/QUICK-START-BUDGET-CHECKING.md).

---

## Quality Gates (3 Layers)

| Layer | Weight | Checks |
|-------|--------|--------|
| DELEGATE Structure | 40% | task_id format, role validity, scope clarity, plan completeness |
| Task Routing Quality | 35% | correct agent selection, confidence scoring |
| HANDBACK Validation | 25% | success_criteria met, quality_score ≥ threshold, metrics present |

**Routing by score:**
- 90–100: Move to done immediately
- 80–89: Move to done with notes
- 70–79: Route to Lead Engineer for review
- 60–69: Issue rework DELEGATE (max 2 retries)
- <60: Escalate to Principal Engineer

---

## SDLC Enforcement

Three git hooks enforce quality at commit/push time:

| Hook | Trigger | Enforces |
|------|---------|----------|
| **pre-commit** | `git commit` | SPEC compliance, secret detection, YAML validity |
| **commit-msg** | After commit message | Message format, DELEGATE/HANDBACK protocol |
| **pre-push** | `git push` | Agent YAML, tests, documentation, protocol compliance |

```bash
make install    # Installs hooks automatically
# or manually:
git config core.hooksPath .githooks
```

Emergency bypass (document reason in commit message):
```bash
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: reason"
SKIP_HOOKS=1 git push
```

---

## Testing

```bash
make test          # Full test suite (1047+ tests)
make test-quick    # Quick smoke tests
make coverage      # Coverage report
make verify        # SPEC compliance check
```

---

## Repository Structure

```
agentic-engineers/
├── src/                    # All source code
│   ├── agents/             # Agent definitions (*.md)
│   ├── skills/             # Skill implementations
│   ├── orchestration/      # Orchestration logic (Python)
│   └── config/             # Configuration (models.yaml)
├── docs/                   # All documentation
│   ├── SPEC.md             # Protocol specification (source of truth)
│   ├── AGENTS.md           # Agent routing reference
│   ├── HANDOFF.md          # DELEGATE/HANDBACK format
│   ├── INDEX.md            # Documentation index
│   └── archive/            # Archived docs
├── tests/                  # Test suite (pytest)
├── renderer/               # Build/installation system
│   └── scripts/            # render-opencode.sh, render-claude.sh, etc.
├── artifacts/              # Queue data (incoming/processing/done)
├── README.md               # This file
├── Makefile                # Build targets
└── TODO.md                 # Current work items
```

---

## Key Documentation

| Document | Purpose |
|----------|---------|
| [docs/SPEC.md](docs/SPEC.md) | Protocol specification (source of truth) |
| [docs/AGENTS.md](docs/AGENTS.md) | Agent routing reference + decision tree |
| [docs/HANDOFF.md](docs/HANDOFF.md) | DELEGATE/HANDBACK format + examples |
| [docs/QUEUE-PROTOCOL.md](docs/QUEUE-PROTOCOL.md) | Queue mechanics |
| [docs/SKILLS.md](docs/SKILLS.md) | Skills overview |
| [docs/INDEX.md](docs/INDEX.md) | Complete documentation index |
| [docs/OPENCODE-INSTALL.md](docs/OPENCODE-INSTALL.md) | OpenCode installation guide |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Troubleshooting (30+ scenarios) |

---

## Cost Optimization (Self-Improving)

Every task contributes metrics → Model Engineer analyzes → routing improves:

```
Task completes → Quality Engineer assesses model suitability
    ↓
Model Engineer analyzes: quality/cost/tokens/QE feedback
    ↓
Generates ranked recommendations (rank_1 to rank_3)
    ↓
Orchestrator applies rank_1 for next similar task
    ↓
System gets cheaper and better automatically
```

**Target:** 15–25% cost reduction over 3 months through better routing.

---

## Framework Integration Research

Comprehensive research on 45 AI frameworks completed (May 2026). Status: **⏸️ PAUSED** — no implementation until explicitly approved.

Top recommendations: CrewAI (51.5K★), LangGraph (32.1K★), Pydantic AI (17.1K★).

Full research: [docs/FRAMEWORKS/](docs/FRAMEWORKS/)

---

## When to Use This System

✅ **Good fit:**
- Codebases with 5+ services needing multi-agent coordination
- Teams wanting autonomous cost optimization
- High-quality output requirements (quality gates, escalation paths)
- Autonomous operation with full audit trail

❌ **Not needed:**
- Single-file changes ("fix typo in README")
- Simple tasks under 30 minutes
- Low-stakes work with no cost/quality concerns
