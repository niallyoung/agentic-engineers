# Agentic Engineers Repository - Comprehensive Overview

**Date:** May 16, 2026  
**Repository:** /Users/niall/git/agentic-engineers  
**Status:** Production Ready (1047+ tests passing)

---

## 1. OVERALL DIRECTORY STRUCTURE & PROJECT LAYOUT

### Top-Level Directory Structure

```
/Users/niall/git/agentic-engineers/
├── src/                              # Source code and canonical definitions
│   ├── agents/                       # Agent role definitions (canonical)
│   ├── skills/                       # Skill implementations for agents
│   ├── orchestration/                # Core orchestration framework
│   ├── tools/                        # Utility tools
│   ├── config/                       # Configuration management
│   └── dashboard/                    # Web dashboard (Next.js)
├── docs/                             # Comprehensive documentation
│   ├── AGENTS.md                     # Agent assignment & routing guide
│   ├── SKILLS.md                     # Skill definitions & workflows
│   ├── QUEUE-PROTOCOL.md             # Queue-based delegation mechanics
│   ├── HANDOFF.md                    # DELEGATE/HANDBACK protocol
│   ├── ENTRYPOINT.md                 # Workflow entry points
│   └── PROTOCOL.md                   # Protocol specification
├── renderer/                         # Build system for rendering agents
│   ├── scripts/                      # Render scripts (Copilot, Claude, π.dev)
│   ├── Makefile                      # Render targets
│   ├── hooks/                        # Pre-commit/session hooks
│   └── instructions/                 # Tool-specific instructions
├── artifacts/                        # Runtime artifacts
│   ├── queue/                        # Task queues (incoming/processing/done)
│   ├── delegates/                    # DELEGATE block archives
│   └── spans/                        # OpenTelemetry spans
├── tests/                            # Test suite (pytest)
├── setup/                            # Installation and startup scripts
├── Makefile                          # Main entry point (install/verify/clean)
├── renderer/Makefile                 # Render-specific targets
└── README.md                         # Main documentation (1318 lines)
```

### Key Subdirectories

#### src/agents/ - Agent Role Definitions (Canonical)
Contains provider-independent agent definitions in Markdown format:
- `engineer.md` — Implementation executor (Haiku, high effort)
- `senior-engineer.md` — Complex architecture & debugging (Sonnet, high)
- `orchestrator.md` — Task routing & metrics (Haiku, low)
- `principal-engineer.md` — Organization-wide strategy (Opus, high)
- `lead-engineer.md` — Code reviews & quality (Sonnet, high)
- `security-engineer.md` — Security & compliance (Opus, max)
- `quality-engineer.md` — Testing & validation (Sonnet, medium)
- `model-engineer.md` — Cost optimization (Sonnet, high)
- Plus: `metrics.md`, `testing.md`, `spec-engineer.md`, `healing-engineer.md`

**Format:** YAML frontmatter + Markdown content (provider-agnostic)

#### src/skills/ - Comprehensive Skill System
Organized by domain with 70+ skills:
- `orchestration/` — Task routing, queue management, coordination
- `security/` — Threat modeling, vulnerability assessment, compliance
- `testing/` — Unit, integration, E2E test execution
- `patterns/` — Implementation patterns and coding standards
- `monitoring/` — Metrics collection, token tracking, observability
- `review/` — Code review, quality analysis, approval workflows
- `architecture/` — System design, tradeoff analysis, decisions
- `optimization/` — Performance tuning, cost reduction
- `roles/` — Role-specific workflows
- `usage-tracking/` — Token budgeting and cost tracking
- `voice-notify/` — Multi-platform notification system

#### renderer/ - Build & Installation System
Transforms source definitions into harness-specific formats:
- `scripts/render-copilot.sh` — GitHub Copilot CLI rendering
- `scripts/render-claude.sh` — Claude Code rendering
- `scripts/render-pi-dev.py` — π.dev harness rendering
- `scripts/render-copilot-agents.py` — Agent YAML→CLI format
- `hooks/` — Guard and session-init hooks
- `shared.mk` — Common build rules

