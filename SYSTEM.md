---
name: agentic-engine{service-name}
description: Central system definition and bootstrap configuration for all CLI harnesses
type: system
---

# Agentic Engineers System Definition

**Single source of truth for CLI harness initialization and configuration.**

All CLI harnesses (Claude Code, GitHub Copilot, future integrations) parse this file to initialize the agentic-engineers framework.

---

## System Metadata

| Property | Value |
|----------|-------|
| **Name** | Agentic Engineers |
| **Version** | 1.0 |
| **Type** | Multi-agent orchestration framework |
| **Roles** | 8 (Orchestrator, Engineer, Senior, Lead, Principal, Security, Quality, Model) |
| **Location** | `agentic-engineers/` (self-contained) |
| **State** | `.session-state/` (excluded from git) |
| **Bootstrap** | `setup/session-init.sh` |
| **Documentation** | `MANIFEST.md` (complete file listing) |

---

## Initialization Sequence

### 1. Parse This File (SYSTEM.md)

CLI harness reads this file to understand:
- System structure and roles
- Initialization requirements
- Key files and entry points
- Configuration and state locations

### 2. Run Bootstrap Script

```bash
bash agentic-engineers/setup/session-init.sh
```

**What happens**:
- ✅ Token usage tracking initialized
- ✅ Budget status determined (GREEN/YELLOW/RED)
- ✅ Session marker created (idempotent)
- ✅ Usage history started

**Properties**:
- Idempotent: safe to call multiple times
- Self-contained: no external dependencies (~/.claude/, ~/.github/)
- State stored in: `.session-state/` (auto-excluded from git)

### 3. Load Framework Rules

Read and follow:
- `setup/copilot-instructions.md` — Framework enforcement rules
- `orchestration/AGENTS.md` — Role definitions and routing
- `orchestration/HANDOFF.md` — Task handoff protocol
- `MANIFEST.md` — Complete file listing (discovery tool)

### 4. Ready for Work

Framework initialized. Accept tasks via DELEGATE protocol.

---

## Directory Structure

```
agentic-engineers/                 # Self-contained framework root
├── SYSTEM.md                      # ← YOU ARE HERE (bootstrap config)
├── README.md                      # Quick overview
├── MANIFEST.md                    # Complete file listing (100+ files)
│
├── setup/                         # Framework setup and rules
│   ├── copilot-instructions.md   # Enforcement rules for all agents
│   ├── GLOBAL_COPILOT_INSTRUCTIONS.md  # Global rules
│   ├── session-init.sh           # Bootstrap script (idempotent)
│   ├── STARTUP-INTEGRATION.md    # Startup integration guide
│   └── STARTUP-CHECKLIST.md      # Verification checklist
│
├── orchestration/                 # How work flows through system
│   ├── AGENTS.md                 # 8 roles, routing rules
│   ├── HANDOFF.md                # DELEGATE/HANDBACK protocol
│   ├── QUALITY.md                # Quality gate checklist
│   ├── AUTOMATIC-INVOCATION.md   # Automatic integration points
│   ├── ORCHESTRATOR-CHECKLIST.md # Orchestrator workflow
│   ├── USAGE-BUDGET-MANAGER.md   # Real-time budget checking
│   ├── USAGE-BUDGET-INTEGRATION.md # Budget in delegation
│   └── TOKEN-USAGE-TRACKING.md   # Historical usage analysis
│
├── skills/                        # 38+ domain-organized skills
│   ├── usage-tracking/           # Token usage capture/analysis skill
│   │   ├── SKILL.md              # Skill definition
│   │   ├── SESSION-INIT.sh       # Usage tracking initialization
│   │   ├── QUICK-START.md        # 5-minute start guide
│   │   ├── AGENT-INTEGRATION.md  # When agents invoke
│   │   └── scripts/              # capture, analyze, wrapper
│   ├── voice-notify/             # Voice alert skill
│   ├── [other domains]/          # architecture, patterns, review, etc.
│   └── roles/                    # Per-role capability definitions
│
├── operations/                    # Metrics and optimization
├── reference/                     # Architecture patterns
├── guides/                        # Learning materials
├── config/                        # Locked configuration
│
├── .session-state/               # Runtime state (excluded from git)
│   └── current-session-initialized  # Session marker
│
└── .gitignore                    # Excludes .session-state/
```

---

## Key Files by Purpose

### Bootstrap & Setup
- `SYSTEM.md` (this file) — Central bootstrap config
- `setup/session-init.sh` — Run at session start
- `.gitignore` — Excludes runtime state

### Entry Points
- `README.md` — Quick overview
- `MANIFEST.md` — Complete file listing (discovery)
- `setup/copilot-instructions.md` — Framework rules

### Framework Definition
- `orchestration/AGENTS.md` — Role definitions
- `orchestration/HANDOFF.md` — Task protocol
- `orchestration/QUALITY.md` — Quality gates

### Automated Features
- `skills/usage-tracking/SKILL.md` — Token monitoring skill
- `orchestration/AUTOMATIC-INVOCATION.md` — Automation integration
- `orchestration/ORCHESTRATOR-CHECKLIST.md` — Orchestrator workflow

---

## Configuration

### Session Initialization

**Automatic**: `bash agentic-engineers/setup/session-init.sh`

**Properties**:
- Idempotent: skip if already initialized
- State file: `agentic-engineers/.session-state/current-session-initialized`
- No external dependencies (no ~/.claude/, ~/.github/)

### Agent Roles

Defined in `orchestration/AGENTS.md`:

| Role | Model | Cost | Primary Use |
|------|-------|------|-------------|
| Orchestrator | Haiku 4.5 | 1x | Routing, checkpoints, metrics |
| Engineer | Haiku/Sonnet | 1-3x | Implementation, TDD |
| Senior Engineer | Sonnet | 3x | Complex code, architecture |
| Lead Engineer | Sonnet | 3x | Code review, quality |
| Principal Engineer | Opus | 5x | Design, strategy |
| Security Engineer | Sonnet | 3x | Threat modeling, audits |
| Quality Engineer | Sonnet | 3x | Testing, verification |
| Model Engineer | Haiku | 1x | Metrics, optimization |

### Task Handoff Protocol

Defined in `orchestration/HANDOFF.md`:

**DELEGATE**: Orchestrator → Agent
- Context, plan, success criteria
- Budget awareness (GREEN/YELLOW/RED)
- Model assignment

**HANDBACK**: Agent → Orchestrator
- Deliverables, tests, metrics
- Token consumption, efficiency notes
- Status (complete/partial/blocked)

---

## Automatic Features (No Agent Action Required)

Enabled by `setup/session-init.sh`:

### Token Usage Tracking

**Automatic invocations**:
- Session start: Capture baseline
- Pre-delegation: Check budget → set model tier
- Every 30 min: Monitor velocity (% per hour)
- Task completion: Collect metrics in HANDBACK
- Session end: Export final analysis

**Data storage**: `data/metrics/usage_history.jsonl` (project-local)

**Voice alerts**: Daniel voice at 70% (warning) and 85% (critical)

### Budget-Aware Routing

Model selection automatic based on budget:
- GREEN (0-70%): Use best model for task (Sonnet/Opus)
- YELLOW (70-85%): Use Sonnet (balanced efficiency)
- RED (>85%): Use Haiku only OR defer task

---

## CLI Harness Integration Pattern

All CLI harnesses follow this pattern:

### Step 1: Parse SYSTEM.md
```
Read agentic-engineers/SYSTEM.md
Extract:
  - bootstrap_script: "setup/session-init.sh"
  - entry_points: ["setup/copilot-instructions.md", "MANIFEST.md"]
  - state_dir: ".session-state/"
  - initialization: "session-init.sh"
```

### Step 2: Run Bootstrap
```bash
bash agentic-engineers/setup/session-init.sh
```

### Step 3: Load Rules
```
Read: setup/copilot-instructions.md
Read: orchestration/AGENTS.md
Read: orchestration/HANDOFF.md
```

### Step 4: Ready
Framework initialized, accept DELEGATE blocks from user.

---

## Future CLI Harnesses

New CLI harnesses (IDE extensions, web interfaces, etc.) follow the same pattern:

1. **Parse SYSTEM.md** — Extract config
2. **Run setup/session-init.sh** — Initialize
3. **Load setup/copilot-instructions.md** — Get rules
4. **Reference MANIFEST.md** — Discover files
5. **Accept DELEGATE blocks** — Start accepting work

---

## Documentation Map

### For Understanding the System
- `MANIFEST.md` — Complete file listing (discovery)
- `README.md` — Quick overview
- `guides/CLAUDE.md` — Team context and integration

### For Using the Framework
- `setup/copilot-instructions.md` — Rules and enforcement
- `orchestration/AGENTS.md` — Role definitions
- `orchestration/HANDOFF.md` — Task protocol
- `orchestration/QUALITY.md` — Quality gates

### For Specific Tasks
- `orchestration/ORCHESTRATOR-CHECKLIST.md` — Orchestrator workflow
- `skills/usage-tracking/QUICK-START.md` — Usage tracking setup
- `skills/[role]/skills/` — Role-specific capabilities

---

## Quick Reference

### At Session Start
```bash
bash agentic-engineers/setup/session-init.sh
```

### Accept a Task
```yaml
---
handoff_type: DELEGATE
task_id: YYYY-MM-DD-task-name
role: [role name from AGENTS.md]
model: [model from AGENTS.md]
budget_context:
  session_pct_at_delegation: XX
  status: GREEN|YELLOW|RED
...
---
```

### Return Work
```yaml
---
handoff_type: HANDBACK
task_id: YYYY-MM-DD-task-name
status: complete|partial|blocked
metrics:
  usage_before_session_pct: XX
  usage_after_session_pct: YY
  tokens_consumed_estimate: XXXX
  model_used: [model]
...
---
```

### Check Token Budget
```bash
bash skills/usage-tracking/scripts/usage-tracking.sh analyze
```

---

## Properties

| Property | Value |
|----------|-------|
| **Bootstrap file** | `SYSTEM.md` (this file) |
| **Initialization** | `setup/session-init.sh` |
| **Framework location** | Entirely within `agentic-engineers/` |
| **External dependencies** | None (~/.claude/, ~/.github/ not used) |
| **State location** | `.session-state/` (excluded from git) |
| **Idempotency** | All scripts safe to call multiple times |
| **Discovery tool** | `MANIFEST.md` (100+ files documented) |
| **Enforcement rules** | `setup/copilot-instructions.md` |
| **Key definitions** | `orchestration/AGENTS.md`, `HANDOFF.md` |

---

## Status

✅ **Production Ready**
- All 8 roles defined and documented
- Automatic token tracking integrated
- Budget-aware delegation enabled
- Quality gates in place
- 100+ files documented
- All tests passing

---

## See Also

- `MANIFEST.md` — Complete file listing with every file documented
- `setup/copilot-instructions.md` — Framework rules (referenced by all harnesses)
- `orchestration/AGENTS.md` — Role definitions
- `orchestration/HANDOFF.md` — Task protocol
- `setup/STARTUP-INTEGRATION.md` — How initialization integrates with harnesses
