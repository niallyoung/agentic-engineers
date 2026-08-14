# Multi-Agent Orchestration Landscape (2026)

**Research date:** 2026-08-13  
**Staleness warning:** This field moves fast — re-research quarterly.

---

## Where agentic-engineers sits

The agent orchestration ecosystem spans three tiers:

### Tier 1: Heavy/production orchestration frameworks (code-first, infra-coupled)
Enterprise-grade frameworks bundling durable state management, observability, and checkpointing. Examples: LangGraph/LangChain, CrewAI, Microsoft Agent Framework, Google ADK, AWS Strands. These solve distributed agent runtime problems but introduce dependency weight, API churn, cloud coupling, and high abstraction tax. Practitioner consensus: 5+-engineer teams often replace them with provider SDKs + lightweight routers.

### Tier 2: Light code-first SDKs
Minimal frameworks prioritizing developer experience and portability: OpenAI Agents SDK, PydanticAI, smolagents, Mastra, Claude Agent SDK. Low dependency weight, multi-vendor support, and weekly iteration. Trade-off: less observability scaffolding; user responsibility for cost tracking and error recovery.

### Tier 3: Markdown-first / harness-native layer
The emerging niche where agentic-engineers sits: Markdown-sourced agent/skill definitions rendered idiomatically per harness (Claude Code, Copilot, Codex, Gemini CLI). Content marketplaces like wshobson/agents (38.8k stars) and SDLC frameworks like obra/superpowers democratize agent-driven workflows, but lack structured handoff protocols and cost-quality loops. **Our positioning:** portable **orchestration protocol (DELEGATE/HANDBACK) + roster** across CLIs, distinct from content-sync tools and config marketplaces — we ship routing rules, structured handoff, and metrics feedback.

---

## Framework Comparison

| Framework | Positioning | Weight | Portability | Delegation mechanism | Model-churn adaptation | License | Momentum (mid-2026) |
|---|---|---|---|---|---|---|---|
| LangGraph/LangChain 1.0 | Enterprise durable stateful agents | Heavy: large dep tree, checkpointer DB, LangSmith | Any model vendor; not a coding-CLI layer | Graph edges; supervisor patterns | init_chat_model strings + provider pkgs | MIT | 1.0 Oct 2025; largest prod footprint (self-reported) |
| CrewAI | Role-based crews, fast prototyping | Medium: Python framework + AMP | Multi-vendor via LiteLLM; no CLI-harness story | Task assignment; hierarchical process | Config strings | MIT (core) | v1.14.3 Apr 2026; ~54k stars |
| MS Agent Framework 1.0 | Azure-centric AutoGen+SK unification | Heavy: .NET/Python SDK, Azure services | Multi-model but Azure-gravity | Handoff orchestration + graph workflows | Azure AI Foundry catalog | MIT | GA Apr 3 2026; 12.4k stars |
| OpenAI Agents SDK | Minimal-abstraction code SDK | Light-medium: small Python/TS lib | Any OpenAI-compatible API; GPT-centric in practice | Handoffs = transfer tool call + history; subagent primitive (beta Apr 2026) | Model string per Agent | MIT | Weekly releases; 27k+ stars; pre-1.0 |
| PydanticAI | Type-safe minimal agent framework | Light: Pydantic-stack Python | Model-agnostic by design | Programmatic (agent-as-tool) | Model registry strings, fallback models | MIT | Active, production-cited |
| smolagents | Code-executing minimal agents | Very light | Any HF/LiteLLM model | Managed agents (code calls) | Model string | Apache 2.0 | Active |
| Mastra | TS agents + deterministic workflows | Light-medium: npm | Vendor-agnostic TS | Workflow steps + agent networks | Model routers | Elastic/OSS (verify) | Top JS pick 2026 |
| AWS Strands 1.0 | Model-first, minimal scaffolding | Light Python; AWS-friendly | Multi-provider incl. Bedrock | Agents-as-tools, swarms | Bedrock/model IDs | Apache 2.0 | 1.0 2026; 150k+ downloads |
| Claude Agent SDK + Skills | Claude Code loop as runtime | Light SDK; subagents = full contexts (cost sprawl) | Anthropic-only runtime; Skills spec cross-tool | Subagent spawn, report back (= our substrate) | Tier aliases (opus/sonnet/haiku) | Proprietary SDK, open Skills spec | Very high |
| wshobson/agents | Multi-harness plugin marketplace (content) | Markdown-only + render scripts | 6 coding CLIs from single source | 16 orchestrator agents; no structured handoff schema | Tier-based assignment | MIT | 38.8k stars, 4.1k forks |
| obra/superpowers | SDLC methodology as composable skills | Markdown skills + hooks, near-zero deps | 8 harnesses | Skill-driven subagent execution; no YAML protocol | Inherits harness model choice | open source (verify) | Anthropic marketplace Jan 2026; stars disputed (57k-224k, flag) |
| dotagents / AgentSync / ai-rules-sync | Config-sync "dotfiles for agents" | Tiny (single binary / toml) | 5-11 tools each | None — sync only | None | OSS various | Active micro-genre |
| **agentic-engineers** | Portable orchestration protocol + roster across 4 CLIs | Markdown + tiny advisory Python, render pipeline; no runtime infra | 4 harnesses; Claude-family + Codex GPT substitution | **DELEGATE/HANDBACK YAML + direct spawn, depth/fan-out limits, metrics** | LOCKED_MODELS.sh + per-harness render transform | MIT | n/a |