#### docs/ - Complete Protocol Documentation
- **AGENTS.md (550 lines)** — Agent roles, routing rules, effort levels
- **SKILLS.md (690 lines)** — Skill definitions, validation, error handling
- **QUEUE-PROTOCOL.md (518 lines)** — Queue mechanics, session partitioning
- **HANDOFF.md (492 lines)** — DELEGATE/HANDBACK/FEEDBACK protocol
- **ENTRYPOINT.md** — Workflow entry points and orchestration
- **PROTOCOL.md** — Master protocol specification
- Plus: ORCHESTRATION-README.md, CORE-PROTOCOL-QUICKSTART.md, etc.

---

## 2. EXISTING AGENTS.md AND SKILLS.md FILES

### AGENTS.md (Primary Agent Reference)

**Location:** `/Users/niall/git/agentic-engineers/docs/AGENTS.md` (550 lines)

**Contents:**
- 8 primary agent roles with model/effort/cost assignments
- Routing decision tree (6-point tree for task routing)
- Optimization feedback loop (Model Engineer analysis)
- Effort levels (Low/Medium/High/Extra High) with token budgets
- Voice-notify strategy and personalities
- Standard workflows (Dark Factory patterns)
- Cost targets per role
- Best practices and dark factory patterns
- Protocol compliance expectations
- FAQ and real-world examples

**Key Structure:**

| Role | Model | Effort | Cost/Task | Purpose |
|------|-------|--------|-----------|---------|
| Orchestrator | claude-haiku-4-5 | low | $0.03 | All entry points; routing; task management |
| Engineer | claude-haiku-4-5 | high | $0.03 | Well-scoped tasks with pre-written plans |
| Quality Engineer | claude-sonnet-4-6 | medium | $0.09 | Post-implementation validation |
| Senior Engineer | claude-sonnet-4-6 | high | $0.09 | Complex coding; unscoped work |
| Lead Engineer | claude-sonnet-4-6 | high | $0.09 | Code review; quality decisions |
| Principal Engineer | claude-opus-4-6 | high | $0.15 | Cross-service architecture |
| Security Engineer | claude-opus-4-7 | max | $0.15 | Security analysis; threat modeling |
| Model Engineer | claude-sonnet-4-6 | high | $0.09 | Cost optimization; routing recommendations |

**Routing Decision Tree:**
1. Security-scoped? → Security Engineer
2. Cross-service architecture? → Principal Engineer
3. Complex coding without plan? → Senior Engineer (plan first)
4. Code review or quality verification? → Lead Engineer / Quality Engineer
5. Well-planned, low-medium complexity? → Engineer
6. Otherwise → Escalate to human

**Cost Distribution (Phase 2C):**
- Orchestrator (Haiku Low): 60%
- Engineer (Haiku High): 18%
- Quality Engineer (Sonnet Medium): 8%
- Senior Engineer (Sonnet High): 7%
- Model Engineer (Sonnet High): 3%
- Lead Engineer (Sonnet High): 2%
- Principal Engineer (Opus 4.6 High): 1%
- Security Engineer (Opus 4.7 Max): 1%

### SKILLS.md (Agent Skill Definitions)

**Location:** `/Users/niall/git/agentic-engineers/docs/SKILLS.md` (690 lines)

**Contents:**
- Validation & error handling patterns
- Per-role skill specifications
- Orchestrator skills (7 core skills):
  - Queue Polling
  - DELEGATE validation & creation
  - Routing decision tree application
  - Agent delegation
  - HANDBACK reception & validation
  - HANDBACK routing
  - Span capture (OpenTelemetry)
  - Artifact indexing
- Core workflow summary
- Queue state transitions

**Key Orchestrator Skills:**

1. **Queue Polling** — Scan incoming/processing/done queues every 30-60s
2. **DELEGATE Validation** — Verify completeness before delegating
3. **Routing Decision Tree** — Apply AGENTS.md routing deterministically
4. **Agent Delegation** — Invoke agents asynchronously
5. **HANDBACK Reception** — Parse and validate results
6. **HANDBACK Routing** — Route to QE or escalation based on status
7. **Span Capture** — Create OpenTelemetry spans for observability
8. **Artifact Indexing** — Index for Model Engineer feedback loop

**Core Workflow:**
```
1. Poll incoming/ → Validate format → Apply routing tree → Create DELEGATE
2. Poll processing/ → Validate HANDBACK → Capture SPAN → Route to QE or escalation
3. Poll done/ → Check decision → Act on result → Move to archive
4. Apply Model Engineer recommendations for next similar task
```

