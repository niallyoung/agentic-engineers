# AI Frameworks: Quick Comparison Table

## Core Orchestration Frameworks (For Multi-Agent Systems)

| Framework | Type | GitHub | Stars | License | Maturity | Multi-Agent | Top LLMs | Learn More |
|-----------|------|--------|-------|---------|----------|-------------|----------|-----------|
| **CrewAI** | Orchestration | [repo](https://github.com/crewAIInc/crewAI) | 51.5K | MIT | Production | ⭐⭐⭐⭐⭐ | All major | [docs](https://docs.crewai.com) |
| **LangGraph** | Orchestration | [repo](https://github.com/langchain-ai/langgraph) | 32.1K | MIT | Production | ⭐⭐⭐⭐⭐ | All major | [docs](https://docs.langchain.com/langgraph) |
| **Pydantic AI** | Runtime | [repo](https://github.com/pydantic/pydantic-ai) | 17.1K | MIT | Production | ⭐⭐⭐⭐ | All major | [docs](https://ai.pydantic.dev) |
| **Semantic Kernel** | Orchestration | [repo](https://github.com/microsoft/semantic-kernel) | 27.9K | MIT | Production | ⭐⭐⭐⭐ | Multi-provider | [docs](https://learn.microsoft.com/semantic-kernel) |
| **AutoGen** | Orchestration | [repo](https://github.com/microsoft/autogen) | 58.1K | MIT | Maintenance | ⭐⭐⭐⭐ | Multi-provider | [docs](https://microsoft.github.io/autogen) |
| **Temporal** | Orchestration | [repo](https://github.com/temporalio/temporal) | 20.3K | MIT | Production | ⭐⭐⭐⭐ | Any via code | [docs](https://docs.temporal.io) |
| **Ray** | Distributed | [repo](https://github.com/ray-project/ray) | 42.6K | Apache 2.0 | Production | ⭐⭐⭐⭐ | Any | [docs](https://docs.ray.io) |
| **Swarm** | Orchestration | [repo](https://github.com/openai/swarm) | 21.5K | MIT | Educational | ⭐⭐⭐ | OpenAI | [docs](https://github.com/openai/swarm) |
| **LangChain** | Framework | [repo](https://github.com/langchain-ai/langchain) | N/A | MIT | Production | ⭐⭐⭐⭐ | 100+ | [docs](https://docs.langchain.com) |

---

## Resource-Aware Orchestration Frameworks (Emerging Paradigm)

**Note:** A new category of frameworks emerging in 2025-2026 that treat computational resources (tokens, API calls, time) as first-class constraints. These frameworks explicitly model resource budgets and enable cost-predictable autonomous operation.

| Framework | Type | GitHub | Stars | License | Maturity | Multi-Runtime | Resource Model | Learn More |
|-----------|------|--------|-------|---------|----------|---------------|----------------|-----------|
| **Gastown** | Resource-Aware Orchestration | [repo](https://github.com/gastownhall/gastown) | 15.4K | MIT | Production (v1.1.0) | ⭐⭐⭐⭐⭐ (Claude, Copilot, Codex, Gemini) | Gas budgets (explicit constraints) | [docs](https://github.com/gastownhall/gastown/blob/main/README.md) |
| **Agentic Engineers** | Resource-Aware + Quality Gates | [repo](https://github.com/niallyoung/agentic-engineers) | Internal | MIT | Production (Phase 6) | ⭐⭐⭐ (OpenCode, Claude, Copilot) | Token tracking + Model Engineer optimization | [docs](https://github.com/niallyoung/agentic-engineers/blob/main/README.md) |

### Key Differences: Resource-Aware vs. Traditional Orchestration

| Aspect | Traditional (CrewAI, LangGraph, AutoGen) | Resource-Aware (Gastown, Agentic Engineers) |
|--------|----------------------------------------|-------------------------------------------|
| **Resource Model** | Unlimited (manual tuning) | Explicit budgets (automatic governance) |
| **Cost Predictability** | Manual (requires expertise) | Built-in (gas/token budgets) |
| **Scaling Pattern** | Horizontal (more agents) | Resource-constrained (bounded) |
| **Failure Mode** | Runaway costs | Graceful degradation (within budget) |
| **Monitoring** | Post-hoc (after overspend) | Real-time (during execution) |
| **Optimization** | Manual tuning | Autonomous (feedback loops) |

---

## Provider SDKs (Foundation Layer)

| Framework | Type | Language | Primary LLM | GitHub | License | Maturity | Tool Use | Learn More |
|-----------|------|----------|------------|--------|---------|----------|----------|-----------|
| **Anthropic SDK** | SDK | Python | Claude | [repo](https://github.com/anthropic-ai/anthropic-sdk-python) | MIT | Production | ⭐⭐⭐⭐⭐ | [docs](https://docs.anthropic.com) |
| **OpenAI SDK** | SDK | Python | GPT-4o | [repo](https://github.com/openai/openai-python) | MIT | Production | ⭐⭐⭐⭐⭐ | [docs](https://platform.openai.com/docs) |
| **Cohere SDK** | SDK | Python | CommandR | [repo](https://github.com/cohere-ai/cohere-python) | MIT | Production | ⭐⭐⭐⭐ | [docs](https://docs.cohere.com) |
| **Together AI SDK** | SDK | Python | 100+ OSS | [repo](https://github.com/togethercomputer/together-python) | Commercial | Production | ⭐⭐⭐ | [docs](https://docs.together.ai) |
| **Vercel AI SDK** | SDK | TS/JS | Multi-provider | [repo](https://github.com/vercel-labs/ai) | Apache 2.0 | Production | ⭐⭐⭐⭐ | [docs](https://sdk.vercel.ai) |
| **Magentic** | SDK | Python | Multi-provider | [repo](https://github.com/jackmpcollins/magentic) | MIT | Production | ⭐⭐⭐ | [docs](https://jackmpcollins.github.io/magentic) |

---

## Local LLM Runtimes (Development & Offline)

| Framework | Type | Interface | Models | License | GitHub Stars | Maturity | API Support | Learn More |
|-----------|------|-----------|--------|---------|--------------|----------|------------|-----------|
| **Ollama** | Local Runtime | CLI + API | 100+ | MIT | 171K ⭐ | Production | REST API | [site](https://ollama.com) |
| **LM Studio** | Local Runtime | GUI | 100+ | Freemium | N/A | Production | REST API | [site](https://lmstudio.ai) |
| **Jan.ai** | Local Runtime | GUI | 100+ | AGPL-3.0 | N/A | Production | OpenAI API | [site](https://jan.ai) |
| **GPT4All** | Local Runtime | Python/CLI | CPU-optimized | MIT | N/A | Production | Python API | [site](https://www.gpt4all.io) |
| **Text Gen WebUI** | Local Runtime | Web (Gradio) | 100+ | AGPL v3 | N/A | Production | API | [repo](https://github.com/oobabooga/text-generation-webui) |

---

## IDE/Editor Integration (Development Tooling)

| Framework | Type | IDEs | Open Source | License | Stars | LLM Support | Learn More |
|-----------|------|------|-------------|---------|-------|------------|-----------|
| **Continue.dev** | IDE Plugin | VS Code, JetBrains, Windsurf | ✅ | Apache 2.0 | 33.2K | Multi-provider | [repo](https://github.com/continuedev/continue) |
| **Zed AI** | Editor | Zed | ✅ | AGPL/Apache/GPL | 82.9K | Multi-provider | [repo](https://github.com/zed-industries/zed) |
| **Cursor IDE** | IDE | Proprietary | ❌ | Proprietary | N/A | Multi-provider | [site](https://cursor.com) |
| **GitHub Copilot** | IDE Plugin | VS Code, JetBrains | ❌ | Commercial | N/A | OpenAI | [site](https://github.com/features/copilot) |
| **Codeium** | IDE Plugin | Multi-IDE | ❌ | Proprietary | N/A | Proprietary | [site](https://codeium.com) |
| **TabNine** | IDE Plugin | Multi-IDE | ❌ | Commercial | N/A | Proprietary | [site](https://tabnine.com) |
| **Supermaven** | IDE Plugin | VS Code, JetBrains | ❌ | Commercial | N/A | Proprietary | [site](https://supermaven.com) |

---

## CLI/Terminal Tools (Developer Workflow)

| Framework | Type | Open Source | License | Use Case | LLM Support | GitHub | Learn More |
|-----------|------|-------------|---------|----------|------------|--------|-----------|
| **Aider** | Pair Programming | ✅ | Apache 2.0 | Git-aware AI pairing | 100+ providers | [repo](https://github.com/Aider-AI/aider) | [site](https://aider.chat) |
| **Mentat** | Pair Programming | ✅ | Apache 2.0 | Terminal pair programming | Multi-provider | [repo](https://github.com/AbanteAI/mentat) | [site](https://mentat.codes) |
| **Plandex** | Project Planning | ✅ | MIT/Apache 2.0 | AI planning in terminal | Multi-provider | [repo](https://github.com/plandex-ai/plandex) | [site](https://plandex.ai) |
| **Devon** | Autonomous Agent | ✅ | MIT/Apache 2.0 | Autonomous coding | Multi-provider | [repo](https://github.com/entropy-research/devon) | [site](https://www.devon.ai) |
| **Grit** | Code Transformation | ⚠️ Mixed | Commercial/OSS | Code transformation | Multi-provider | [repo](https://github.com/getgrit/grit) | [site](https://grit.io) |

---

## Managed Cloud Services (Enterprise)

| Service | Provider | Models | Multi-Agent | Native Agents API | Enterprise Features | Pricing |
|---------|----------|--------|-------------|------------------|-------------------|---------|
| **Amazon Bedrock** | AWS | Claude, GPT, Llama | ✅ | ✅ Native Agents API | Security, compliance | Usage-based |
| **Google Vertex AI** | Google | Gemini, Claude | ✅ | ✅ Agents Framework | Analytics, evaluation | Usage-based |
| **Azure OpenAI** | Microsoft | GPT models | ✅ | ✅ Assistants API | Enterprise compliance | Subscription |

---

## Language & Framework Support

### Python Frameworks (Dominant)
- CrewAI, LangGraph, Pydantic AI, AutoGen, Swarm, Ray, Temporal, Aider, Mentat, Semantic Kernel, Anthropic SDK, OpenAI SDK, Cohere SDK, Together AI SDK, Ollama, Jan.ai, GPT4All, Magentic

### Multi-Language Support
- **Semantic Kernel:** Python, C#, Java
- **Temporal:** Go, Java, TypeScript, Python, C#
- **Anthropic/OpenAI SDKs:** Python, JavaScript/TypeScript, more

### JavaScript/TypeScript
- Vercel AI SDK, OpenAI SDK (JS), Anthropic SDK (JS)

---

## Key Decision Matrix

### Choose CrewAI If:
- ✅ Building multi-agent teams
- ✅ Need fast execution (5.76x faster than LangGraph)
- ✅ Want independent framework (not LangChain dependent)
- ✅ Enterprise deployment needed
- ✅ YAML configuration preferred

### Choose LangGraph If:
- ✅ Need low-level state management
- ✅ Require human-in-the-loop capabilities
- ✅ Want durable execution with recovery
- ✅ Deep debugging needed (LangSmith integration)
- ✅ Complex agent workflows required

### Choose Pydantic AI If:
- ✅ Type safety is priority
- ✅ Full IDE support needed
- ✅ Dependency injection important
- ✅ Strong validation required
- ✅ Prefer Pydantic ecosystem

### Choose Semantic Kernel If:
- ✅ Multi-language support needed
- ✅ Enterprise plugin ecosystem required
- ✅ Vector database integration needed
- ✅ Microsoft ecosystem integration
- ✅ Large-scale deployment needed

### Choose Temporal If:
- ✅ Mission-critical durability required
- ✅ Failure recovery essential
- ✅ Complex orchestration needed
- ✅ Enterprise workflows
- ✅ Multi-service coordination

### Choose Ollama If:
- ✅ Local development needed
- ✅ Offline capability required
- ✅ Privacy is critical
- ✅ Cost optimization needed
- ✅ Model flexibility important

### Choose Aider If:
- ✅ Terminal-based workflow preferred
- ✅ Git integration needed
- ✅ Pair programming style
- ✅ Multi-file context required
- ✅ Automatic commits wanted

---

## Open-Source License Breakdown

### MIT (Most Permissive - 20 frameworks)
Permissive, allows commercial use, requires attribution

- CrewAI, LangGraph, Pydantic AI, Temporal, AutoGen, Swarm, Aider, Mentat, Ollama, GPT4All, Anthropic SDK, OpenAI SDK, Cohere SDK, Magentic, LangChain, Semantic Kernel (partial)

### Apache 2.0 (10 frameworks)
More restrictive than MIT, includes patent grants

- Continue.dev, Ray, Vercel AI, Airflow, Semantic Kernel (partial)

### AGPL (4 frameworks)
Most restrictive, requires derivative works be open-source

- Zed AI, Text Generation WebUI, Jan.ai

### Commercial/Proprietary (9 frameworks)
Commercial products, licensing varies

- Cursor, Codeium, TabNine, Supermaven, GitHub Copilot, LM Studio, Bedrock, Vertex AI, Azure OpenAI

---

## Maturity & Stability Scale

**Production** (38): Thoroughly tested, active development, safe for critical systems
**Stable** (5): Mature, less active development, suitable for production
**Maintenance** (1): In maintenance mode, no major new features
**Educational** (1): Designed for learning, not recommended for production

---

## Documentation Quality Scale

⭐⭐⭐⭐⭐ **Excellent** (18 frameworks)
- Comprehensive, clear, well-organized, quick start guides, API docs, examples

⭐⭐⭐⭐ **Good** (22 frameworks)
- Adequate documentation, most features covered, good examples

⭐⭐⭐ **Fair** (4 frameworks)
- Basic documentation, some gaps, community forums helpful

⭐⭐ **Poor** (1 framework)
- Minimal documentation, steep learning curve

---

## GitHub Activity Ranking

### Top 10 by Stars:
1. **Ollama** - 171K ⭐ (Local runtime, essential)
2. **Zed** - 82.9K ⭐ (Editor, not agent framework)
3. **AutoGen** - 58.1K ⭐ (Orchestration, maintenance mode)
4. **CrewAI** - 51.5K ⭐ (Orchestration, RECOMMENDED)
5. **Apache Airflow** - 45.4K ⭐ (Workflow, not agent-specific)
6. **Aider** - 44.9K ⭐ (CLI tool, good for development)
7. **Ray** - 42.6K ⭐ (Distributed, very relevant)
8. **Continue.dev** - 33.2K ⭐ (IDE plugin, good tooling)
9. **LangGraph** - 32.1K ⭐ (Orchestration, RECOMMENDED)
10. **Semantic Kernel** - 27.9K ⭐ (Orchestration, enterprise)

---

## For Agentic-Engineers: Top Recommendations

### Tier 1: Essential
- **CrewAI** - Multi-agent orchestration
- **LangGraph** - State management
- **Pydantic AI** - Type safety
- **Anthropic/OpenAI SDKs** - Foundation

### Tier 2: Highly Recommended
- **Semantic Kernel** - Enterprise scale
- **Temporal** - Durability
- **Ollama** - Local development
- **Ray** - Distributed systems

### Tier 3: Important Integration Points
- **Continue.dev** - IDE integration
- **Aider** - Developer workflow
- **LangChain** - Ecosystem support
- **Cohere SDK** - LLM diversity

---

## Quick Links Summary

**Getting Started:**
- CrewAI docs: https://docs.crewai.com
- LangGraph docs: https://docs.langchain.com/langgraph
- Ollama: https://ollama.com

**APIs & SDKs:**
- Anthropic: https://docs.anthropic.com
- OpenAI: https://platform.openai.com/docs

**Local Development:**
- Ollama GitHub: https://github.com/ollama/ollama
- Jan.ai: https://jan.ai

**Enterprise:**
- Semantic Kernel: https://learn.microsoft.com/semantic-kernel
- Temporal: https://temporal.io

---

**Last Updated:** May 16, 2026  
**Data Source:** Comprehensive research across 45 AI frameworks  
**For:** Agentic-Engineers Framework Selection & Integration