---

## Standards Alignment

### Foundational standards

**AAIF (Linux Foundation Agentic AI Foundation)**, formed Dec 2025 with platinum members (AWS, Anthropic, Block, Bloomberg, Cloudflare, Google, Microsoft, OpenAI), established three baseline specifications:

- **MCP (Model Context Protocol)** — won the agent↔tool layer. 2026-07-28 spec revision: stateless core (horizontal scaling on plain HTTP), MCP Apps (server-rendered UI), Tasks extension (long-running work). Registry ~9.6k servers / ~29k versions; 41% of surveyed orgs in limited/broad production.
- **A2A (Agent-to-Agent Protocol)** — v1.0 stable Jan 2026; 150+ orgs; in Azure AI Foundry, Bedrock AgentCore, Google Cloud; service-to-service (JSON-RPC, agent cards). Deployment metrics unverified; independent commentary calls adoption "messier." Largely irrelevant to in-process CLI subagent handoff today.
- **AGENTS.md** — de facto standard: 60k+ repos, 20-30+ tools (Codex, Cursor, Copilot, Gemini CLI, Aider, Windsurf, Zed, Jules, Factory…); nested-file precedence for monorepos. **Uncertainty flag:** one blog wrongly credits Anthropic origin; agents.md itself credits OpenAI Codex/Amp/Jules/Cursor/Factory.

### New entrant: Agent Skills

**SKILL.md (Agent Skills)**, published as open standard Dec 18, 2025 at agentskills.io. Fastest adoption of any 2025-26 spec: Microsoft, OpenAI, Cursor, GitHub, Atlassian, Figma; by Mar 2026, 32 tools (Gemini CLI, JetBrains Junie, AWS Kiro, Block goose) read the same SKILL.md directory structure. **Our skills-first bet landed on the winning horse.**

### The handoff gap

**Delegation/handoff formats: NO open standard exists.** Each framework ships proprietary handoff:
- OpenAI Agents SDK: tool-call + history transfer
- Microsoft Agent Framework: handoff orchestration layer
- IBM ACP/BeeAI: structured handoff negotiation
- A2A: task semantics
- Academic work (AIP, "Externalization in LLM Agents" survey) explicitly notes the absence. **DELEGATE/HANDBACK sits in genuinely unstandardized territory — an opportunity (first-mover positioning) and a risk (whatever AAIF blesses later wins).**

### Our concrete compatibility

Widespread portability in 2026 means:
1. **SKILL.md conformance** with agentskills.io (done)
2. **AGENTS.md v1.0 conformance** when AAIF publishes the stable behavioral spec (under 2026 roadmap)
3. **Optionally exposing skills' deterministic scripts via MCP** (stateless-core 2026-07-28 spec lowers the bar)
4. **Rendering into each harness's native agent format** (we already do this: Claude Code AGENTS.md, Copilot custom agents, Codex TOML, Gemini CLI config)

We **do not** adopt A2A (service-to-service, irrelevant to our in-process spawn model).