---

## 3. CURRENT MAKE/BUILD/INSTALLATION TARGETS AND SCRIPTS

### Main Makefile (/Users/niall/git/agentic-engineers/Makefile)

**Install Targets:**
```make
make install              # Install to all 3 harnesses (~/.claude/, ~/.copilot/, ~/.pi/)
make install-claude      # Install rendered agents → ~/.claude/
make install-copilot     # Install rendered agents → ~/.copilot/
make install-pi          # Install π.dev harness → ~/.pi/
```

**Uninstall Targets:**
```make
make uninstall-claude    # Remove from ~/.claude/ (managed only)
make uninstall-copilot   # Remove from ~/.copilot/ (managed only)
make uninstall-pi        # Remove from ~/.pi/ (managed only)
make uninstall-all       # Remove from all 3 locations
```

**Render Targets (generate dist/ from source):**
```make
make render-claude       # Generate dist/claude/ (provider-specific)
make render-copilot      # Generate dist/copilot/ (provider-specific)
make render-pi           # Generate ~/.pi/agent/ config (π.dev harness)
make render-all          # All three
```

**Diagnostic Targets:**
```make
make status              # Check installation status (all harnesses)
make verify              # Verify framework structure + run tests
make clean               # Remove build artifacts
make help                # Show available targets
```

**Key Implementation Details:**

```bash
# Install workflow:
1. Render agents from src/agents/ → dist/ or direct installation
2. Copy skills from src/skills/ → target harness
3. Create queue structure
4. Set permissions

# Installation paths:
- ~/.copilot/agents/      # GitHub Copilot CLI
- ~/.copilot/skills/      # Copilot skills
- ~/.claude/agents/       # Claude Code
- ~/.claude/skills/       # Claude skills
- ~/.pi/agent/            # π.dev harness config

# Render scripts use:
- renderer/scripts/render-copilot.sh
- renderer/scripts/render-claude.sh
- renderer/scripts/render-pi.sh
- renderer/scripts/render-copilot-agents.py
- renderer/scripts/render-pi-dev.py
```

### Renderer Makefile (/Users/niall/git/agentic-engineers/renderer/Makefile)

**Install Targets:**
```make
make install              # Render agents + skills (main entry point)
make install-all          # All targets including ~/.github/
make install-github       # Copy hooks/scripts to ~/.github/ (legacy compat)
make install-copilot      # Render agents + skills into ~/.copilot/
make install-claude       # Render agents → ~/.claude/agents/, skills → ~/.claude/skills/
```

**Uninstall Targets:**
```make
make uninstall-github     # Remove from ~/.github/
make uninstall-copilot    # Remove from ~/.copilot/
make uninstall-claude     # Remove from ~/.claude/
make uninstall-all        # All three
```

**Status Target:**
```make
make status              # Drift report across all targets
```

**Render Scripts Available:**
- `render-copilot.sh` — Copilot CLI installation
- `render-claude.sh` — Claude Code installation
- `render-copilot-agents.py` — Agent definition rendering
- `render-pi-dev.py` — π.dev harness configuration
- `copilot-guard.sh` — Pre-commit guard for protocol compliance
- `copilot-session-init.sh` — Session initialization

---

## 4. HOW AGENTS AND SKILLS ARE CURRENTLY ORGANIZED AND CONFIGURED

### Agent Organization (Canonical in src/agents/)

**Source Files (Provider-Agnostic):**
- Located: `/Users/niall/git/agentic-engineers/src/agents/*.md`
- Format: YAML frontmatter + Markdown
- Each agent has 3 required frontmatter fields:
  - `name` — Display name
  - `description` — Brief description (1-2 sentences)
  - `model` — Claude model string (haiku/sonnet/opus)

**Rendering Pipeline:**
```
src/agents/*.md (ground truth)
    ↓
renderer/scripts/render-copilot-agents.py (YAML→CLI format)
    ↓
dist/copilot/*.agent.md OR ~/.copilot/agents/*.agent.md
dist/claude/*.agent.md  OR ~/.claude/agents/*.agent.md
```

**Agent Categories:**

**Core Agents (4):**
- Engineer — Implementation executor
- Senior Engineer — Complex architecture & debugging
- Orchestrator — Task routing & metrics
- Principal Engineer — Organization-wide strategy

