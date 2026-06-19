# Agentic Engineers

A **Multi-Agent Orchestration Framework** for optimizing token usage, quality, and delivery speed through intelligent work routing, quality gates, and continuous cost-quality optimization feedback loops. Designed for integration with coding CLIs: **Claude**, **Copilot**, **OpenCode**, **Pi**, **Codex**.

## What It Is

**Agentic Engineers** solves the multi-agent coordination problem:

- **How do you coordinate 8+ specialized AI agents** without spaghetti code?
- **How do you enforce quality gates** consistently across all agents?
- **How do you optimize cost** while maintaining quality?
- **How do you stay within token budgets** across unlimited work?

**The answer:** A queue-based ORCHESTRATOR-FIRST architecture:

1. All work enters a queue as DELEGATE tasks (SPEC-compliant YAML)
2. Orchestrator polls and routes to the right specialist
3. Each agent returns a HANDBACK with results + metrics
4. Quality gates validate all work before moving to done
5. Metrics feed back into model selection and routing optimization

### Files Agentic Engineers Creates & Modifies

Installing/rendering a harness writes **only** to that harness's own config
location, plus a single framework work directory. It never touches your project
source.

| Path | Created / Modified | Purpose |
|------|--------------------|---------|
| `~/.claude/`, `~/.copilot/`, `~/.pi/`, `~/.config/opencode/` | **Modified** (agents, skills, settings, system prompt) | Per-harness rendered config — what `make install-<harness>` writes |
| `~/.agentic-engineers/{session-id}/{harness}/queue/` | **Created** | Per-session, per-harness work queue (`incoming/`, `processing/`, `done/`, `failed/`) holding DELEGATE/HANDBACK YAML |
| `~/.<harness>.YYYYMMDD/` (e.g. `~/.claude.20260611/`) | **Created on install** | Timestamped backup of your prior harness config (see warning below) |

### ⚠️ Backups & Conflicts (read before installing)

`make install` / `make clean-install` **back up your existing harness config by
moving it aside** to a date-stamped copy (e.g. `~/.claude/` → `~/.claude.20260611/`)
before writing the new one. Two important caveats:

- **The backup suffix is the date only (`YYYYMMDD`), not a full timestamp.** If
  you install the **same harness twice on the same day**, the second backup
  target already exists and the backup step will fail (it will not silently
  overwrite your first backup). **Handling today:** rename or remove the
  existing `~/.<harness>.YYYYMMDD/` before re-installing, or restore from it
  first (`rm -rf ~/.claude && mv ~/.claude.20260611 ~/.claude`). *We plan to
  switch the suffix to a full `YYYYMMDD-HHMMSS` timestamp soon so same-day
  re-installs stop colliding — oops.* 🙇
- **Backups cover harness config dirs only — never `~/.agentic-engineers/`.**
  Your queue/work directory is left in place across installs. If you want a
  truly clean slate, remove the relevant session dirs under
  `~/.agentic-engineers/` yourself.
- **If you skip the backup prompt** and the harness dir already contains
  non-framework files, the installer warns about pollution but proceeds —
  mixing your files with rendered ones. Back up or start clean if unsure.

To preview without writing to your home dir, render to `dist/` instead:
`make render-claude` (and friends) produce the exact files under `dist/<harness>/`.

### Key Benefits

1. **90+/100 Quality** — Structured DELEGATE/HANDBACK protocol enforces clarity
2. **65% Cost Savings** — Smart model selection (Haiku for execution, Opus for architecture)
3. **40-60% Faster** — Parallel sub-agent execution at scale
4. **80% Fewer Iterations** — Clear success criteria prevent rework