**Compliance summary:** See [README.md § Standards Compliance](../README.md#standards-compliance) for a status table of each standard.

---

## Validation of the self-reduction thesis

The landscape confirms the core hypothesis: **harnesses are commoditizing spawn/route/skill mechanics.**

**Evidence:**
- Copilot CLI GA'd Apr 2026 with custom agents, skills, subagents, and native `/fleet` multi-subagent command
- GitHub Agent HQ (public preview Feb 2026, Apr 2026 model selection) puts Claude/Codex/Copilot agents under one control plane with AGENTS.md-based custom agents
- OpenCode v1.0 (Apr 2026 spec) ships native skills + subagents + Copilot auth
- All four harnesses now read AGENTS.md and SKILL.md natively

**What harnesses still lack** (= what we keep):
- Opinionated role rosters (Orchestrator, Engineer, Senior Engineer, … with SLAs and model assignments)
- **Structured handoff protocol** (DELEGATE/HANDBACK YAML with scope, plan, success criteria, metrics)
- **Cost/quality feedback loops** — tie task complexity to model spend and outcome quality
- **Depth and fan-out limits** to prevent runaway subagent cost

---

## Bonus-Task Backlog

The following items represent observed demand signals and low-cost extensions. **These are explicitly OPTIONAL future work, not commitments.**

| ID | Task | Why Now | Effort | Extends | Status |
|---|---|---|---|---|---|
| 1 | Publish DELEGATE/HANDBACK as standalone spec page | No open delegation standard; first-mover text costs nothing | S | `docs/specs/protocol-core-v1.0.yaml` | ✓ 2026-08-14: standalone spec published at `docs/specs/DELEGATE-HANDBACK.md` |
| 2 | agentskills.io conformance audit + badge | 32 tools read SKILL.md; conformance = free portability | S | `src/skills/` | ✓ 2026-08-14: All 6 skills conformant to agentskills.io spec |
| 3 | AGENTS.md v1.0 readiness | AAIF stable spec + validation tooling 2026 roadmap; CI step stub | S-M | `renderer/`, `.github/workflows/ci.yml` | ✓ 2026-08-14: v1.0/validator confirmed unreleased (no agentsmd/agents.md GitHub release; no primary AAIF roadmap page found — see docs/RENDERING.md); nested-precedence clobber bug found live-tested and fixed in claude/opencode/codex/copilot renderers; non-blocking CI probe stub added |
| 4 | Subagent cost guardrail | Runaway-cost is loudest pain in niche; our metrics fields exist | M | `PROTOCOL.md`, orchestrator skill | ✓ 2026-08-14: Convention documented on existing `tokens_estimate`/`budget` DELEGATE extensions + Orchestrator refusal pattern (`docs/PROTOCOL.md` §6, `src/AGENTS.md`, orchestrator `SKILL.md`); no wire-format or hook change |
| 5 | Gemini CLI + Cursor render targets | Peers cover 6-8 harnesses; we cover 4; Gemini CLI is highest-value | M per harness | `renderer/scripts/` | |
| 6 | /fleet-aware Copilot rendering | Investigated 2026-08-14: NOT adoptable due to architectural mismatch (single-prompt /fleet vs. per-agent DELEGATE blocks) | S | `docs/RENDERING.md` | |
| 7 | models.dev-backed advisory drift check | Pure-function script diffing `LOCKED_MODELS.sh` against models.dev JSON (context, pricing, deprecation) | S | `scripts/` | |
| 8 | Render pipeline storytelling | "One source → N harnesses" is wshobson's 38.8k-star selling point; our differentiator is protocol + metrics | S | `docs/LANDSCAPE.md` + README Positioning | |
| 9 | MCP-expose deterministic skill scripts (thin, optional) | Stateless-core spec lowers the bar; validate demand first | M | Generated MCP manifest | |
| 10 | HANDBACK cost rollup report | Session-transcript-derived cost/quality summary per role; #1 asked-for capability | M | Post-session analysis | ✓ 2026-08-14: `scripts/handback_rollup.py` — advisory per-role cost/quality report from HANDBACK YAML, compared against `docs/SPEC.md`'s Cost Target Distribution; `tests/test_handback_rollup.py` (36 tests incl. drift check) |

---

## Model-Churn Strategy

### The verdict

Tier/alias indirection (opus/sonnet/haiku) is consensus best practice across the niche and avoids hardcoding model names into routing logic. Claude Code's native tier aliases are the harness-native version. We already do this at render time; role→tier as the primary mapping, tier→model-ID as the single swap point.

### Three cheap borrows (candidates, not commitments)

1. **Per-tier fallback pools** — A tier maps to an ordered pool with fallback, not one ID. LiteLLM Auto Router v2 (v1.94.x, Jul 2026) formalizes this as `tier_pools` and `model_group_alias`. We already have exactly this for security_engineer (fable-5 → opus-4.8 fallback); generalizing per-tier is ~10 lines of LOCKED_MODELS.sh.

2. **Review-by dates** — Set a review date per locked model at lock time (ValueStream lifecycle guidance; OpenAI retired 15 model entries on Jul 23, 2026 alone). LOCKED_MODELS.sh could carry `REVIEW_BY_<model>` dates checked by pre-commit — zero runtime cost.

3. **models.dev advisory drift check** — Pure-function script diffing LOCKED_MODELS.sh against models.dev's JSON (capabilities, context, pricing, deprecation tracking). Advisory-only (no enforcement), leveraging OpenCode's open TOML/JSON model database as the lightweight external registry.

### What to avoid

Proxy-based routers and provider-hosted virtual-model services add operational coupling; nothing in the field is lighter-and-better than LOCKED_MODELS.sh + per-harness render transform.

---

## Sources

**Landscape research:** presenc.ai/research/multi-agent-orchestration-frameworks-2026 · langchain.com/resources/ai-agent-frameworks · changelog.langchain.com/announcements/langgraph-1-0-is-now-generally-available · blog.langchain.com/langchain-langgraph-1dot0/ · blog.agentailor.com/posts/is-langchain-worth-it-2026 · enterprisedna.co/resources/blog/practitioner-langchain-2026/ · en.wikipedia.org/wiki/CrewAI · github.com/crewAIInc/crewAI/releases · atlan.com/know/ai-agent/what-is-autogen/ · theagentecosystem.com/blog/agent-framework-consolidation-2026 · openlinksw.com/data/html/openai-agents-sdk-next-evolution-infographic.html · devops.com/openai-upgrades-its-agents-sdk-with-sandboxing-and-a-new-model-harness/ · respan.ai/articles/openai-agents-sdk-vs-swarm · aws.amazon.com/blogs/opensource/introducing-strands-agents-1-0 · blog.jetbrains.com/pycharm/2026/06/top-agentic-frameworks · morphllm.com/ai-agent-framework · arxiv.org/abs/2604.25602 (OxyGent) · github.com/wanxingai/LightAgent · microsoft.github.io/agent-lightning · github.com/wshobson/agents · github.com/obra/superpowers · heyclau.de/entry/skills/superpowers-skills (star figure flagged) · github.com/getsentry/dotagents · lib.rs/crates/agentsync · dev.to/pederaa/how-to-sync-cursor-rules-claudemd-and-agentsmd · github.blog/news-insights/company-news/welcome-home-agents/ (Agent HQ) · codex.danielvaughan.com/2026/04/15/github-agent-hq-model-selection · devtoollab.com/blog/top-cli-ai-coding-agents (Copilot /fleet)

**Standards:** linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation · baeseokjae.github.io/posts/linux-foundation-agentic-ai-foundation-2026/ · blog.modelcontextprotocol.io/posts/2026-07-28/ · blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/ · digitalapplied.com/blog/mcp-adoption-statistics-2026 · linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations · glukhov.org/ai-systems/comparisons/a2a-protocol-2026-adoption/ · agents.md · blog.buildbetter.ai/agents-md-complete-guide (origin-conflict source) · the-decoder.com/anthropic-publishes-agent-skills-as-an-open-standard · simonwillison.net/2025/Dec/19/agent-skills/ · paperclipped.de/en/blog/agent-skills-open-standard-interoperability/ · boldare.com/blog/agent-communication-protocol-acp-explained · arxiv.org/pdf/2603.24775 (AIP) · arxiv.org/pdf/2604.08224 · learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/handoff

**Gaps/cost:** cloudzero.com/blog/claude-code-agents/ · faros.ai/blog/claude-code-token-usage · tembo.io/blog/claude-code-subagents · dev.to/suraj_khaitan (subagent field report) · github.com/VoltAgent/awesome-claude-code-subagents

**Model-adaptability:** models.dev · github.com/anomalyco/models.dev · docs.litellm.ai/blog/autorouter-v2 · truefoundry.com/blog/model-deprecations-virtual-models-staged-cutovers · valuestreamai.com/blog/ai-model-lifecycle-guide-2026 · mindstudio.ai/blog/set-up-ai-model-router-llm-stack-c2610 · tianpan.co/blog/2026-04-27-model-deprecation-treadmill

### Uncertainty Flags

1. **AGENTS.md origin** — buildbetter.ai wrongly credits Anthropic; agents.md itself credits OpenAI Codex/Amp/Jules/Cursor/Factory.
2. **Superpowers 224k-star figure** (HeyClaude, Jun 2026) vs 57.5k (Feb) — implausible, unverified against GitHub directly.
3. **A2A "production deployments"** — press-release claims without usage metrics; independent sources skeptical.
4. **LangGraph "largest production footprint"** — partly self-reported by LangChain.
5. **Mastra's exact license and Superpowers' license** — not confirmed from primary sources.