**Specialized Agents (5):**
- Lead Engineer — Code review & critical issues
- Security Engineer — Security architecture
- Quality Engineer — Testing & validation
- Spec Engineer — Specification validation
- Healing Engineer — System debugging

**Support Agents (4):**
- Model Engineer — Cost optimization
- Metrics Agent — Token tracking
- Testing Agent — Test execution
- Spec Engineer Orchestrator — Spec + routing

### Skill Organization (Hierarchical in src/skills/)

**Skill Structure (70+ skills):**

```
src/skills/
├── orchestration/           # Core task orchestration
│   ├── task-routing.md      # Routing decision tree
│   ├── todo-management.md   # TODO.md tracking
│   ├── github-cli-operations.md
│   ├── model-engineer-coordination.md
│   └── README.md
├── security/                # Security domain
│   ├── threat-modeling.md
│   ├── vulnerability-assessment.md
│   ├── security-architecture-review.md
│   └── README.md
├── testing/                 # Test execution
│   ├── README.md
│   └── playwright-testing.md
├── patterns/                # Implementation patterns
│   ├── implementation-coding.md
│   └── (others)
├── monitoring/              # Metrics & observability
│   ├── metrics-collection.md
│   ├── token-advisor.md
│   ├── quality-feedback-analysis.md
│   ├── cicd-watch.md
│   └── README.md
├── review/                  # Code review workflows
│   ├── code-review.md
│   ├── code-quality-analysis.md
│   ├── quorum-qe.md
│   └── README.md
├── architecture/            # System design
│   ├── architecture-design.md
│   ├── system-tradeoff-analysis.md
│   ├── design-decision-documentation.md
│   └── README.md
├── roles/                   # Role-specific workflows
├── usage-tracking/          # Token budgeting
│   ├── SKILL.md
│   ├── README.md
│   ├── QUICK-START.md
│   └── AGENT-INTEGRATION.md
├── voice-notify/            # Notification system
│   ├── SKILL.md
│   ├── ARCHITECTURE.md
│   ├── VOICE-CONFIG.md
│   └── (others)
├── model-engineer/          # Model optimization
│   └── SKILL.md
└── (70+ other skills)
```

### Protocol Configuration

**Queue-Based Delegation System:**

```
~/.copilot/queue/
├── {session-id}/
│   ├── incoming/          # New tasks (Orchestrator polls here)
│   ├── processing/        # Tasks assigned to agents (waiting for HANDBACK)
│   └── done/              # Completed tasks (human reviews here)
└── .migration-log         # Legacy → partitioned migration record
```

**Artifact Storage:**

```
artifacts/
├── queue/
│   ├── incoming/          # New work
│   ├── processing/        # Work in progress
│   └── done/              # Completed work
├── delegates/
│   └── YYYY-MM-DD/        # DELEGATE block archives
│       └── DELEGATE-{task_id}-{role}.yaml
└── spans/                 # OpenTelemetry spans
    └── SPAN-{timestamp}-{agent_role}.yaml
```

### Configuration Management (src/config/)

- Standard configuration format definitions
- Configuration enforcement rules
- Configuration validation schemas

### Dashboard (src/dashboard/web/)

- Next.js-based web interface
- Real-time queue monitoring
- Agent status visualization
- Task metrics and cost tracking

---

## 5. EXISTING INSTALLATION AND SETUP MECHANISMS

### Startup & Initialization (setup/ directory)

**Files:**
- `setup/session-init.sh` — Initialize session environment
- `setup/STARTUP-CHECKLIST.md` — Pre-flight checklist
- `setup/STARTUP-INTEGRATION.md` — Integration guide
- `setup/GLOBAL_COPILOT_INSTRUCTIONS.md` — Global Copilot instructions
- `setup/copilot-instructions.md` — Copilot-specific setup
- `setup/README.md` — Setup documentation

**Responsibilities:**
- Environment variable setup
- Queue directory creation
- Session state initialization
- Permission management

### Installation Entry Point (Makefile)

**Two-Level System:**

**Level 1: Main Makefile (User-Facing)**
```bash
cd /Users/niall/git/agentic-engineers
make install              # Complete installation
make verify              # Verify + run tests
```

**Level 2: Renderer Makefile (Build System)**
```bash
cd /Users/niall/git/agentic-engineers/renderer
make install             # Render + install to all 3 harnesses
```

