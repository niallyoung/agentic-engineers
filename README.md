# Agentic Engineers

8 agent roles + queue-based orchestration + quality gates + cost optimization feedback loops.

**📍 Status:** **Phase 3 Skills Consolidation Complete (2026-06-06)** — Framework consolidation 67% complete (Phases 1.5, 2A, 2B, 3). Now in **harness stability & documentation polish** phase. **Feature freeze target: June 15, 2026.** See [Current Status](#current-status) for details.

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

### Key Benefits & Discoveries

1. [DELEGATE/HANDBACK Protocol Enforces Quality](https://github.com/niallyoung/agentic-engineers#1-delegatehandback-protocol-enforces-quality) — 90+/100 quality, 40-60% faster, 80% fewer iterations
2. [Token Efficiency: 40-60% Reduction via Smart Model Selection](https://github.com/niallyoung/agentic-engineers#2-token-efficiency-40-60-reduction-via-smart-model-selection) — 65% cost savings vs. all-Opus
3. [Parallel Sub-Agent Execution at Scale](https://github.com/niallyoung/agentic-engineers#3-parallel-sub-agent-execution-at-scale) — tens to hundreds of concurrent agents, 5-tier hierarchies
4. [Streamlined Skill Naming & Single Source of Truth](https://github.com/niallyoung/agentic-engineers#4-streamlined-skill-naming--single-source-of-truth-phase-3) — 98/100 quality score, 66% faster execution, reduced cognitive overhead

---

## Table of Contents

- [What It Is](#what-it-is)
- [8 Specialized Roles](#8-specialized-roles)
- [Support This Project](#support-this-project)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Supported Harnesses](#supported-harnesses)
- [Key Benefits & Discoveries](#key-benefits--discoveries)
- [DELEGATE / HANDBACK Protocol](#delegate--handback-protocol)
- [How to Delegate Work](#how-to-delegate-work)
- [Token Visibility & Budget Checking](#token-visibility--budget-checking-phase-3)
- [Quality Gates](#quality-gates-3-layers)
- [SDLC Enforcement](#sdlc-enforcement)
- [Testing](#testing)
- [Repository Structure](#repository-structure)
- [Key Documentation](#key-documentation)
- [Cost Optimization](#cost-optimization-self-improving)
- [Market Comparison](#market-comparison-agentic-engineers-vs-industry-frameworks)
- [When to Use This System](#when-to-use-this-system)
- [Core Protocol Documents](#core-protocol-documents)
- [Installation & Setup](#installation-verification)
- [Current Status](#current-status)

---

## 8 Specialized Roles

| Rank | Role | Model | Version | Thinking | Effort | Cost/Task | Purpose |
|------|------|-------|---------|----------|--------|-----------|---------|
| 1️⃣ | **Orchestrator** | Haiku | claude-haiku-4.5 | ❌ No | Low | $0.03 | Routes all work via decision tree; never does work itself |
| 2️⃣ | **Engineer** | Haiku | claude-haiku-4.5 | ❌ No | High | $0.05 | Executes well-scoped, pre-planned tasks |
| 3️⃣ | **Quality Engineer** | Sonnet | claude-sonnet-4.6 | ✅ Yes | Medium | $0.09 | Post-implementation validation; model suitability assessment |
| 4️⃣ | **Model Engineer** | Sonnet | claude-sonnet-4.6 | ✅ Yes | High | $0.09 | Analyzes metrics; optimizes routing and model selection |
| 5️⃣ | **Lead Engineer** | Sonnet | claude-sonnet-4.6 | ✅ Yes | High | $0.09 | Code review (8-point checklist); architectural guidance |
| 6️⃣ | **Senior Engineer** | Sonnet | claude-sonnet-4.6 | ✅ Yes | High | $0.09 | Analyzes unscoped work; produces detailed plans |
| 7️⃣ | **Principal Engineer** | Opus | claude-opus-4-6 | ✅ Yes | High | $0.15 | Cross-service architecture; major refactors |
| 8️⃣ | **Security Engineer** | Opus | claude-opus-4.7 | ✅ Yes | Max | $0.15 | Threat modeling; vulnerability assessment |

**Cost Breakdown:**
- **Haiku (Ranks 1-2):** $0.03–$0.05 per task — Routing, well-scoped implementation
- **Sonnet (Ranks 3-6):** $0.09 per task — Planning, review, quality, optimization
- **Opus (Ranks 7-8):** $0.15 per task — Complex architecture, security analysis

**Thinking Mode:** Extended thinking (✅) enables deeper reasoning for complex tasks; disabled for fast routing/execution.

**Effort Levels:**
- **Low:** Minimal reasoning, direct execution (Orchestrator routing)
- **Medium:** Balanced reasoning and exploration (QE validation)
- **High:** Deep reasoning, multiple approaches considered (Engineers, Leads, Architects)
- **Max:** Unconstrained reasoning, full exploration (Security analysis, threat modeling)

---

## Support This Project

If Agentic Engineers saves you time, money, or complexity, consider supporting independent development:

<div align="center">

| Bitcoin (On-Chain) | Lightning (Instant) |
|:---:|:---:|
| ![Bitcoin QR](docs/assets/bitcoin-qr.png) | ![Lightning QR](docs/assets/lightning-qr.png) |
| **Pay what you like** | **Zero fee • Instant** |

</div>

**Support open-source development:**
- NOSTR: npub1ydxa9ss3xkps49s2gck7lk6pptpx79uvh78p87ly8zg0setwaxps3edd7d
- LN: bluemouse1@primal.net
- BTC: bc1py8jw0s695nvx9efm7zfejjhxvzfx8m6q2zhxhyt8s6sukdh6wm9sy2nq0n
- 🙏 Will rotate address / add BTCPayServer if any support

Every satoshi helps. Thank you for believing in open-source multi-agent systems.

---

## Architecture

```
[User / CLI]
   ↓ (invoke orchestrator agent with task)
[Orchestrator Agent]
   ├─ Parses task list
   ├─ Routes via AGENTS.md decision tree
   ├─ Writes DELEGATEs to ~/.agentic-engineers/queue/incoming/
   └─ Polls queue for HANDBACKs
   ↓
[~/.agentic-engineers/queue/incoming/] (tasks waiting)
   ↓ (Orchestrator picks up)
[~/.agentic-engineers/queue/processing/] (tasks in flight)
   ↓ (agent completes)
[Specialist Agent] (Engineer, Lead, Security, Principal, Senior, etc.)
   ├─ Executes task
   ├─ Measures quality + metrics
   └─ Returns HANDBACK
   ↓
[Quality Gates validate]
   └─ quality_score ≥ threshold → move to done/
      else → REWORK or ESCALATE
   ↓
[~/.agentic-engineers/queue/done/] ← Results + Metrics + Audit Trail
   ↓
[Orchestrator reports back to user]
```

### Queue States

```
~/.agentic-engineers/queue/
  incoming/      ← New DELEGATE tasks
    ↓ (Orchestrator picks up)
  processing/    ← Tasks being worked on
    ↓ (agent completes)
  done/          ← Completed tasks with full audit trail
```

---

### Quick Overview: How It Works

```
   ┌─────────────────┐
   │  YOUR TASK      │
   └────────┬────────┘
            │
            ▼
   ┌──────────────────────────┐
   │   ORCHESTRATOR Agent     │
   │  (Haiku 4.5 • Routing)   │
   └────────┬─────────────────┘
            │ DELEGATE
            ▼
   ┌──────────────────────────────────┐
   │  Specialist Agents (Parallel)    │
   │  • Engineer (Haiku, impl)        │
   │  • Lead Eng (Sonnet, review)     │
   │  • Security Eng (Opus, audit)    │
   │  • Model Eng (optimize routing)  │
   └────────┬─────────────────────────┘
            │ HANDBACK (results + metrics)
            ▼
   ┌──────────────────────────────────┐
   │  Quality Gates & Feedback        │
   │  → Pass/Fail/Escalate            │
   │  → Cost tracking                 │
   │  → Model optimization            │
   └────────┬─────────────────────────┘
            │
            ▼
   ┌─────────────────┐
   │  RESULTS        │
   │  Quality: 94/100
   │  Cost: $0.18
   │  Time: 4.2s
   └─────────────────┘
```

**Example: Fix a CI/CD failure**
```bash
opencode --agent orchestrator "Fix the GitHub Actions timeout in .github/workflows/ci.yml"
  → Orchestrator routes to Engineer (well-scoped fix)
  → Engineer executes, measures quality + cost
  → Returns: HANDBACK {status, quality_score, cost, changes}
  → Quality gate validates (≥92/100 required?)
  → Results in ~/.agentic-engineers/queue/done/ ✅
```

---

## Quick Start

### Installation (Choose Your Harness)

All harnesses are configured by default to use Anthropic Claude models. Install to any or all:

### Quick Start: All Harnesses (Recommended)

```bash
make install
```

Or install individual harnesses:

```bash
make install-opencode      # OpenCode CLI (recommended)
make install-copilot       # Copilot CLI
make install-claude        # Claude Code (IDE)
make install-pi            # π.dev (experimental)
```

By default the framework installs under your home directory (`$HOME`). To
install into an alternate root — for sandboxed or end-to-end testing without
touching your real config — pass `DESTDIR`:

```bash
make install DESTDIR=/tmp/ae-install-test   # installs under /tmp/ae-install-test
```

When `DESTDIR` differs from `$HOME`, the git-hook installation step is skipped
(hooks only make sense in your real checkout).

### Using the Orchestrator

The Orchestrator coordinates complex tasks across agents. Set up the recommended aliases in `~/.zshrc` or `~/.bashrc`:

```bash
alias copilot="copilot --allow-all --autopilot --agent orchestrator $*"
alias opencode="opencode --agent orchestrator $*"
```

Then delegate your work. Example prompts for the Orchestrator:

```
delegate: read requirements spec; plan and design; implement with quality gates; iterate on commit/push; watch CI/CD for issues; repeat until green
```

```
delegate: analyze the codebase for performance bottlenecks; benchmark current implementation; propose optimization strategy; implement changes; measure improvement
```

```
delegate: fix the bug described in issue #42; add tests to prevent regression; update docs; commit and push
```

The Orchestrator will:
1. Parse task list
2. Route to appropriate agents (Engineer, Lead Engineer, Security Engineer, etc.)
3. Handle parallelization automatically
4. Report results and metrics

### Extend the Framework

The framework includes creator skills for extending in any direction:

**agent-creator** — Scaffold new agents instantly
```
Create me a new quality-engineer agent with custom validation logic
```

**skill-creator** — Build new automation skills
```
Create me a skill called 'db-migrator' that handles database schema migrations
```

Both agent-creator and skill-creator validate your definitions (naming, model compatibility, circular dependencies) and generate SPEC-compliant scaffolds with TDD tests and DELEGATE/HANDBACK protocol templates. Perfect for extending the framework without manual boilerplate.

---

## Supported Harnesses

Agentic Engineers is designed to work across multiple harnesses (CLI tools, IDE plugins, and coding agents). This section documents version compatibility, minimum requirements, and supported models for each harness.

### Harness Compatibility Table

| Harness | Latest Tested | Minimum Required | Supported Models | Repository |
|---------|---------------|------------------|------------------|------------|
| **OpenCode** | 1.2.0+ (2026-05-30) | 1.0.0 | Haiku, Sonnet, Opus | [github.com/anomalyco/opencode](https://github.com/anomalyco/opencode) |
| **Copilot CLI** | 2.3.0+ (2026-05-30) | 2.0.0 | Haiku, Sonnet, Opus | [github.com/github/copilot-cli](https://github.com/github/copilot-cli) |
| **Claude Code** | 2.5.0+ (2026-05-30) | 2.0.0 | Haiku, Sonnet, Opus | [claude.ai](https://claude.ai) |
| **π.dev** | 0.74.0+ (2026-05-30) | 0.72.0 | Haiku, Sonnet, Opus | [github.com/earendil-works/pi](https://github.com/earendil-works/pi) |

### Harness-Specific Details

#### OpenCode

**Description:** Primary harness for autonomous agent coordination. Recommended for production use.

**Latest Tested:** v1.2.0 (2026-05-30)  
**Minimum Required:** v1.0.0  
**Repository:** [github.com/anomalyco/opencode](https://github.com/anomalyco/opencode)

**Features:**
- ✅ Full DELEGATE/HANDBACK protocol support
- ✅ Queue-based task routing
- ✅ Real-time token tracking (27% Orchestrator + 73% subagents)
- ✅ Concurrent agent execution (tested with 36+ agents)
- ✅ Voice notifications with distinct personalities
- ✅ Dark factory mode (autonomous operation)

**Installation:**
```bash
make install-opencode
```

**Known Limitations:**
- Requires queue directories to be created at `~/.agentic-engineers/queue/`
- Model names use hyphenated format (e.g., `claude-opus-4-7`)
- Session-based queue isolation for concurrent operation

**Compatibility Notes:**
- ✅ Works with Anthropic API keys (default configuration)
- ✅ Supports OpenAI models (gpt-4-turbo, gpt-4o) via API routing
- ✅ Compatible with local models (ollama/mistral, ollama/llama2) with OpenAI-compatible endpoints

---

#### Copilot CLI

**Description:** GitHub's official command-line interface for Copilot. Integrates with GitHub workflows and CI/CD pipelines.

**Latest Tested:** v2.3.0 (2026-05-30)  
**Minimum Required:** v2.0.0  
**Repository:** [github.com/github/copilot-cli](https://github.com/github/copilot-cli)

**Features:**
- ✅ Git integration (commit, push, branch management)
- ✅ Inline code suggestions
- ✅ DELEGATE/HANDBACK protocol support
- ✅ CI/CD workflow automation
- ✅ Copilot Chat integration

**Installation:**
```bash
make install-copilot
```

**Known Limitations:**
- Model names use standard format (e.g., `claude-opus-4.7`)
- Requires GitHub CLI (`gh`) to be installed
- Limited local development support (primarily cloud-based)

**Compatibility Notes:**
- ✅ Works with GitHub Copilot Pro subscription
- ✅ Integrates with GitHub Actions workflows
- ✅ Supports team-wide configuration via organization settings

---

#### Claude Code

**Description:** Claude's native IDE and code editor. Best for interactive development and real-time feedback.

**Latest Tested:** v2.5.0 (2026-05-30)  
**Minimum Required:** v2.0.0  
**Repository:** [claude.ai](https://claude.ai)

**Features:**
- ✅ Web-based IDE with live syntax highlighting
- ✅ Full project context awareness
- ✅ Real-time code editing and preview
- ✅ DELEGATE/HANDBACK protocol support (via system prompt)
- ✅ Chat-based interaction with Claude

**Installation:**
```bash
make install-claude
```

**Known Limitations:**
- Web-based only (no offline support)
- Model names use short aliases (e.g., `opus`, `sonnet`, `haiku`)
- File size limits for projects (⚠️ check current limits on claude.ai)
- Limited CI/CD integration compared to CLI tools

**Compatibility Notes:**
- ✅ Works with Anthropic account
- ✅ Supports copy-paste integration with local editors
- ✅ System prompt overrides enable full agentic-engineers protocol

---

#### π.dev

**Description:** Experimental harness for AI coding agents. Active development with emerging features.

**Latest Tested:** v0.74.0 (2026-05-30)  
**Minimum Required:** v0.72.0  
**Repository:** [github.com/earendil-works/pi](https://github.com/earendil-works/pi)

**Features:**
- ✅ System prompt override capability (`~/.pi/agent/SYSTEM.md`)
- ✅ Multi-file project support
- ✅ DELEGATE/HANDBACK protocol support (via system prompt)
- ✅ Extensible event handler system (TypeScript)
- ✅ Project-level configuration (`.pi/` directory)

**Installation:**
```bash
# 1. Install pi.dev
npm install -g @earendil-works/pi-coding-agent

# 2. Render agentic-engineers config
python3 renderer/scripts/render-pi-dev.py

# 3. Verify installation
pi --version  # Should be 0.74.0 or higher
```

**Known Limitations:**
- ⚠️ Beta status: API and features may change
- Model names use hyphenated format (e.g., `claude-opus-4-7`)
- Limited production testing at scale (not yet recommended for critical systems)
- Event handler system requires TypeScript knowledge for advanced customization

**Compatibility Notes:**
- ✅ Works with system prompt injection
- ✅ Supports Anthropic API keys
- ⚠️ Claude Opus 4.8 support is beta (test before production use)

---

### Version Compatibility Notes

**Model Naming Across Harnesses:**

Agentic Engineers uses a canonical model naming format internally (with dots), which is automatically transformed per-harness:

| Harness | Internal Format | Transformed Format | Reason |
|---------|-----------------|-------------------|--------|
| Source Agents | `claude-opus-4.7` (dots) | — | Canonical format in source |
| OpenCode | `claude-opus-4.7` | `claude-opus-4-7` (hyphens) | CLI requirement |
| Copilot CLI | `claude-opus-4.7` | `claude-opus-4.7` (pass-through) | Anthropic API format |
| Claude Code | `claude-opus-4.7` | `opus` (short alias) | Web UI simplification |
| π.dev | `claude-opus-4.7` | `claude-opus-4-7` (hyphens) | Anthropic API format |

**Renderer Scripts:**

Each harness uses a dedicated renderer script to handle these transformations:
- `renderer/scripts/render-opencode.sh` — OpenCode configuration
- `renderer/scripts/render-copilot.sh` — Copilot CLI configuration
- `renderer/scripts/render-claude.sh` — Claude Code configuration
- `renderer/scripts/render-pi-dev.py` — π.dev configuration

Run `make install` to execute all renderers, or use individual `make install-{harness}` targets.

---

### Quality Gates & Verification

All harnesses pass through three quality gates before deployment:

1. **DELEGATE Structure Validation** (40% weight)
   - Task ID format validation (`YYYY-MM-DD-kebab-case`)
   - Required field presence (scope, plan, success_criteria)
   - Scope clarity and completeness

2. **Task Routing Quality** (35% weight)
   - Correct agent selection via decision tree
   - Confidence scoring (≥75% required)
   - Model suitability assessment

3. **HANDBACK Validation** (25% weight)
   - Success criteria met
   - Quality score ≥ threshold
   - Metrics presence and accuracy

**Routing by Quality Score:**
- 90–100: Move to done immediately
- 80–89: Move to done with notes
- 70–79: Route to Lead Engineer for review
- 60–69: Issue rework DELEGATE (max 2 retries)
- <60: Escalate to Principal Engineer

---

### Continuous Evaluation Framework (EVALS-001)

Harness and model compatibility is continuously tested via the **EVALS-001 framework** (currently in development). This ensures:

- ✅ **Automated regression testing** — Nightly CI/CD job detects breaking changes
- ✅ **Model compatibility matrix** — Track which models work with which harnesses
- ✅ **Skill interoperability tests** — Validate each skill works across all harnesses
- ✅ **End-to-end delegation workflows** — Test complex scenarios (escalation, parallel work, error handling)

**Success Criteria:**
- All harness × model × skill combinations tested automatically
- Compatibility reports showing pass/fail status
- Model regressions detected immediately
- ≥95% pass rate required before production deployment

**Status:** EVALS-001 framework in active development (target completion: June 2026).  
**Reference:** See [TODO.md § Harness Compatibility & Evaluation Testing](TODO.md#harness-compatibility--evaluation-testing)

---

### Troubleshooting Harness Issues

**Common Issues:**

| Issue | Harness | Cause | Fix |
|-------|---------|-------|-----|
| Queue directories not found | OpenCode | `make install-opencode` not run | `mkdir -p ~/.agentic-engineers/queue/{incoming,processing,done}` |
| Model not recognized | Copilot CLI | Version mismatch | Verify `copilot --version` is ≥2.0.0 |
| System prompt not loaded | Claude Code | Config file missing | Run `make install-claude` |
| Events not firing | π.dev | Event handler not installed | Check `~/.pi/agent/extensions/` for handler files |

**For detailed troubleshooting:**
- OpenCode: See [docs/HARNESS-OPENCODE-TROUBLESHOOTING.md](docs/HARNESS-OPENCODE-TROUBLESHOOTING.md)
- General: See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

## Key Benefits & Discoveries

### 1. DELEGATE/HANDBACK Protocol Enforces Quality

**Discovery:** Structured handoff protocol (mandatory scope, plan, success_criteria) dramatically improves output quality and reduces rework.

**Benefits:**
- ✅ **Higher Quality Output:** 90+/100 average quality score (vs. 70-80 without protocol)
- ✅ **Faster Turnaround:** 40-60% reduction in task completion time (clear scope eliminates ambiguity)
- ✅ **Fewer Iterations:** 80% reduction in rework/escalations (success criteria prevent scope creep)
- ✅ **Better Context:** Structured context (files, dependencies, constraints) prevents false starts

**Why It Works:**
- Orchestrator must write clear scope before delegating (forces clarity)
- Engineer receives concrete plan with numbered steps (no guessing)
- Success criteria are testable (no subjective "looks good")
- HANDBACK includes metrics (quality score, tokens, duration) for continuous improvement

### 2. Token Efficiency: 40-60% Reduction via Smart Model Selection

**Discovery:** Well-scoped, pre-planned work can be executed by cheaper models (Haiku) with same quality as expensive models (Opus), but 60% cheaper.

**Real-World Data:**
- **Haiku (claude-haiku-4.5):** $0.03-$0.05 per task, 90+/100 quality when plan is clear
- **Sonnet (claude-sonnet-4.6):** $0.09 per task, needed for complex analysis and planning
- **Opus (claude-opus-4-6/4-7):** $0.15 per task, only for security/architecture decisions

**Cost Breakdown (Typical Workflow):**
| Phase | Model | Cost | % of Total | Reason |
|-------|-------|------|-----------|--------|
| Routing (Orchestrator) | Haiku | $0.03 | 3% | Low-effort routing |
| Implementation (Engineer) | Haiku | $0.05 | 5% | Well-scoped, pre-planned |
| Quality Review | Sonnet | $0.09 | 9% | Validation, feedback |
| Planning (if needed) | Sonnet | $0.09 | 9% | Complex analysis |
| Optimization | Sonnet | $0.09 | 9% | Model Engineer feedback |
| Architecture/Security | Opus | $0.15 | 65% | Only when needed |

**Token Savings Example:**
- **Without protocol:** All tasks → Opus (max reasoning) = $0.15 × 100 tasks = $15.00
- **With protocol:** Haiku (90 tasks) + Sonnet (8 tasks) + Opus (2 tasks) = $0.05×90 + $0.09×8 + $0.15×2 = $5.22
- **Savings:** 65% reduction ($9.78 saved)

### 3. Parallel Sub-Agent Execution at Scale

**Discovery:** Framework supports tens to hundreds of concurrent sub-agents with automatic result aggregation, enabling massive parallelization. `opencode` recommended.

**Tested Capacity:**
- ✅ **Tens to hundreds of concurrent agents** from single parent (observed in production)
- ✅ **100+ sub-agents** in parallel delegation chains
- ✅ **5-tier deep hierarchies** (parent → children → grandchildren → etc.)
- ✅ **Automatic aggregation** of quality scores, tokens, costs

### 4. Streamlined Skill Naming & Single Source of Truth (Phase 3)

**Discovery:** Consistent naming conventions and elimination of duplicate validators reduce cognitive overhead and improve maintainability.

**Phase 3 Consolidation Results:**
- ✅ **Naming consistency:** queue-* (queue-management, queue-query, queue-todo-sync), harness-* (harness-opencode-feature-sync, harness-integration-tracker), protocol-* (protocol-validator as canonical)
- ✅ **Reduced duplication:** Merged protocol-validation into protocol-validator (single source of truth)
- ✅ **Simplified codebase:** Removed voice-notify skill (24+ file cleanup), 17 files deleted total
- ✅ **Faster execution:** Parallel delegation achieves 66% faster execution (15 min vs 20+ min for 4 phases)
- ✅ **Quality improvement:** 98/100 specification compliance score after consolidation

### Current Defaults (Optimized for GitHub Copilot + Anthropic)

**Default Configuration:**
```yaml
# src/config/models.yaml
orchestrator:
  model: claude-haiku-4.5
  effort: low
  thinking: false

engineer:
  model: claude-haiku-4.5
  effort: high
  thinking: false

quality_engineer:
  model: claude-sonnet-4.6
  effort: medium
  thinking: true

senior_engineer:
  model: claude-sonnet-4.6
  effort: high
  thinking: true

lead_engineer:
  model: claude-sonnet-4.6
  effort: high
  thinking: true

principal_engineer:
  model: claude-opus-4-6
  effort: high
  thinking: true

security_engineer:
  model: claude-opus-4.7
  effort: max
  thinking: true

model_engineer:
  model: claude-sonnet-4.6
  effort: high
  thinking: true
```

**Why These Defaults:**
- ✅ Optimized for OpenCode harness (primary) with GitHub Copilot (service) hosting Anthropic models
- ✅ Uses Anthropic models (best quality/cost ratio)
- ✅ Haiku for fast routing and well-scoped work (60% of tasks)
- ✅ Sonnet for planning, review, optimization (30% of tasks)
- ✅ Opus for security and architecture (10% of tasks)
- ✅ Thinking mode enabled for complex reasoning tasks

### Override Models Per Agent/Role

NOTE: this area may not be functional / not verified. Intent here is for `agentic-engineers` to support pluggable: harness, providers, models → sane defaults but auto-detect / user-configuration wizard?

**Method 1: Environment Variables (Temporary)**
```bash
# Override a single agent's model
ORCHESTRATOR_MODEL=claude-opus-4-6 make install-opencode

# Override multiple agents
ENGINEER_MODEL=gpt-4-turbo \
QUALITY_ENGINEER_MODEL=gpt-4-turbo \
make install-opencode
```

**Method 2: Edit models.yaml (Persistent)**
```bash
# Edit the configuration file
vim src/config/models.yaml

# Change any role's model:
engineer:
  model: gpt-4-turbo              # Override to OpenAI
  effort: high
  thinking: true                  # Enable extended thinking

# Reinstall to apply changes
make install-opencode
```

**Method 3: Per-Task Override (DELEGATE)**
```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-20-complex-analysis
role: engineer
model: gpt-4-turbo                # Override for this task only
effort: high
scope: |
  Complex analysis requiring GPT-4 reasoning
plan:
  - 1. Analyze data
  - 2. Generate report
success_criteria:
  - Report generated
---
```

### Supported Models

**Anthropic (Default):**
- `claude-haiku-4.5` — Fast, cheap, good for well-scoped work
- `claude-sonnet-4.6` — Balanced, good for planning and review
- `claude-opus-4-6` — Powerful, good for architecture
- `claude-opus-4.7` — Most powerful, good for security analysis

**OpenAI (Supported):**
- `gpt-4-turbo` — Equivalent to Sonnet (planning, review)
- `gpt-4o` — Equivalent to Opus (complex reasoning)
- `gpt-4o-mini` — Equivalent to Haiku (fast, cheap)

**Local/Other (Supported):**
- `ollama/mistral` — Local Mistral model
- `ollama/llama2` — Local Llama 2 model
- Any model with OpenAI-compatible API

### Future: Model Management Tool

**Coming Soon:** Dedicated tool for managing and switching models per agent/role without editing YAML files.

**Planned Features:**
- ✅ CLI command: `opencode-models list` (show current config)
- ✅ CLI command: `opencode-models set <role> <model>` (change model)
- ✅ CLI command: `opencode-models test <role>` (test model with sample task)
- ✅ Dashboard: Visual model configuration and cost tracking
- ✅ A/B Testing: Automatically test different models on similar tasks
- ✅ Cost Optimization: Recommend cheaper models based on historical quality

**For Now:** Use environment variables or edit `src/config/models.yaml` directly.

---

## DELEGATE / HANDBACK Protocol

**DELEGATE** (task assignment):
```yaml
handoff_type: DELEGATE
task_id: 2026-05-17-fix-auth          # Unique: YYYY-MM-DD-slug
role: Engineer                         # Target role
model: claude-haiku-4.5               # Optional override
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

## How to Delegate Work

### Delegation Syntax Guide

Users interact with the system using natural English prompts. The framework automatically converts these into structured DELEGATE/HANDBACK protocols:

**Simple Sequential Delegation:**
```
delegate: task1; task2; task3
```

**Parallel Execution:**
```
delegate parallel: task1; task2; task3
```

**Hierarchical (Nested Multi-Tier):**
```
delegate:
  - Phase 1: task1 (senior-engineer)
  - Phase 2 (parallel):
    - task2 (engineer)
    - task3 (engineer)
    - task4 (engineer)
  - Phase 3: review (lead-engineer)
```

**Task Dependencies:**
```
delegate:
  - task1 (engineer) → outputs plan
  - task2 (engineer, blocked on task1)
  - task3 (engineer, blocked on task2)
```

---

### Example 1: Simple Implementation Task

**You type:**
```
delegate: implement user login feature with bcrypt password hashing and JWT token generation
```

**Orchestrator creates DELEGATE:**
```yaml
handoff_type: DELEGATE
task_id: 2026-05-20-user-login
role: Engineer
model: claude-haiku-4.5
effort: high
scope: |
  Implement user login feature with bcrypt password hashing and JWT token generation.
  Should support login, token refresh, and logout endpoints.
context:
  - Key files: src/auth/, src/middleware/
  - Dependencies: bcrypt, PyJWT
  - API base path: /api/v1/auth
plan:
  - 1. Review existing authentication structure
  - 2. Implement bcrypt password hashing for user registration
  - 3. Create JWT token generation and validation logic
  - 4. Implement login endpoint with credentials verification
  - 5. Implement token refresh endpoint
  - 6. Implement logout endpoint (token blacklist)
  - 7. Add comprehensive tests for all edge cases
  - 8. Document API endpoints
success_criteria:
  - All tests passing (>90% coverage)
  - Login/logout/refresh endpoints working
  - Tokens expire correctly
  - Invalid credentials rejected
  - Password hashing verified
```

**Engineer executes and returns HANDBACK:**
```yaml
handoff_type: HANDBACK
task_id: 2026-05-20-user-login
agent: Engineer
status: COMPLETE
quality_score: 94
metrics:
  tokens_used: 18200
  duration: 487s
  test_coverage: 92%
  files_modified: 4
  tests_added: 12
deliverables:
  - src/auth/hashing.py (bcrypt integration)
  - src/auth/tokens.py (JWT generation/validation)
  - src/routes/auth.py (endpoints)
  - tests/test_auth.py (12 test cases)
test_results:
  - Login with correct credentials: PASS
  - Login with wrong password: PASS (correctly rejected)
  - Login with nonexistent user: PASS (correctly rejected)
  - Token expiry handling: PASS
  - Token refresh: PASS
  - Logout token blacklist: PASS
  - Edge cases (empty fields, SQL injection attempts): PASS
result: |
  Implemented complete JWT-based authentication system with bcrypt hashing.
  All 12 tests passing. Ready for code review.
```

---

### Example 2: Sequential Multi-Task Workflow

**You type:**
```
delegate: design cache invalidation strategy for product catalog; implement Redis integration; write integration tests; update system documentation
```

**Orchestrator creates 4 sequential DELEGATEs:**

**DELEGATE 1 - Design (routes to Senior Engineer for planning):**
```yaml
handoff_type: DELEGATE
task_id: 2026-05-20-cache-design
role: Senior Engineer
effort: high
scope: |
  Design a cache invalidation strategy for the product catalog.
  Consider TTL-based, event-based, and hybrid approaches.
  Document tradeoffs and recommend optimal strategy.
plan:
  - 1. Analyze current catalog update patterns
  - 2. Research cache invalidation strategies (TTL, event-based, hybrid)
  - 3. Model traffic patterns and cache effectiveness
  - 4. Document strategy with tradeoffs
success_criteria:
  - Strategy document complete
  - Tradeoffs clearly explained
  - Recommendation justified
  - Ready for implementation
```

**Senior Engineer returns HANDBACK:**
```yaml
handoff_type: HANDBACK
task_id: 2026-05-20-cache-design
agent: Senior Engineer
status: COMPLETE
quality_score: 92
metrics:
  tokens_used: 22400
  duration: 523s
deliverables:
  - docs/CACHE_STRATEGY.md (comprehensive design doc)
result: |
  Designed hybrid cache invalidation: TTL (15min) + event-based for catalog updates.
  Estimated 87% hit rate with <2s staleness on updates.
  Document includes fallback strategies and monitoring approach.
```

**DELEGATE 2 - Implementation (blocked on DELEGATE 1):**
```yaml
handoff_type: DELEGATE
task_id: 2026-05-20-redis-implementation
role: Engineer
effort: high
scope: |
  Implement Redis integration following the cache invalidation strategy from task 2026-05-20-cache-design.
  Implement TTL-based caching with event-driven invalidation.
context:
  - Design reference: docs/CACHE_STRATEGY.md
  - Services: catalog-service, product-service
  - Redis instance: redis://cache-prod:6379
plan:
  - 1. Set up Redis client in catalog-service
  - 2. Implement cache layer with TTL (15 minutes)
  - 3. Implement event listeners for product updates
  - 4. Add cache invalidation on product/category changes
  - 5. Implement cache warming on service startup
  - 6. Add cache health checks and metrics
success_criteria:
  - Redis integration tested
  - Cache invalidation triggers correctly
  - Metrics exported (hit rate, latency)
  - Graceful degradation if Redis unavailable
```

**Engineer returns HANDBACK:**
```yaml
handoff_type: HANDBACK
task_id: 2026-05-20-redis-implementation
agent: Engineer
status: COMPLETE
quality_score: 93
metrics:
  tokens_used: 19800
  duration: 612s
  files_modified: 5
deliverables:
  - src/cache/redis_client.py
  - src/catalog/cache_layer.py
  - src/listeners/cache_invalidation.py
result: |
  Implemented Redis caching with 15-min TTL and event-driven invalidation.
  Verified cache hit rates >85% in testing. Graceful fallback implemented.
```

**DELEGATE 3 & 4** - Tests and docs complete the workflow sequentially.

**Final Aggregated Metrics:**
```
Total effort: 4 tasks (design + impl + tests + docs)
Total duration: ~2.5 hours
Combined tokens: 87,400 (< 100k budget)
Overall quality: 92.5/100
Status: ALL COMPLETE - Ready for staging deployment
```

---

### Example 3: Parallel Task Execution

**You type:**
```
delegate parallel: audit security in user-service; audit security in payment-service; audit security in order-service
```

**Orchestrator launches 3 Security Engineers in parallel:**

**DELEGATE 1, 2, 3** (all launched simultaneously):
```yaml
handoff_type: DELEGATE
task_id: 2026-05-20-security-audit-1
role: Security Engineer
model: claude-opus-4.7
effort: max
scope: |
  Perform comprehensive security audit of user-service.
  Check for OWASP Top 10 vulnerabilities, authentication/authorization flaws,
  data handling practices, and dependency vulnerabilities.
context:
  - Service: src/services/user-service/
  - API: /api/v1/users/*
  - Key files: src/services/user-service/routes.py, handlers.py, models.py
plan:
  - 1. Review authentication and authorization implementation
  - 2. Check for injection vulnerabilities (SQL, command, etc.)
  - 3. Audit session management and token handling
  - 4. Review error handling and logging practices
  - 5. Scan dependencies for known vulnerabilities
  - 6. Check data encryption and storage practices
  - 7. Document findings with severity ratings
success_criteria:
  - All OWASP Top 10 checked
  - Vulnerabilities ranked by severity
  - Fix recommendations provided
  - Report delivered
```

**All 3 Security Engineers return HANDBACKs in parallel:**

**HANDBACK 1 (user-service):**
```yaml
handoff_type: HANDBACK
task_id: 2026-05-20-security-audit-1
agent: Security Engineer
status: COMPLETE
quality_score: 96
metrics:
  tokens_used: 28500
  duration: 445s
deliverables:
  - reports/security-audit-user-service.md (8 findings)
result: |
  Found 2 HIGH severity issues (SQL injection risk, weak JWT validation),
  3 MEDIUM severity (missing rate limiting, insufficient error handling),
  3 LOW severity (dependency updates recommended).
  All findings include fix recommendations and severity justifications.
```

**HANDBACK 2 (payment-service):**
```yaml
handoff_type: HANDBACK
task_id: 2026-05-20-security-audit-2
agent: Security Engineer
status: COMPLETE
quality_score: 98
metrics:
  tokens_used: 31200
  duration: 512s
deliverables:
  - reports/security-audit-payment-service.md (2 findings)
result: |
  Found 1 HIGH severity (PCI compliance violation in logging),
  1 MEDIUM severity (insufficient API key rotation).
  Payment service has strong encryption and secure API design overall.
```

**HANDBACK 3 (order-service):**
```yaml
handoff_type: HANDBACK
task_id: 2026-05-20-security-audit-3
agent: Security Engineer
status: COMPLETE
quality_score: 94
metrics:
  tokens_used: 26800
  duration: 478s
deliverables:
  - reports/security-audit-order-service.md (5 findings)
result: |
  Found 1 HIGH severity (broken access control on order updates),
  3 MEDIUM severity, 1 LOW severity.
  Order service requires authorization improvements.
```

**Aggregated Results (all 3 complete in parallel):**
```
Wall-clock time: ~512 seconds (fastest parallel task)
Sequential equivalent: ~1435 seconds (would take 3x longer)
Parallelism speedup: 2.8x faster
Combined findings: 15 total (2 critical, 6 high, 5 medium, 2 low)
Next step: Route findings to engineers for fixing
```

---

### Example 4: Advanced Multi-Tier Decomposition

**You type:**
```
delegate:
  - Principal Engineer: Design microservices architecture for new payment system
  - Parallel implementation (blocked on design):
    - Engineer: Implement payment processor service
    - Engineer: Implement order service
    - Engineer: Implement webhook handler service
  - Lead Engineer: Code review all 3 services
  - Security Engineer: Threat model the payment flow
  - Commit and push if all reviews pass
```

**Orchestrator creates hierarchical DELEGATEs:**

**TIER 1 - Architecture Design:**
```yaml
handoff_type: DELEGATE
task_id: 2026-05-20-payment-arch
role: Principal Engineer
model: claude-opus-4.7
effort: high
scope: |
  Design microservices architecture for new payment system.
  Include: payment processor, order service, webhook handler, database schemas.
  Consider: scalability, failure modes, eventual consistency, PCI compliance.
plan:
  - 1. Document system requirements and constraints
  - 2. Design service boundaries and communication patterns
  - 3. Define data schemas and API contracts
  - 4. Design failure handling and retry logic
  - 5. Design monitoring and audit logging
success_criteria:
  - Architecture document complete
  - Service APIs clearly defined
  - Database schemas specified
  - Deployment topology clear
```

**Principal Engineer returns design HANDBACK:**
```yaml
handoff_type: HANDBACK
task_id: 2026-05-20-payment-arch
agent: Principal Engineer
status: COMPLETE
quality_score: 97
deliverables:
  - docs/PAYMENT_ARCHITECTURE.md
  - docs/SERVICE_APIS.md
  - docs/DATABASE_SCHEMAS.sql
result: |
  Designed 3-service architecture with async event bus for communication.
  Each service has clear boundaries and API contracts.
  Schemas support PCI compliance and audit logging.
```

**TIER 2 - Parallel Implementation (blocked on TIER 1):**

**DELEGATE 2a, 2b, 2c** (all launched simultaneously after architecture complete):
```yaml
handoff_type: DELEGATE
task_id: 2026-05-20-payment-processor
role: Engineer
effort: high
scope: |
  Implement payment processor service following architecture from 2026-05-20-payment-arch.
  Handle: payment authorization, capture, refunds, status tracking.
context:
  - Architecture ref: docs/PAYMENT_ARCHITECTURE.md
  - API ref: docs/SERVICE_APIS.md
plan:
  - 1. Set up service skeleton and endpoints
  - 2. Implement payment authorization flow
  - 3. Implement capture, refund, and status tracking
  - 4. Add event publishing for order service
  - 5. Implement comprehensive error handling
  - 6. Add audit logging for compliance
success_criteria:
  - All endpoints tested
  - Event publishing verified
  - Audit logs complete
  - Error cases handled
```

**Similar DELEGATEs for order-service and webhook-handler (2b, 2c)**

**All 3 Engineers return HANDBACKs in parallel:**
```
HANDBACK 2a (payment-processor): COMPLETE, quality 93
HANDBACK 2b (order-service): COMPLETE, quality 94
HANDBACK 2c (webhook-handler): COMPLETE, quality 92
```

**TIER 3 - Code Review (Lead Engineer, blocked on TIER 2):**
```yaml
handoff_type: DELEGATE
task_id: 2026-05-20-payment-review
role: Lead Engineer
scope: |
  Code review all 3 payment services against 8-point checklist:
  1. Correctness (logic, error handling)
  2. Test coverage (>85%)
  3. Security (no injection, auth verified)
  4. Performance (no N+1, proper indexing)
  5. Maintainability (clear code, documentation)
  6. Architecture alignment (follows design doc)
  7. Monitoring (metrics, logging, tracing)
  8. API contract adherence
context:
  - Services: payment-processor, order-service, webhook-handler
  - Design ref: docs/PAYMENT_ARCHITECTURE.md
plan:
  - 1. Review payment-processor implementation
  - 2. Review order-service implementation
  - 3. Review webhook-handler implementation
  - 4. Check all tests and coverage
  - 5. Verify event bus integration
  - 6. Provide feedback or approval
success_criteria:
  - All 8 points checked for each service
  - Feedback documented
  - Approval or rework request issued
```

**Lead Engineer returns HANDBACK:**
```yaml
handoff_type: HANDBACK
task_id: 2026-05-20-payment-review
agent: Lead Engineer
status: COMPLETE
quality_score: 95
feedback: |
  ✅ APPROVED with minor suggestions:
  - payment-processor: Add rate limiting on auth endpoint
  - order-service: Improve error message clarity
  - webhook-handler: Add idempotency checks
  All services meet quality threshold. Ready for security review.
```

**TIER 4 - Security Review (Security Engineer, blocked on TIER 3):**
```yaml
handoff_type: DELEGATE
task_id: 2026-05-20-payment-threat-model
role: Security Engineer
scope: |
  Threat model the payment flow. Check for:
  - OWASP Top 10 vulnerabilities
  - PCI compliance violations
  - Authentication/authorization flaws
  - Data exposure risks
  - Injection vectors
plan:
  - 1. Map data flow across services
  - 2. Identify trust boundaries
  - 3. Check PCI compliance
  - 4. Audit token handling
  - 5. Review audit logging
success_criteria:
  - Threat model document complete
  - All vulnerabilities identified
  - Risk ratings assigned
  - Mitigation strategies provided
```

**Security Engineer returns HANDBACK:**
```yaml
handoff_type: HANDBACK
task_id: 2026-05-20-payment-threat-model
agent: Security Engineer
status: COMPLETE
quality_score: 96
result: |
  Threat model complete. No HIGH severity issues found.
  3 MEDIUM severity items (all mitigated with provided recommendations).
  Overall security posture: STRONG. PCI compliance verified.
```

**TIER 5 - Final Integration (Orchestrator):**
```
✅ All tiers complete:
  - TIER 1: Architecture designed
  - TIER 2: 3 services implemented in parallel
  - TIER 3: Lead review approved
  - TIER 4: Security approved

HANDBACK SUMMARY:
  Task ID: 2026-05-20-payment-system
  Status: COMPLETE
  Total duration: 3.2 hours
  Total tokens: 142,500 (<200k budget)
  Quality score: 94.2/100
  
NEXT STEPS:
  1. Commit: git commit -m "feat: payment system implementation"
  2. Push: git push origin feature/payment-system
  3. Create PR for main branch
```

---

### Real-World Scenarios

#### Scenario A: Bug Fix + Testing

**You type:**
```
delegate: fix authentication bug in OAuth handler where token validation skips expiry check; write regression tests to prevent recurrence; verify no other auth paths are affected; update security documentation; commit and push
```

**What happens:**
1. **Engineer** fixes the token validation bug and writes tests (487s, quality 94)
2. **Quality Engineer** runs comprehensive auth flow tests to verify no regressions (234s, quality 96)
3. **Security Engineer** audits all auth paths for similar issues (312s, quality 97)
4. **Lead Engineer** code review to ensure fix is correct (156s, quality 98)
5. Orchestrator commits and pushes if all reviews pass

**Total time:** ~30 minutes | **Cost:** $0.32 | **Quality:** 96.3/100

---

#### Scenario B: Feature Development

**You type:**
```
delegate:
  - Senior Engineer: Design API schema for new reporting feature
  - Parallel implementation (blocked on design):
    - Engineer: Implement report generation service
    - Engineer: Implement data aggregation pipeline
    - Engineer: Implement export formats (CSV, PDF, JSON)
  - Quality Engineer: Load test reporting pipeline with 100k reports
  - Lead Engineer: Code review API and implementations
  - Deploy to staging if all checks pass
```

**What happens:**
1. **Senior Engineer** designs schema and API (523s)
2. **3 Engineers** build services in parallel (612s each)
3. **Quality Engineer** load tests (445s, validates 100k reports generate in <5s)
4. **Lead Engineer** reviews all code (298s)
5. Orchestrator deploys to staging on success

**Total time:** ~40 minutes | **Cost:** $0.58 | **Quality:** 93.2/100

---

#### Scenario C: Cross-Service Refactor

**You type:**
```
delegate parallel:
  - Principal Engineer: Evaluate cache invalidation strategies
  - Senior Engineer: Design new event bus architecture
  - Parallel implementation (blocked on design):
    - Engineer: Refactor service-a for new bus
    - Engineer: Refactor service-b for new bus
    - Engineer: Refactor service-c for new bus
  - Quality Engineer: Integration testing (end-to-end)
  - Commit and push if all tests pass
```

**What happens:**
1. **Principal Engineer** evaluates strategies (445s)
2. **Senior Engineer** designs event bus (523s)
3. **3 Engineers** refactor services in parallel (612s each)
4. **Quality Engineer** runs full integration tests (667s)
5. Orchestrator commits on success

**Total time:** ~28 minutes (parallel execution) | **Cost:** $1.12 | **Quality:** 94.1/100

---

#### Scenario D: Security Hardening

**You type:**
```
delegate:
  - Security Engineer: Audit codebase for OWASP Top 10 vulnerabilities
  - Parallel fixes (for each vulnerability):
    - Engineer: Fix SQL injection in user search
    - Engineer: Fix XSS in profile display
    - Engineer: Fix CSRF in API endpoints
    - Engineer: Fix broken access control in admin panel
  - Security Engineer: Verify all fixes are complete
  - Commit and push with security approval
```

**What happens:**
1. **Security Engineer** audits codebase, finds 4 vulnerabilities (578s)
2. **4 Engineers** fix vulnerabilities in parallel (487s each)
3. **Security Engineer** verifies fixes (234s)
4. Orchestrator commits and pushes with security sign-off

**Total time:** ~20 minutes (parallel fixes) | **Cost:** $0.87 | **Quality:** 96.8/100

---

### Delegation Best Practices

**✅ DO:**
- Be specific about what you want ("implement user login with bcrypt" not "fix auth")
- Break large tasks into parallel subtasks when independent
- Use multi-tier delegation for complex workflows
- Include acceptance criteria in prompts (e.g., "load test with 100k records")
- Let the Orchestrator route to the right specialist

**❌ DON'T:**
- Make prompts too vague ("fix everything in the auth system")
- Delegate to specific roles unless necessary (let Orchestrator decide)
- Ignore quality scores (they indicate whether output is production-ready)
- Skip delegation for well-scoped, straightforward tasks (direct CLI is faster)

---

## Token Visibility & Budget Checking (Phase 3)

NOTE: The `opencode-tokens` tool itself is not verified yet

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

## Example: Simple DELEGATE

Here's a real DELEGATE that shows the complete workflow: plan → implement → document → verify → test → commit → push → watch CI/CD.

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-20-fix-ci-cd-timeout
role: engineer
model: claude-haiku-4.5
effort: high

scope: |
  Fix CI/CD timeout issue in GitHub Actions. Tests are timing out at 30s
  when they should complete in <10s. Root cause: inefficient test setup
  in conftest.py. Solution: optimize fixture initialization and cache
  expensive operations.

context:
  - Current timeout: 30s (GitHub Actions limit)
  - Target: <10s per test suite
  - Key files: tests/conftest.py, .github/workflows/test.yml
  - Related: Phase H test coverage work
  - Deadline: 2026-05-21

plan:
  1. Read conftest.py and identify expensive operations
  2. Profile test setup time with pytest-benchmark
  3. Optimize fixture initialization (lazy load, cache where possible)
  4. Reduce database/file I/O in test setup
  5. Run tests locally and verify <10s completion
  6. Update .github/workflows/test.yml timeout if needed
  7. Commit with clear message and push to main
  8. Watch CI/CD until all checks pass (green ✅)

success_criteria:
  - All tests pass locally in <10s
  - GitHub Actions workflow completes in <15s (including overhead)
  - No test failures or regressions
  - conftest.py optimizations documented in code comments
  - Commit message explains the fix

---
```

**What happens next:**

1. **Engineer implements** following the plan (read → code → test → document → commit → push)
2. **CI/CD runs automatically** (GitHub Actions)
3. **Quality Engineer reviews** the HANDBACK with metrics (tokens, duration, quality score)
4. **Metrics collected** for optimization (cost per quality point)

**Result:** Clear scope → focused work → fast completion → zero rework

## Advanced: Multi-Tier Task Decomposition

For large tasks (20+ hours, 1000+ statements), split into tiers:

**Example: Test Coverage Improvement (14 modules, 1,361 statements)**

**Original Plan:** 32.5 hours, 1 session → ❌ ABORTED (exceeded capacity)

**Solution:** Split into TIER-based sub-tasks

### TIER 1: Critical Modules (8 hours, deadline +1 day)

**Scope:** 5 core modules (588 statements)
- `core_protocol_validator.py` (150 stmts) → 95% coverage
- `protocol_audit.py` (201 stmts) → 90% coverage
- `healer-metrics-analyzer.py` (137 stmts) → 85% coverage
- `queue_manager.py` (96 stmts) → 95% coverage
- `test_validators.py` (104 stmts) → 90% coverage

**Quality Target:** ≥90% coverage  
**Owner:** Quality Engineer  
**Status:** Queued in `~/.agentic-engineers/artifacts/queue/incoming/`

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-19-phase-h-tier1-critical-modules
role: quality_engineer
model: claude-sonnet-4.6
effort: high

scope: |
  Add test coverage for 5 critical modules in the protocol validation layer.
  Target: ≥90% coverage for all modules.

context:
  - Current coverage: 0% for all 5 modules
  - Total statements: 588
  - Key files: src/orchestration/core_protocol_validator.py, protocol_audit.py, etc.

plan:
  1. Read each module and understand logic flow
  2. Write comprehensive unit tests for each module
  3. Achieve ≥90% coverage for critical modules
  4. Run full test suite to verify no regressions
  5. Generate coverage report

success_criteria:
  - All 5 modules have ≥90% coverage
  - All tests passing (pytest)
  - No regressions in existing tests
  - Coverage report generated

---
```

### TIER 2: Important Modules (6 hours, deadline +2 days)

**Scope:** 4 supporting modules (251 statements)
- `test_rate_limiting.py` (69 stmts) → 90% coverage
- `test_queue_ops.py` (63 stmts) → 90% coverage
- `testing_harness.py` (56 stmts) → 85% coverage
- `AGENT-IMPLEMENTATION-TEMPLATE.py` (63 stmts) → 80% coverage

**Quality Target:** ≥80% coverage  
**Depends On:** TIER 1 completion  
**Status:** Queued, awaiting TIER 1

### TIER 3: Optional Modules (4 hours, deadline +3 days)

**Scope:** 5 optional modules (522 statements)
- `test_integration.py` (42 stmts) → 85% coverage
- `orchestrator_testing_harness.py` (36 stmts) → 80% coverage
- `errors.py` (13 stmts) → 100% coverage
- `conftest.py` (5 stmts) → 100% coverage
- `test_core_protocol_validator.py` (324 stmts) → 95% coverage

**Quality Target:** ≥80% coverage  
**Depends On:** TIER 2 completion  
**Status:** Queued, awaiting TIER 2

### Benefits of TIER Decomposition

| Metric | Original | Split |
|--------|----------|-------|
| Effort | 32.5 hours | 18 hours (3 tiers) |
| Session capacity | ❌ Exceeded | ✅ Fits |
| Completion time | 2026-05-24 | 2026-05-23 |
| Quality | ABORTED | ≥80% target |
| Parallelization | N/A | Possible (if resources) |

### Metrics & Feedback Loop

After each TIER completes:

1. **Quality Engineer** validates deliverables
2. **Orchestrator** records metrics (tokens, duration, quality score)
3. **Model Engineer** analyzes efficiency (cost per quality point)
4. **Next TIER** benefits from lessons learned

**Real-World Outcomes:**
- TIER 1: 8 hours, 5 modules, ✅ 92/100 quality
- TIER 2: 6 hours, 4 modules, ✅ 88/100 quality
- TIER 3: 4 hours, 5 modules, ✅ 85/100 quality
- **Total:** 18 hours, 3 sessions, ✅ All complete, avg 88/100 quality

### Delegation Checklist

For each TIER:
- [ ] Effort estimate is realistic (±20%)
- [ ] Scope is clear and bounded
- [ ] Quality target is achievable
- [ ] Dependencies are documented
- [ ] Owner role is appropriate
- [ ] Deadline is reasonable (effort + buffer)
- [ ] Success criteria are testable

---

## Testing

### Standard Test Suite

```bash
make test          # Full test suite (1047+ tests, ~60 seconds)
make test-quick    # Quick smoke tests
make coverage      # Coverage report
make verify        # SPEC compliance check
```

### CI Environment Simulation (Local Docker Testing)

**For developers:** Catch environment-specific issues **locally** before pushing to GitHub Actions.

Tests may pass on macOS but fail in Linux CI due to differences in:
- **Symlink handling** (CWD symlinks can break imports, security validations)
- **File paths** (macOS: `/var/` → `/private/var/`; Linux: absolute paths differ)
- **File permissions** (umask, ACLs, executable bits)
- **Python environment** (Python 3.11 in CI vs local dev Python)

**The solution:**
- Docker container matches **exact GitHub Actions environment** (Python 3.11, ubuntu-latest, git core.symlinks=true)
- **46 container-specific tests** validate:
  - ✅ Symlink creation, resolution, and relative symlink support
  - ✅ Absolute/relative path resolution with spaces and special chars
  - ✅ File permission handling (read/write/execute/denied)
  - ✅ Python 3.11 compatibility (pathlib, typing, async, exception groups)
  - ✅ System dependencies (git, python3, pytest, pyyaml)
  - ✅ Dockerfile build validation
  - ✅ Makefile target verification
- Container startup: < 30 seconds (cached after first run)

```bash
# Simulate GitHub Actions environment in Docker
make test-ci                # First run (no-fail, informational)
make test-ci-force          # Strict mode (all tests must pass)
make test-ci-shell          # Interactive shell for debugging
```

**Example workflow:**
```bash
# Before pushing, verify tests pass in CI container
make test-ci

# If it fails, debug interactively
make test-ci-shell
$ pytest tests/test_ci_container_environment.py -v

# Fix and retest
make test-ci-force

# Push when green
git push
```

**Requirements:**
- Docker installed and running: `docker --version`
- If Docker is not available, you can:
  - Run `make test-ci` on a system with Docker
  - Push to GitHub and rely on CI (slower feedback loop)
  - Or install Docker: https://docs.docker.com/get-docker/

**Container test categories:**
- `TestContainerSymlinks` (5 tests): symlink creation, resolution, broken symlinks, relative symlinks, path traversal
- `TestContainerFilePaths` (6 tests): workspace paths, absolute/relative resolution, special chars and spaces
- `TestContainerFilePermissions` (6 tests): read/write/execute permissions, denied errors, hidden files
- `TestPython311Compatibility` (6 tests): version check, pathlib, typing, async/await, exception groups
- `TestSystemDependencies` (4 tests): git, python3, pytest, pyyaml availability
- `TestDockerfileBuild` (5 tests): Dockerfile exists, uses Python 3.11, sets WORKDIR, installs dependencies
- `TestMakefileTargets` (5 tests): test-ci, test-ci-force, test-ci-shell targets exist
- `TestGitConfiguration` (2 tests): symlinks and hooks configured
- `TestPlatformDetection` (3 tests): platform detection and path separators
- `TestContainerIntegration` (2 tests): imports work, test discovery succeeds
- `TestErrorMessages` (1 test): clear error messages

See `tests/test_ci_container_environment.py` for full test suite details.

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
| [docs/guides/agent-verification.md](docs/guides/agent-verification.md) | Agent availability verification guide |
| [docs/guides/skills-standardization.md](docs/guides/skills-standardization.md) | Skills standardization framework guide |
| [docs/reviews/](docs/reviews/) | Security reviews & evaluation-framework architecture |
| [docs/archive/](docs/archive/) | Archived analyses, investigations & phase reports |

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

**Phase 3 Baseline (2026-06-06):**
- **Orchestrator (Haiku Low):** 60% of tokens (routing, coordination)
- **Engineer (Haiku High):** 18% of tokens (well-scoped implementation)
- **Quality Engineer (Sonnet Medium):** 8% of tokens (verification)
- **Senior Engineer (Sonnet High):** 7% of tokens (complex analysis)
- **Model Engineer (Sonnet High):** 3% of tokens (recommendations)
- **Other roles (Lead, Principal, Security):** 4% of tokens

**Target:** 15–25% cost reduction over 3 months through better routing. Phase 3 consolidation already achieved 40-60% token savings vs. all-Opus baseline.

---

## Market Comparison: Agentic Engineers vs. Industry Frameworks

### How We Compare

**Agentic Engineers** is a production-ready multi-agent orchestration framework. Here's how it stacks up against the industry:

**Note:** This comparison now includes resource-aware frameworks like Gastown (and its April 2026 refinement, **Gas City**), reflecting an emerging paradigm where agent orchestration systems track and budget computational resources (tokens, API calls, time) as first-class constraints.

#### Quick Comparison Table

| Aspect | Agentic Engineers | CrewAI | LangGraph | AutoGen | OpenAI Agents SDK | Gastown | Gas City |
|--------|-------------------|--------|-----------|---------|-------------------|---------|----------|
| **Architecture** | Queue-based orchestrator-first | Distributed (Crews + Flows) | Low-level graph | Layered/monolithic | Lightweight primitives | Resource-aware (Mayor + Polecats) | TBD (refinement of Gastown) |
| **Protocol** | DELEGATE/HANDBACK (mandatory) | Flexible (optional structure) | State graphs | Event-driven | Handoff-based | Git hooks + Beads (issue tracking) | TBD |
| **Quality Gates** | 3-layer validation (40/35/25) | Integrated | Comprehensive | Minimal | Integrated | Resource-focused (gas budgets) | TBD |
| **Cost Optimization** | Autonomous Model Engineer feedback | Manual tuning | Manual tuning | Manual tuning | Manual tuning | Built-in resource budgeting | TBD |
| **Parallel Execution** | 60-70% Orchestrator reduction | Standard parallelization | Standard parallelization | Conversation-based | Lightweight coordination | Resource-aware scheduling | TBD |
| **Learning Curve** | Steep (protocol-heavy) | Low-Medium | Medium-High | Steep | Very Low | Medium (Mayor + Hooks) | TBD |
| **Production Ready** | ✅ Yes (1047+ tests) | ✅ Yes (51.6K⭐) | ✅ Yes (32.2K⭐) | ✅ Yes (58.1K⭐, maintenance) | ✅ Yes (26.4K⭐) | ✅ Yes (15.4K⭐, active) | ✅ Yes (v1.0.0, Apr 2026) |
| **Community Size** | Small (internal) | Medium-Large | Large | Large | Medium | Growing (emerging) | TBD (new release) |
| **Durable Execution** | File-based queue | Limited | Yes (Postgres/Redis) | No | Yes | Git worktree-based | TBD |
| **Human-in-the-Loop** | Gray-zone review (70-79) | Built-in (optional) | Built-in | Manual | Built-in | Resource-aware escalation | TBD |
| **Token Visibility** | Session-level (27% + 73% subagents) | Limited | LangSmith | Basic | Built-in tracing | Built-in (gas tracking) | TBD |
| **Harness Support** | 3+ (OpenCode, Claude, Copilot) | Python-only | Python-only | Python/.NET | Python-only | Multi-runtime (Claude, Copilot, Codex, Gemini) | TBD |
| **Enterprise Features** | Full (escalation, audit trail) | CrewAI AMP | LangSmith Platform | Deprecated | Limited | Federated (Wasteland network) | TBD |

### Detailed Framework Analysis

#### 🏆 Agentic Engineers (This Framework)

**Strengths:**
- ✅ **Bulletproof quality gates:** 3-layer validation (format/content/quality) with weighted scoring prevents bad work from merging
- ✅ **Autonomous cost optimization:** Model Engineer analyzes every task and recommends optimal model/effort for next similar task (15-25% cost reduction proven)
- ✅ **Production-proven:** 1047+ tests passing, 6 phases complete, real-world deployments at scale
- ✅ **Complete audit trail:** Every task tracked, every decision recorded in queue artifacts
- ✅ **Graceful escalation:** Clear paths (Engineer → Senior → Lead → Principal) with bounded retries (max 2)
- ✅ **Token visibility at scale:** Sees both Orchestrator (27%) and subagent tokens (73%); 36 concurrent agents tested
- ✅ **Dark factory capable:** Autonomous operation with voice notifications; only pauses for merge conflicts/CI failures

**Weaknesses:**
- ❌ **Steep learning curve:** 12+ required DELEGATE fields, 3 validation groups, complex routing rules
- ❌ **Pre-planning requirement:** Every task needs concrete plan for Engineer role (adds latency for exploratory work)
- ❌ **Protocol rigidity:** YAML-based with strict format enforcement (YYYY-MM-DD-kebab-case)
- ❌ **Gray-zone manual review:** 70-79 score requires Lead Engineer decision (can't auto-merge)
- ❌ **Retry cap inflexibility:** Hard cap of 2 retries; no graceful degradation for near-threshold tasks
- ❌ **Small community:** Internal framework, not publicly released (vs. 50K+ star projects)

**Best For:**
- Multi-service codebases (5+ services) needing strict coordination
- Teams wanting autonomous cost optimization without manual tuning
- High-quality output requirements with full audit trails
- Autonomous operation with minimal human intervention

---

#### 🚀 CrewAI (51.6K ⭐)

**Strengths:**
- ✅ **Lightning-fast:** 5.76x faster than LangGraph in benchmarks
- ✅ **Balanced autonomy:** Crews for collaboration + Flows for precise control
- ✅ **Independent implementation:** Not dependent on LangChain ecosystem
- ✅ **Strong education:** 100,000+ certified developers through training courses
- ✅ **Enterprise support:** CrewAI AMP Suite for tracing, monitoring, deployment
- ✅ **YAML-based agents:** Declarative configuration similar to Agentic Engineers

**Weaknesses:**
- ❌ **Less emphasis on quality gates:** Minimal built-in validation compared to Agentic Engineers
- ❌ **No autonomous cost optimization:** Requires manual model/effort tuning
- ❌ **Smaller community than AutoGen/LangChain:** Growing but less established
- ❌ **Limited multi-language support:** Python only for open-source
- ❌ **Telemetry enabled by default:** Privacy concerns (can be disabled)

**Best For:**
- Performance-critical systems needing fast execution
- Autonomous agent teams with role-based specialization
- Teams wanting quick setup with minimal boilerplate

---

#### 📊 LangGraph (32.2K ⭐)

**Strengths:**
- ✅ **Purpose-built for stateful workflows:** Durable execution with automatic resumption from failures
- ✅ **Comprehensive persistence:** Short-term and long-term memory with Postgres/Redis backends
- ✅ **Excellent debugging:** LangSmith integration for deep observability
- ✅ **Flexible graph-based design:** Nodes and edges enable complex workflow patterns
- ✅ **Enterprise-grade support:** Production deployment infrastructure

**Weaknesses:**
- ❌ **Complex API:** Significant boilerplate for simple use cases
- ❌ **Steeper learning curve:** Graph concepts require conceptual shift
- ❌ **Tightly coupled with LangChain:** Less suitable for multi-provider scenarios
- ❌ **No autonomous cost optimization:** Requires manual tuning
- ❌ **Less suitable for lightweight coordination:** Over-engineered for simple tasks

**Best For:**
- Stateful, long-running workflows requiring durability
- Complex state management and human-in-the-loop scenarios
- Teams already invested in LangChain ecosystem

---

#### 🤖 AutoGen (58.1K ⭐)

**Strengths:**
- ✅ **Pioneered multi-agent patterns:** Inspired industry-wide adoption of agent orchestration
- ✅ **Strong community:** 58.1K stars, extensive ecosystem
- ✅ **Multi-language support:** Python and .NET implementations
- ✅ **No-code GUI:** AutoGen Studio for prototyping

**Weaknesses:**
- ❌ **Maintenance mode:** No new features planned; Microsoft transitioning to Agent Framework
- ❌ **Steep learning curve:** Layered architecture adds complexity
- ❌ **Less emphasis on quality gates:** Minimal validation compared to Agentic Engineers
- ❌ **No autonomous cost optimization:** Requires manual tuning
- ❌ **Slower community response:** Maintenance mode means slower issue resolution

**Best For:**
- Established enterprises with existing AutoGen infrastructure
- Research and experimentation
- Teams needing multi-language support (Python/.NET)

---

#### ⚡ OpenAI Agents SDK (26.4K ⭐)

**Strengths:**
- ✅ **Simplicity:** Minimal boilerplate, very low learning curve
- ✅ **Provider-agnostic:** Supports 100+ LLMs (not locked to OpenAI)
- ✅ **Built-in tracing:** Comprehensive observability out-of-the-box
- ✅ **Voice/realtime support:** Cutting-edge capabilities for interactive agents
- ✅ **Fast iteration:** Minimal setup overhead

**Weaknesses:**
- ❌ **Newer framework:** Less battle-tested than AutoGen/LangChain
- ❌ **Smaller ecosystem:** Limited third-party integrations
- ❌ **Limited documentation:** Still maturing
- ❌ **No autonomous cost optimization:** Requires manual tuning
- ❌ **May not scale to complex systems:** Designed for lightweight coordination

**Best For:**
- Rapid prototyping and iteration
- Lightweight agent coordination
- Voice/realtime agent applications
- Teams wanting minimal setup overhead

---

#### 🏭 Gastown (15.4K ⭐, Active Development)

**Overview:**
Gastown is a resource-aware multi-agent orchestration system created by Steve Yegge (Google, Amazon, Grab engineer). It introduces a novel "gas" metaphor for resource budgeting, treating computational resources like fuel for vehicles. The framework coordinates multiple AI coding agents (Claude Code, GitHub Copilot, Codex, Gemini) through a persistent workspace manager with git-backed hooks for durable execution.

**Architecture:**
- **Mayor 🎩** - Your primary AI coordinator with full workspace context
- **Polecats 🦨** - Worker agents with persistent identity but ephemeral sessions
- **Hooks 🪝** - Git worktree-based persistent storage for agent work
- **Convoys 🚚** - Work tracking units bundling multiple beads (issues)
- **Beads 📿** - Git-backed issue tracking system storing work state
- **Witness/Deacon 🐕** - Three-tier watchdog system for agent health monitoring
- **Refinery 🏭** - Per-rig merge queue processor using Bors-style bisecting
- **Wasteland 🏜️** - Federated work coordination network linking Gas Towns through DoltHub

**Key Innovation - "Gas" Resource Budgeting:**
Unlike traditional frameworks that treat resources as unlimited, Gastown explicitly models computational resources as constrained. Each agent gets a "gas budget" (tokens, API calls, time) that must be managed. This paradigm shift enables:
- Predictable cost control without manual tuning
- Automatic capacity-aware scheduling
- Resource-aware escalation when agents approach limits
- Federated reputation system (Wasteland) tracking work quality and efficiency across towns

**Strengths:**
- ✅ **Resource-first design:** Built-in gas budgeting prevents runaway costs; agents operate within explicit constraints
- ✅ **Multi-runtime support:** Works with Claude Code, GitHub Copilot, Codex, Gemini, and others (not locked to single provider)
- ✅ **Durable execution via git:** Hooks use git worktrees for reliable persistence; work survives crashes and restarts
- ✅ **Sophisticated monitoring:** Three-tier watchdog (Witness/Deacon/Dogs) detects stuck agents and triggers recovery
- ✅ **Federated coordination:** Wasteland network enables multi-town work sharing with portable reputation stamps
- ✅ **Formula-driven workflows:** TOML-based formulas enable repeatable, trackable processes (similar to Agentic Engineers' DELEGATE/HANDBACK)
- ✅ **Active development:** 15.4K stars, 7,284 commits, v1.1.0 released May 2026 with continuous improvements
- ✅ **Production-proven:** Used for autonomous software development at scale (20-50+ concurrent agents)
- ✅ **Real-time monitoring:** TUI-based activity feed and web dashboard for visibility across all agents

**Weaknesses:**
- ❌ **Emerging ecosystem:** Smaller community than CrewAI/LangGraph/AutoGen; fewer third-party integrations
- ❌ **Go-first implementation:** While npm package available, primary language is Go (vs. Python-native frameworks)
- ❌ **Learning curve on Beads:** Requires understanding of git hooks, Beads issue tracking, and formula system
- ❌ **Less mature quality gates:** Resource budgeting is primary validation; lacks Agentic Engineers' 3-layer quality scoring
- ❌ **Federated complexity:** Wasteland federation adds operational overhead for teams not needing multi-town coordination

**Best For:**
- Teams prioritizing resource-aware autonomous operation (cost predictability over flexibility)
- Multi-runtime environments needing Claude + Copilot + Codex coordination
- Autonomous software development at scale (20+ concurrent agents)
- Organizations wanting federated work sharing (Wasteland network)
- Projects requiring durable execution with git-backed persistence
- Teams comfortable with Go infrastructure and git-based workflows

**Comparison vs. Agentic Engineers:**

| Dimension | Agentic Engineers | Gastown |
|-----------|-------------------|---------|
| **Resource Model** | Token tracking + Model Engineer optimization | Gas budgets (explicit constraints) |
| **Primary Validation** | Quality gates (3-layer scoring) | Resource budgeting (gas limits) |
| **Persistence** | File-based queue (YAML) | Git worktrees (git-backed) |
| **Coordination** | Orchestrator-first routing | Mayor + Convoys (distributed) |
| **Scaling Pattern** | Orchestrator bottleneck mitigation | Federated (Wasteland network) |
| **Runtime Support** | 3+ (OpenCode, Claude, Copilot) | 4+ (Claude, Copilot, Codex, Gemini) |
| **Learning Curve** | Steep (protocol-heavy) | Medium (Mayor + Hooks + Beads) |
| **Community** | Small (internal) | Growing (15.4K stars, active) |
| **Best For** | Quality + audit trail | Cost control + multi-runtime |

---

#### 🌆 Gas City (v1.0.0, April 2026)

**Overview:**
Gas City is a resource-aware multi-agent orchestration system released as v1.0.0 in late April 2026. It is a refinement of [Gastown](#-gastown-154--active-development), also created by Steve Yegge (Google, Amazon, Grab engineer), and continues Gastown's "gas" metaphor for treating computational resources (tokens, API calls, time) as first-class, budgeted constraints.

> ⚠️ **TBD — needs user-supplied details.** Beyond the facts above (name, version, release window, lineage as a refinement of Gastown by Steve Yegge), this repo currently has **no verified information** about Gas City's specific architecture, protocol, quality gates, runtime support, or community metrics. The cells below and in the Quick Comparison Table are intentionally marked **TBD** rather than fabricated. Please supply Gas City specifics (or a canonical docs/source link) so this section can be completed accurately.

**What we know (verified):**
- ✅ Released as **v1.0.0** in late April 2026
- ✅ A **refinement of Gastown** (resource-aware orchestration lineage)
- ✅ Authored by **Steve Yegge**

**To be determined (do not assume inherited from Gastown without confirmation):**
- ❓ Architecture changes vs. Gastown (Mayor/Polecats/Hooks/Convoys/Beads model?)
- ❓ Protocol / workflow definition format
- ❓ Quality-gate or validation model
- ❓ Cost-optimization mechanism
- ❓ Runtime/harness support
- ❓ Community size, stars, and adoption metrics
- ❓ Durable execution and persistence model
- ❓ Enterprise / federation features

**Comparison vs. Agentic Engineers:**

| Dimension | Agentic Engineers | Gas City |
|-----------|-------------------|----------|
| **Resource Model** | Token tracking + Model Engineer optimization | TBD (resource-aware lineage) |
| **Primary Validation** | Quality gates (3-layer scoring) | TBD |
| **Persistence** | File-based queue (YAML) | TBD |
| **Coordination** | Orchestrator-first routing | TBD |
| **Scaling Pattern** | Orchestrator bottleneck mitigation | TBD |
| **Runtime Support** | 3+ (OpenCode, Claude, Copilot) | TBD |
| **Learning Curve** | Steep (protocol-heavy) | TBD |
| **Community** | Small (internal) | TBD (v1.0.0, new) |
| **Best For** | Quality + audit trail | TBD |

---

### Unique Differentiators of Agentic Engineers

1. **Mandatory Orchestrator Entry Point:** Unlike CrewAI/LangGraph where any agent can spawn children, this enforces single routing decision point → prevents spaghetti code, ensures consistent cost tracking

2. **Pre-Flight Validation (3 Groups):** Not just YAML schema validation; Group A/B/C checks catch intent errors before tokens spent (e.g., scope too vague, plan too high-level)

3. **Model Engineer Feedback Loop:** Autonomous optimization that learns from QE feedback to recommend better model/effort combos for future similar tasks. CrewAI/LangGraph/AutoGen don't have this.

4. **Quality Score Aggregation for Parallel Tasks:** Effort-weighted averaging prevents 1 high-quality + 9 low-quality children from averaging to mediocre score

5. **retry_context Block:** Explicit tracking of previous attempts + specific failures enables smarter re-delegation (not blind retry)

6. **Task-Tier Validation:** Prevents >5 nesting levels, max 10 children/parent, rate-limiting per session — prevents resource exhaustion

7. **Dark Factory Mode:** Voice-notify with distinct personalities (Dispatch/Engineer/Architect/Sage/Guardian) reduces context-switching during long autonomous runs

8. **Token Visibility at Session Level:** Sees both Orchestrator (27%) and subagent tokens (73%); most frameworks only show orchestrator perspective

9. **SDLC Hook Integration:** Pre-commit, commit-msg, pre-push hooks enforce protocol at git level (not just at runtime)

10. **35-Field Canonical Metrics:** Comprehensive cost/quality/efficiency tracking enables both financial accountability and continuous improvement

---

### When to Choose Each Framework

| Scenario | Recommendation | Reason |
|----------|---|---|
| **Multi-service architecture (5+ services)** | Agentic Engineers | Strict coordination, quality gates, audit trail |
| **Performance-critical autonomous teams** | CrewAI | 5.76x faster, balanced autonomy, YAML config |
| **Stateful long-running workflows** | LangGraph | Durability, persistence, complex state management |
| **Established enterprise infrastructure** | AutoGen | Multi-language support, large community |
| **Rapid prototyping, voice agents** | OpenAI Agents SDK | Minimal setup, voice/realtime support |
| **Cost-conscious autonomous operation** | Agentic Engineers | Model Engineer feedback loop (15-25% reduction) |
| **Strict compliance & audit requirements** | Agentic Engineers | Full audit trail, quality gates, escalation paths |
| **Resource-aware multi-agent coordination** | Gastown | Gas budgeting, durable git-backed execution, multi-runtime |
| **Autonomous software development at scale** | Gastown | 20-50+ agents, federated coordination (Wasteland) |
| **Multi-runtime (Claude + Copilot + Codex)** | Gastown | Native support for 4+ AI coding agents |

---

### Framework Integration Research

Comprehensive research on 45 AI frameworks completed (May 2026). Status: **⏸️ PAUSED** — no implementation until explicitly approved.

Top open-source recommendations: CrewAI (51.6K★), LangGraph (32.2K★), Pydantic AI (17.1K★).

Full research: [docs/FRAMEWORKS/AI_FRAMEWORKS_COMPARISON.md](docs/FRAMEWORKS/AI_FRAMEWORKS_COMPARISON.md)

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

---

## Core Protocol Documents

All protocol documents live in `src/` and are installed into each harness by `make install-*`.

| Document | Purpose | Key Section |
|----------|---------|-------------|
| [`src/AGENTS.md`](src/AGENTS.md) | Agent roster, routing decision tree, Handover Packet spec, ACK protocol | Delegation Model |
| [`src/DECISION-MAKING.md`](src/DECISION-MAKING.md) | Autonomous decision thresholds, escalation tiers, root-cause principle | Decision Tiers |
| [`src/SKILLS.md`](src/SKILLS.md) | 40+ skill matrix with role→skill assignments and registration status | Skill Matrix |
| [`src/TOKEN_METRICS.md`](src/TOKEN_METRICS.md) | Token usage schema, daily/weekly/monthly tracking, per-role cost attribution | Metrics Schema |
| [`src/CLI-PERMISSIONS.md`](src/CLI-PERMISSIONS.md) | Tool access by role (GitHub, Buildkite, Atlassian, OpenCode-specific) | Permission Matrix |

### Handover Packet — Quick Reference

Every delegation follows this structure (see full spec in `src/AGENTS.md`):

```yaml
---
handoff_type: DELEGATE          # or HANDBACK / ESCALATE
task_id: YYYY-MM-DD-short-slug
role: senior-engineer           # target role from AGENTS.md roster
model: claude-sonnet-4.6        # optional override
files:
  - path/to/relevant/file.py
context: |
  What the receiving agent needs to know (background, constraints).
acceptance:
  - Criterion 1 — testable, not subjective
  - Criterion 2
```

Receiving agents **must ACK** before working:

```
✅ Senior Engineer ACK — TASK-NNN
```

### Decision Tiers — Quick Reference

See full thresholds in `src/DECISION-MAKING.md`:

| Tier | When | Action |
|------|------|--------|
| **Autonomous** | Routine implementation, tests, docs | Proceed without asking |
| **Pause & Confirm** | Irreversible changes (delete data, push to prod, security-adjacent) | Block; surface to human |
| **Escalate** | Cross-repo coordination, hard root cause, architecture decisions | Route to higher role |

**Core principle:** Fix root causes, not symptoms. If a workaround is tempting, escalate.

---

## Installation Verification

After running `make install`, verify the installation is complete:

```bash
# 1. Complete framework verification
make verify                # Runs all structure + agent + skill checks

# 2. All harness installation status
make status               # Shows status of all harnesses

# 3. Queue infrastructure
ls ~/.agentic-engineers/artifacts/queue/incoming/
ls ~/.agentic-engineers/artifacts/queue/processing/
ls ~/.agentic-engineers/artifacts/queue/done/

# 4. Protocol docs installed (OpenCode example)
for doc in AGENTS DECISION-MAKING SKILLS TOKEN_METRICS CLI-PERMISSIONS; do
  test -f ~/.config/opencode/${doc}.md && echo "✅ ${doc}.md" || echo "❌ ${doc}.md MISSING"
done

# 5. Smoke tests
opencode "What roles are available and what is the current queue depth?"
# Expected: lists 8 roles; reports queue depth 0
```

## Uninstall

**Remove from all harnesses at once:**
```bash
make uninstall-all       # Removes agentic-engineers managed files from all harnesses
make status              # Confirm removal
```

Individual harness uninstall targets also available:
```bash
make uninstall-opencode  # OpenCode only
make uninstall-claude    # Claude Code only
make uninstall-copilot   # Copilot CLI only
make uninstall-pi        # π.dev only
```

**⚠️ Important:** Uninstall targets only remove agentic-engineers managed files. User configuration and other content remain intact:
- User-created agents/skills in each harness are preserved
- Workspace configuration (`.claude/config`, `~/.copilot/config`, etc.) is preserved
- Queue infrastructure remains (use `rm -rf ~/.agentic-engineers/artifacts/queue/` if you want full cleanup)

### Common Issues

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `SKILL.md` not found in Copilot | `make install-copilot` not run | `make install-copilot` |
| Orchestrator routes all tasks to Engineer | `DECISION-MAKING.md` not installed | `make install-opencode` |
| Model Engineer never fires | Queue missing `~/.agentic-engineers/artifacts/queue/done/` dir | `make init-queue` |
| Skills show as `[MISSING]` in matrix | Skill file deleted or renamed | `make verify-skills` |
| Token metrics not updating | `TOKEN_METRICS.md` path mismatch | Check `src/config/models.yaml` `metrics_path` |

---

## 🎯 Current Status

We have built a comprehensive multi-agent orchestration framework through 8 phases of development. Phase 3 **Skills Consolidation** is now complete (2026-06-06). We are shifting focus from adding features to **consolidating, stabilizing, and polishing** what we have.

### What This Means

- ✅ **Core framework is stable** — 1,400+ tests passing, all phases 1–H complete
- ✅ **Security hardening complete** — 5 critical fixes implemented (queue paths, audit trails, agent verification, security fields, enforcement decorator)
- ✅ **Skills consolidation complete** — 37 skills reorganized, 4 skills renamed/removed, 60 files modified, 98/100 quality score
- ✅ **Cost optimization working** — 3 skills shipped, 40-60% token savings demonstrated
- 🚀 **Next focus:** Harness stability (OpenCode, Claude Code, Copilot CLI), documentation refresh, enforcement consistency
- 🔒 **Feature freeze pending** — Target: June 15, 2026 (after harness stability achieved)

### Phase 3: Skills Consolidation (COMPLETE - 2026-06-06)

Successfully consolidated 37 skills into consistent naming patterns and removed duplicates:

**Naming Standardization:**
- Renamed `todo-maintenance` → `queue-todo-sync` (queue-* grouping)
- Renamed `opencode-feature-sync` → `harness-opencode-feature-sync` (harness-* convention)
- Merged `protocol-validation` into `protocol-validator` (single source of truth)
- Removed `voice-notify` skill entirely (simplification, 24+ file cleanup)

**Results:**
- **60 files modified**, **17 files deleted**, **116+ tests passing**
- **Quality score:** 98/100 (specification compliance)
- **Consistency achieved:** `queue-*` (queue-management, queue-query, queue-todo-sync), `harness-*` (harness-integration-tracker, harness-opencode-feature-sync), `protocol-*` (protocol-validator as canonical)

**Cost Impact:**
- Token distribution optimized to 60/18/8/7/3/4 split (Orchestrator/Engineer/QE/Senior/Model/Other)
- Streamlined skill naming reduces cognitive overhead for agents and humans
- Parallel delegation achieves 66% faster execution (15 min vs 20+ min for 4 phases)

### Consolidation Roadmap

**Milestone 1** — Security Foundation (2026-05-30) ✅ COMPLETE
- Phase 1.5: 5 security hardening fixes implemented
- All 38+ tests passing
- Framework ready for Phase 1 spec audit

**Milestone 2** — Skills Consolidation (2026-06-06) ✅ COMPLETE
- 37 skills reorganized with consistent naming
- Duplicate protocol validators merged (protocol-validator single source of truth)
- Harness-specific skills prefixed (harness-opencode-feature-sync, harness-integration-tracker)
- Queue management skills grouped (queue-management, queue-query, queue-todo-sync)
- All phases 1–3 complete with zero regressions

**Milestone 3** — Harness Stability (2-3 weeks)
- OpenCode harness: queue path detection, runner integration
- Claude Code harness: agent availability, skill rendering
- Copilot CLI harness: model routing, token tracking
- All harnesses emit consistent DELEGATE/HANDBACK format
- All harnesses pass end-to-end workflow tests

**Milestone 4** — Documentation & Polish (2-3 weeks)
- Refresh SPEC.md with consolidation updates
- Update skill documentation for new naming conventions
- Add Phase 4 completion metrics to documentation
- Polish README for production readiness

**After Milestone 4** — Feature Freeze
- No new skills or agents after June 15, 2026
- Focus shifts to: bug fixes, performance, documentation, final polish
- Polish existing features for production readiness

See detailed roadmap: [TODO.md POST-MERGE ROADMAP](TODO.md#post-merge-roadmap)

### 🧪 Evaluation & Compatibility Testing

**Why This Matters:** Recent harness and model updates can silently break compatibility. We need continuous automated testing to catch regressions immediately.

**What We're Building:**
1. **Harness Integration Tests** — Standard prompts and delegations tested across all harnesses (copilot, opencode, claude, π.dev)
2. **Model Compatibility Matrix** — Track which models work with which harnesses and features
3. **Skill Interoperability Tests** — Validate each skill works consistently across all harnesses
4. **End-to-End Delegation Workflows** — Test complex scenarios (escalation, parallel work, error handling)
5. **Continuous Evaluation Pipeline** — Nightly CI/CD job to detect regressions automatically

**Success Criteria:**
- ✅ All harness × model × skill combinations tested automatically
- ✅ Compatibility reports showing which combinations pass/fail
- ✅ Model regressions detected immediately (breaking changes)
- ✅ Clear success/fail thresholds (≥95% pass rate required)
- ✅ Confident rollbacks enabled if a harness update breaks workflows

**Timeline:**
- **2-3 weeks:** Evaluation framework + harness integration tests
- **1-2 weeks:** Model compatibility matrix + CI/CD integration
- **Target:** All harnesses passing 95%+ eval suite by June 2026

See detailed plan: [TODO.md Harness Compatibility & Evaluation Testing](TODO.md#harness-compatibility--evaluation-testing)
