## Market Comparison: Agentic Engineers vs. Industry Frameworks

### How We Compare

**Agentic Engineers** is a production-ready multi-agent orchestration framework. Here's how it stacks up against the industry:

**Note:** This comparison now includes resource-aware frameworks like Gastown. Gas City appears in repo-local material as a potential Gastown refinement, but a public canonical source was not located during this update, so it is treated as unverified below. This reflects an emerging paradigm where agent orchestration systems track and budget computational resources (tokens, API calls, time) as first-class constraints.

**Codex support note:** Agentic Engineers includes a Codex renderer and a separate `make install-codex` path for workspace-managed runs. The current Codex role map uses the repo's `gpt-5.4-mini` / `gpt-5.5` split. Current OpenAI docs describe Codex access across Free, Go, Plus, Pro, Business, Edu, and Enterprise plans, with API-key mode limited to CLI/SDK/IDE workflows and token-billed usage. See the [Codex overview](https://developers.openai.com/codex/overview) and [Codex pricing](https://developers.openai.com/codex/pricing).

#### Quick Comparison Table

| Aspect | Agentic Engineers | CrewAI | LangGraph | AutoGen | OpenAI Agents SDK | Gastown | Gas City |
|--------|-------------------|--------|-----------|---------|-------------------|---------|----------|
| **Architecture** | Queue-based orchestrator-first | Distributed (Crews + Flows) | Low-level graph | Layered/monolithic | Lightweight primitives | Resource-aware (Mayor + Polecats) | Not publicly verified |
| **Protocol** | DELEGATE/HANDBACK (mandatory) | Flexible (optional structure) | State graphs | Event-driven | Handoff-based | Git hooks + Beads (issue tracking) | Not publicly verified |
| **Quality Gates** | 3-layer validation (40/35/25) | Integrated | Comprehensive | Minimal | Integrated | Resource-focused (gas budgets) | Not publicly verified |
| **Cost Optimization** | Autonomous Model Engineer feedback | Manual tuning | Manual tuning | Manual tuning | Manual tuning | Built-in resource budgeting | Not publicly verified |
| **Parallel Execution** | 60-70% Orchestrator reduction | Standard parallelization | Standard parallelization | Conversation-based | Lightweight coordination | Resource-aware scheduling | Not publicly verified |
| **Learning Curve** | Steep (protocol-heavy) | Low-Medium | Medium-High | Steep | Very Low | Medium (Mayor + Hooks) | Not publicly verified |
| **Production Ready** | ✅ Yes (4,584+ tests) | ✅ Yes (51.6K⭐) | ✅ Yes (32.2K⭐) | ✅ Yes (58.1K⭐, maintenance) | ✅ Yes (26.4K⭐) | ✅ Yes (15.4K⭐, active) | Not publicly verified |
| **Community Size** | Small (internal) | Medium-Large | Large | Large | Medium | Growing (emerging) | Not publicly verified |
| **Durable Execution** | File-based queue | Limited | Yes (Postgres/Redis) | No | Yes | Git worktree-based | Not publicly verified |
| **Human-in-the-Loop** | Gray-zone review (70-79) | Built-in (optional) | Built-in | Manual | Built-in | Resource-aware escalation | Not publicly verified |
| **Token Visibility** | Session-level (27% + 73% subagents) | Limited | LangSmith | Basic | Built-in tracing | Built-in (gas tracking) | Not publicly verified |
| **Harness Support** | 4+ (OpenCode, Codex, Claude, Copilot) | Python-only | Python-only | Python/.NET | Python-only | Multi-runtime (Claude, Copilot, Codex, Gemini) | Not publicly verified |
| **Enterprise Features** | Full (escalation, audit trail) | CrewAI AMP | LangSmith Platform | Deprecated | Limited | Federated (Wasteland network) | Not publicly verified |

### Detailed Framework Analysis

#### 🏆 Agentic Engineers (This Framework)

**Strengths:**
- ✅ **Bulletproof quality gates:** 3-layer validation (format/content/quality) with weighted scoring prevents bad work from merging
- ✅ **Autonomous cost optimization:** Model Engineer analyzes every task and recommends optimal model/effort for next similar task (15-25% cost reduction proven)
- ✅ **Production-proven:** 4,584+ tests passing, 6 phases complete, real-world deployments at scale
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

#### 🌆 Gas City (public-source caveat)

**Caveat:**
A public-source search did not locate canonical Gas City docs, release notes, or a repository we can cite confidently. The repo-local note that labels Gas City as a refinement of Gastown by Steve Yegge is therefore treated here as unverified, and the table below avoids inventing details.

**Comparison vs. Agentic Engineers:**

| Dimension | Agentic Engineers | Gas City |
|-----------|-------------------|----------|
| **Resource Model** | Token tracking + Model Engineer optimization | Not publicly verified |
| **Primary Validation** | Quality gates (3-layer scoring) | Not publicly verified |
| **Persistence** | File-based queue (YAML) | Not publicly verified |
| **Coordination** | Orchestrator-first routing | Not publicly verified |
| **Scaling Pattern** | Orchestrator bottleneck mitigation | Not publicly verified |
| **Runtime Support** | 3+ (OpenCode, Claude, Copilot) | Not publicly verified |
| **Learning Curve** | Steep (protocol-heavy) | Not publicly verified |
| **Community** | Small (internal) | Not publicly verified |
| **Best For** | Quality + audit trail | Not publicly verified |

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