### Render Scripts (Automated Installation)

**Scripts Location:** `renderer/scripts/`

**Copilot Installation:**
```bash
renderer/scripts/render-copilot.sh [REPO_ROOT] [INSTALL_PATH] [--uninstall|--status]
# Renders src/agents/*.md → ~/.copilot/agents/
# Copies skills → ~/.copilot/skills/
# Creates queue structure
```

**Claude Installation:**
```bash
renderer/scripts/render-claude.sh [REPO_ROOT] [INSTALL_PATH] [--uninstall|--status]
# Renders src/agents/*.md → ~/.claude/agents/
# Copies skills → ~/.claude/skills/
```

**π.dev Installation:**
```bash
renderer/scripts/render-pi.sh [REPO_ROOT] [INSTALL_PATH] [--uninstall|--status]
# Uses render-pi-dev.py for configuration
```

**Installation Workflow:**
```
1. Parse arguments (REPO_ROOT, INSTALL_PATH, --uninstall|--status)
2. Validate source files (check for completeness)
3. Create target directories (mkdir -p)
4. Copy/symlink/render files based on target harness
5. Set permissions (chmod)
6. Create queue structure (incoming/, processing/, done/)
7. Verify installation (checksums or directory scan)
8. Report status (installed, up-to-date, or drift)
```

### Protocol Compliance Hooks

**Pre-commit Hook:** `renderer/hooks/guard.json`
- Validates DELEGATE blocks for completeness
- Checks HANDBACK format compliance
- Prevents non-compliant commits

**Session Initialization Hook:** `renderer/hooks/session-init.json`
- Initializes session state
- Creates queue directories
- Sets environment variables

### Test Suite

**Location:** `/Users/niall/git/agentic-engineers/tests/`

**Invoked by:**
```bash
make verify              # Main entry point
cd /Users/niall/git/agentic-engineers && python3 -m pytest tests/ -q --tb=short
```

**Test Coverage:**
- Framework structure verification
- Agent definition validation
- Skill completeness checks
- Protocol compliance validation
- End-to-end workflow tests (1047+ tests)

---

## 6. COMPREHENSIVE FEATURE SUMMARY

### Queue-Based Orchestration
- Session-partitioned queues (UUID per session)
- Three-stage workflow: incoming → processing → done
- Orchestrator polling (30-60s interval)
- Asynchronous agent delegation
- Automatic retry mechanism with exponential backoff

### DELEGATE/HANDBACK Protocol
- Machine-readable YAML format
- Mandatory fields validation
- Structured context transfer (no re-summarization)
- Status tracking (complete/blocked/partial)
- Token metrics collection

### 8 Specialized Agent Roles
- Orchestrator (routing & coordination)
- Engineer (implementation execution)
- Senior Engineer (complex design & diagnosis)
- Lead Engineer (code review & quality)
- Quality Engineer (post-implementation validation)
- Principal Engineer (cross-service architecture)
- Security Engineer (threat modeling & compliance)
- Model Engineer (cost optimization & routing improvements)

### Optimization Feedback Loop
- Quality Engineer provides model assessment
- Model Engineer analyzes metrics
- Ranking recommendations (Rank 1, 2, 3)
- Orchestrator applies top-ranked recommendations
- Autonomous cost optimization over time

### Comprehensive Skills System (70+ Skills)
- Orchestration (task routing, queue management)
- Security (threat modeling, vulnerability assessment)
- Testing (unit, integration, E2E)
- Monitoring (metrics, token tracking, observability)
- Code review (structured 8-point checklist)
- Architecture (system design, tradeoffs)

### Multi-Harness Support
- GitHub Copilot CLI
- Claude Code
- π.dev harness
- Provider-agnostic agent definitions
- Automatic rendering per harness

### Observability & Metrics
- OpenTelemetry span capture
- Artifact indexing (Model Engineer analysis)
- Token usage tracking
- Cost calculation and trending
- Quality score tracking

### Autonomy Management
- Reduced autonomy mode (prevents scope creep)
- TODO.md as source of truth
- Explicit pause/continue boundaries
- Task completion verification

---

## KEY FILES AND QUICK REFERENCE

### Documentation Files (Quick Links)