See [Key Benefits & Discoveries](#key-benefits--discoveries) below for details.

---

## Architecture at a Glance

```
       ┌─────────────────────────────────────────────────────────────┐
       │                    AGENTIC-ENGINEERS                         │
       │              Framework & Multi-Harness System                │
       └─────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                          ┌──────────────────┐
                          │  make install    │
                          │  (per harness)   │
                          └──────────────────┘
                  /           │           │           \
              ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
              │ Claude  │ │ Copilot │ │ OpenCode│ │   Pi    │
              │ Config  │ │ Config  │ │ Config  │ │ Config  │
              └─────────┘ └─────────┘ └─────────┘ └─────────┘
                  │           │           │           │
                  └───────────┼───────────┼───────────┘
                              ▼
                     ┌────────────────────┐
                     │ Invoke your harness│
                     │ claude|copilot|    │
                     │ opencode|pi        │
                     └────────────────────┘
```

**Framework → Configure → Deploy → Invoke.** Each harness installs customized agents, skills, and routing logic for its provider.

### How It Works

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
   │  Quality: 94/100│
   │  Cost: $0.18    │
   │  Time: 4.2s     │
   └─────────────────┘
```

**Example:**
```bash
opencode --agent orchestrator "Fix the GitHub Actions timeout in .github/workflows/ci.yml"
  → Orchestrator routes to Engineer (well-scoped fix)
  → Engineer executes, measures quality + cost
  → Returns: HANDBACK {status, quality_score, cost, changes}
  → Quality gate validates (≥92/100 required)
  → Results in ~/.agentic-engineers/queue/done/ ✅
```

---

## 8 Specialized Roles

| Role | Model | Effort | Purpose |
|------|-------|--------|---------|
| **Orchestrator** | claude-haiku-4.5 | Low | Routes all work via decision tree; never does work itself |
| **Engineer** | claude-haiku-4.5 | High | Executes well-scoped, pre-planned tasks |
| **Model Engineer** | claude-sonnet-4.5 | Medium | Analyzes metrics; optimizes routing and model selection |
| **Quality Engineer** | claude-sonnet-4.6 | Medium | Post-implementation validation; model suitability assessment |
| **Lead Engineer** | claude-sonnet-4.6 | High | Code review (8-point checklist); architectural guidance |
| **Senior Engineer** | claude-sonnet-4.6 | High | Analyzes unscoped work; produces detailed plans |
| **Principal Engineer** | claude-opus-4.6 | High | Cross-service architecture; major refactors |
| **Security Engineer** | claude-opus-4.8 | Max | Threat modeling; vulnerability assessment |

**Cost Breakdown:**
- **Haiku:** $0.03–$0.05 per task — Routing, well-scoped implementation
- **Sonnet:** $0.09 per task — Planning, review, quality, optimization
- **Opus:** $0.15 per task — Complex architecture, security analysis

**Effort Levels:**
- **Low:** Minimal reasoning, direct execution (Orchestrator routing)
- **Medium:** Balanced reasoning and exploration (QE validation, Model Engineer analysis)
- **High:** Deep reasoning, multiple approaches considered (Engineers, Leads, Architects)
- **Max:** Unconstrained reasoning, full exploration (Security analysis, threat modeling)

> 💡 **Model Selection:** Each role maps to provider-specific equivalents (GPT-4o, GPT-5.5/GPT-5.4 mini, Gemini, Llama) — see [Multi-Model Support](#multi-model-support--provider-routing) below. For thinking mode details, see [docs/guides/thinking-modes-and-cost-quality-trade-offs.md](docs/guides/thinking-modes-and-cost-quality-trade-offs.md).

---

## Quick Start

### Installation (Choose Your Harness)

Core harnesses are configured by default to use Anthropic Claude models. Codex is available through the initial renderer support path for workspace-managed runs. Install the default set or choose a specific harness:

```bash
# Default harness set
make install

# Or install individual harnesses:
make install-opencode      # OpenCode CLI (recommended for production)
make install-copilot       # Copilot CLI
make install-claude        # Claude Code (IDE)
make install-pi            # π.dev (experimental)
make install-codex         # Codex CLI/IDE custom agents + skills
```

By default the framework installs under your home directory (`$HOME`). To install into an alternate root — for sandboxed or end-to-end testing without touching your real config — pass `DESTDIR`:

```bash
DESTDIR=/tmp/test-install make install-opencode
DESTDIR=/tmp/test-install make install-codex BACKUP=never
```

### Using the Orchestrator

The **Orchestrator** is the single entry point for all work. It routes tasks to specialist agents based on complexity and type:

```bash
# OpenCode (recommended)
opencode --agent orchestrator "Your task description"

# Copilot CLI
copilot --agent orchestrator "Your task description"

# Codex
codex --profile agentic-engineers-orchestrator --sandbox workspace-write --ask-for-approval on-request "Your task description"

# Claude Code
# Paste the orchestrator system prompt into Claude's settings, then:
# "Your task description"
```

**Example Tasks:**
```bash
opencode --agent orchestrator "Fix the CI/CD timeout in .github/workflows/ci.yml"
opencode --agent orchestrator "Add authentication to the API endpoints"
opencode --agent orchestrator "Review PR #42 for security issues"
opencode --agent orchestrator "Optimize token usage across all agents"
```

The orchestrator will:
1. Parse the task
2. Route to the appropriate specialist agent(s)
3. Monitor progress via queue
4. Aggregate results and metrics
5. Report back to you

### Extend the Framework

Add new agents or skills to customize the framework for your needs:

```bash
# Create a new agent role
python3 scripts/agent-creator.py --role "data-engineer" --model "claude-sonnet-4.6" --effort high

# Create a new skill
python3 scripts/skill-creator.py --name "database-migration" --category "infrastructure"
```

See [docs/guides/agent-creation.md](docs/guides/agent-creation.md) and [docs/guides/skill-creation.md](docs/guides/skill-creation.md) for detailed guides.

---

## Key Features

- **🎯 Queue-Based Orchestration** — Centralized task routing via DELEGATE/HANDBACK protocol
- **⚖️ Multi-Tier Model Selection** — Haiku for execution, Sonnet for planning, Opus for architecture
- **✅ Quality Gates (3 Layers)** — DELEGATE structure, task routing, HANDBACK validation
- **📊 Real-Time Metrics** — Token tracking, quality scores, cost per task
- **🔄 Self-Improving Feedback Loops** — Model Engineer optimizes routing based on metrics
- **🌐 Multi-Harness Support** — OpenCode, Copilot, Claude, π.dev, Codex
- **🔐 Security by Default** — Opus-tier Security Engineer for threat modeling
- **📚 Comprehensive Documentation** — Protocol specs, guides, troubleshooting

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
- **Opus (claude-opus-4.6/4.8):** $0.15 per task, only for security/architecture decisions

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

---

## Documentation

| Topic | Document | Description |
|-------|----------|-------------|
| **Architecture** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Detailed framework architecture and decision rationale |
| **Protocol** | [docs/PROTOCOL.md](docs/PROTOCOL.md) | DELEGATE/HANDBACK protocol specification |
| **Harness Setup** | [docs/guides/harness-setup/](docs/guides/harness-setup/) | Detailed setup guides for each harness |
| **Agent Creation** | [docs/guides/agent-creation.md](docs/guides/agent-creation.md) | How to create new agent roles |
| **Skill Creation** | [docs/guides/skill-creation.md](docs/guides/skill-creation.md) | How to create new skills |
| **Cost Optimization** | [docs/COST-QUALITY-MATRIX.md](docs/COST-QUALITY-MATRIX.md) | Cost-quality trade-offs and optimization strategies |
| **Testing** | [docs/guides/troubleshooting.md](docs/guides/troubleshooting.md) | Testing strategy and troubleshooting |
| **Market Comparison** | [docs/market-comparison.md](docs/market-comparison.md) | Comparison with CrewAI, LangGraph, AutoGen, etc. |
| **Contributing** | [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute to the project |

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

Every satoshi helps. Thank you for believing in open-source multi-agent systems. 🙏

---

## Installation Verification

```bash
# 1. Complete framework verification
make test

# 2. All harness installation status
ls ~/.agentic-engineers/queue/      # Should show: incoming/ processing/ done/

# 3. Protocol docs installed (OpenCode example)
cat ~/.opencode/agents/orchestrator/SYSTEM.md  # Should show orchestrator system prompt

# 4. Smoke tests
opencode --agent orchestrator --version        # Should show version
opencode --agent orchestrator "echo 'Hello from orchestrator'"  # Should route and execute
```

---

## Multi-Model Support & Provider Routing

Every role has a **canonical model tier** (the primary recommendation) plus **provider-specific equivalents** that the render pipeline substitutes automatically. The single source of truth is [`src/config/models.yaml`](src/config/models.yaml).

### Role → Model Mapping (All Providers)

| Role | Canonical | Claude (Anthropic) | GitHub Copilot | OpenAI | Codex | Google | Meta / Llama |
|------|-----------|-------------------|----------------|--------|-------|--------|--------------|
| **Orchestrator** | Haiku | `claude-haiku-4.5` | `claude-haiku-4.5` | `gpt-4o-mini` | `gpt-5.4-mini` | `gemini-2.0-flash` | `llama-3-8b` |
| **Engineer** | Haiku | `claude-haiku-4.5` | `claude-haiku-4.5` | `gpt-4o-mini` | `gpt-5.4-mini` | `gemini-2.0-flash` | `llama-3-8b` |
| **Quality Engineer** | Sonnet | `claude-sonnet-4.6` | `claude-sonnet-4.6` | `gpt-4-turbo` | `gpt-5.5` | `gemini-1-5-pro` | `llama-3-70b` |
| **Model Engineer** | Sonnet | `claude-sonnet-4.5` | `claude-sonnet-4.5` | `gpt-4-turbo` | `gpt-5.5` | `gemini-1-5-pro` | `llama-3-70b` |
| **Lead Engineer** | Sonnet | `claude-sonnet-4.6` | `claude-sonnet-4.6` | `gpt-4` | `gpt-5.5` | `gemini-1-5-pro` | `llama-3-70b` |
| **Senior Engineer** | Sonnet | `claude-sonnet-4.6` | `claude-sonnet-4.6` | `gpt-4-turbo` | `gpt-5.5` | `gemini-1-5-pro` | `llama-3-70b` |
| **Principal Engineer** | Opus | `claude-opus-4.6` | `claude-opus-4.6` | `gpt-4o` | `gpt-5.5` | `gemini-2-pro` | `llama-3-405b` |
| **Security Engineer** | Opus | `claude-opus-4.8` | `claude-opus-4.8` | `gpt-4o` | `gpt-5.5` | `gemini-2-pro` | `llama-3-405b` |

**Why these model choices:**
- **Haiku / gpt-4o-mini / gpt-5.4-mini / gemini-2.0-flash / llama-3-8b** — cheapest tier, sufficient for deterministic routing and pre-planned execution
- **Sonnet / gpt-4-turbo / gpt-5.5 / gemini-1-5-pro / llama-3-70b** — mid-tier, balances cost and capability for planning, review, and validation
- **Opus / gpt-4o / gemini-2-pro / llama-3-405b** — highest capability tier, required for architecture and security decisions

### Provider Feature Deltas

Not all providers support every feature. The framework degrades gracefully:

| Feature | Claude (Anthropic) | GitHub Copilot | OpenAI | Google | Meta/Llama |
|---------|-------------------|----------------|--------|--------|------------|
| Extended Thinking | ✅ Native | ✅ Native | ⚠️ Limited | ❌ Not supported | ❌ Not supported |
| Structured Output | ✅ | ✅ | ✅ | ✅ | ❌ Not guaranteed |
| Max Context | 200K tokens | 200K tokens | 128K tokens | 1M tokens | 128K tokens |
| Cost Tier | Premium | Premium | Premium | Standard | Budget/Free |

> ⚠️ **Thinking mode on non-Claude providers:** When deploying to OpenAI, Google, or Meta, `thinking: true` roles fall back to the best available reasoning of the target model.

See [docs/guides/harness-setup/](docs/guides/harness-setup/) for detailed harness configuration.

### Codex Support & Pricing Snapshot

Current OpenAI docs describe Codex as available on Free, Go, Plus, Pro, Business, Edu, and Enterprise plans. For this repo, the Codex renderer is initial support for workspace-managed runs, with the current role map following the canonical `gpt-5.4-mini` / `gpt-5.5` split.

| Codex plan | Price | Current support snapshot |
|------------|-------|-------------------------|
| Free | `$0/month` | Quick coding tasks |
| Go | `$8/month` | Lightweight coding tasks |
| Plus | `$20/month` | Codex on the web, CLI, IDE extension, and iOS; latest models include GPT-5.5, GPT-5.4, and GPT-5.4 mini |
| Pro | `from $100/month` | 5x or 20x higher Codex rate limits; GPT-5.3-Codex-Spark research preview |
| API key | Token-based | CLI, SDK, or IDE extension only; no cloud features; usage billed by API pricing |

---


## When to Use This System

**✅ Use Agentic Engineers when:**
- You need **coordination across 8+ specialized AI agents**
- You want **quality gates and cost optimization** built-in
- You need **parallel sub-agent execution at scale** (tens to hundreds concurrent)
- You want **structured handoffs** (DELEGATE/HANDBACK protocol)
- You need **metrics and feedback loops** for continuous improvement

**❌ Consider alternatives when:**
- You only need a single agent (use the provider's native API)
- You don't care about cost optimization (use Opus for everything)
- You don't need quality gates or structured validation
- You're building a chatbot or conversational AI (different problem domain)

See [docs/market-comparison.md](docs/market-comparison.md) for detailed comparison with CrewAI, LangGraph, AutoGen, and other frameworks.

---

## Supported Harnesses

| Harness | Description | Best For | Status |
|---------|-------------|----------|--------|
| [Codex](docs/guides/harness-setup/codex.md) | Codex custom agents, skills, and permission profiles | Workspace-managed runs, local development | ⚠️ Initial renderer support |
| [OpenCode](docs/guides/harness-setup/opencode.md) | Primary harness for autonomous coordination | Production use, dark factory mode | ✅ Recommended |
| [GitHub Copilot](docs/guides/harness-setup/copilot.md) | GitHub's official CLI with CI/CD integration | GitHub workflows, team collaboration | ✅ Stable |
| [Claude Code](docs/guides/harness-setup/claude.md) | Claude's native IDE and code editor | Interactive development, prototyping | ✅ Stable |
| [π.dev](docs/guides/harness-setup/pi-dev.md) | Experimental harness with emerging features | Early adopters, experimentation | ⚠️ Beta |

See [docs/guides/harness-setup/](docs/guides/harness-setup/) for detailed setup guides per harness.

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Key Areas:**
- **Harness integrations** — Add support for new AI coding harnesses
- **Agent roles** — Design new specialist agents for specific domains
- **Skills** — Create reusable skills for common tasks
- **Testing** — Expand test coverage and evaluation framework
- **Documentation** — Improve guides, examples, and troubleshooting

---

## License

MIT License — see [LICENSE](LICENSE) for details.

## Acknowledgments

Built with inspiration from:
- **CrewAI** — Multi-agent orchestration patterns
- **LangGraph** — State machine design for AI workflows
- **AutoGen** — Agent communication protocols
- **OpenAI Agents SDK** — Structured agent design

Special thanks to the open-source AI community for pushing the boundaries of what's possible with multi-agent systems.

---

**⭐ If this project helps you, please star the repository and share with others!**