| File | Purpose | Lines |
|------|---------|-------|
| docs/AGENTS.md | Agent roles, routing, effort levels | 550 |
| docs/SKILLS.md | Skill definitions, validation | 690 |
| docs/QUEUE-PROTOCOL.md | Queue mechanics | 518 |
| docs/HANDOFF.md | DELEGATE/HANDBACK format | 492 |
| docs/ENTRYPOINT.md | Workflow entry points | - |
| docs/PROTOCOL.md | Master protocol spec | - |
| README.md | Project overview | 1318 |

### Source Files (Canonical)

| Location | Purpose |
|----------|---------|
| src/agents/*.md | Agent definitions (ground truth) |
| src/skills/**/*.md | Skill implementations |
| src/orchestration/ | Core orchestration framework |
| src/config/ | Configuration management |

### Build System

| Location | Purpose |
|----------|---------|
| Makefile | Main entry point |
| renderer/Makefile | Render-specific targets |
| renderer/scripts/ | Render and installation scripts |
| renderer/hooks/ | Pre-commit and session hooks |

### Runtime Structure

| Location | Purpose |
|----------|---------|
| ~/.copilot/agents/ | GitHub Copilot agents |
| ~/.claude/agents/ | Claude Code agents |
| ~/.pi/agent/ | π.dev configuration |
| artifacts/queue/ | Task queue (session-partitioned) |
| artifacts/delegates/ | DELEGATE archive |
| artifacts/spans/ | OpenTelemetry spans |

---

## INSTALLATION QUICK START

### One-Command Installation
```bash
cd /Users/niall/git/agentic-engineers
make install
```

### Verify Installation
```bash
make status              # Check all 3 harnesses
make verify             # Run full test suite
```

### What Gets Installed
- Agent definitions to ~/.copilot/agents/, ~/.claude/agents/, ~/.pi/agent/
- All 70+ skills to corresponding skill directories
- Queue structure (session-partitioned)
- Hooks and initialization scripts

### After Installation
- Queue tasks via `~/.copilot/queue/{session-id}/incoming/`
- Orchestrator polls and routes automatically
- Results appear in `~/.copilot/queue/{session-id}/done/`
- Artifacts stored in `artifacts/` for analysis

---

## PHASE 2C ARCHITECTURE (Current)

**Status:** Production Ready with Autonomous Optimization

The system implements:
1. **Queue-based routing** — All work flows through Orchestrator
2. **8 specialized agents** — Right tool for each task type
3. **Quality gates** — Post-implementation validation
4. **Feedback loops** — Model Engineer optimizes routing
5. **Cost optimization** — 15-25% cost reduction over 3 months (target)
6. **Multi-harness** — Copilot, Claude Code, π.dev support
7. **Full observability** — OpenTelemetry spans + artifact indexing

---

## NOTES FOR AGENTS AND SKILLS MANAGEMENT

### Managing Agents

**To update an agent:**
```bash
vim src/agents/engineer.md          # Edit source
make install                        # Render and install
head ~/.copilot/agents/engineer.agent.md  # Verify output
```

**To add a new agent:**
1. Create `src/agents/new-agent.md` with YAML frontmatter
2. Run `make install`
3. Test with appropriate harness

### Managing Skills

**To add a new skill:**
1. Create `src/skills/{domain}/new-skill.md`
2. Run `make install`
3. Reference in agent definitions

**Skill Naming Convention:**
- Domain-based organization: `security/`, `testing/`, `orchestration/`
- Clear purpose in filename: `threat-modeling.md`, `code-review.md`
- Consistent format: Header + description + implementation details

### Configuration Management

- Agent configs defined in AGENTS.md
- Skill configs defined in individual skill files
- Protocol rules in docs/PROTOCOL.md
- Queue rules in docs/QUEUE-PROTOCOL.md

---

## CONCLUSION

The **agentic-engineers** repository is a comprehensive, production-ready multi-agent orchestration framework with:

1. **Well-defined agents and skills** organized in source format
2. **Comprehensive documentation** of protocol and workflows
3. **Automated build system** for multi-harness deployment
4. **Queue-based execution model** enabling scalable orchestration
5. **Optimization feedback loops** for autonomous cost reduction
6. **Full observability** through OpenTelemetry and artifact indexing

All agents and skills are managed centrally in `src/`, rendered to provider-specific formats, and installed to target harnesses. The system is fully operational and ready for scaling to additional agents, skills, and use cases.
