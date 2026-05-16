# AI Frameworks Research - Complete Documentation Index

## Overview

This research package contains comprehensive analysis of **45 AI frameworks** across 6 categories, including orchestration systems, IDEs, CLI tools, SDKs, local LLM runtimes, and managed services.

**Research Date:** May 16, 2026  
**Scope:** Complete comparative analysis with URLs, licensing, maturity assessment, and agentic-engineers relevance

---

## Files in This Package

### 1. **ai-frameworks-research.json** (58 KB)
Complete structured data export with detailed information for all 45 frameworks.

**Contains:**
- All framework objects with full metadata
- Multi-agent support details
- LLM provider lists
- License information
- GitHub stars and last commit dates
- Documentation quality ratings
- Agentic-engineers relevance assessments
- Summary statistics by category, license, maturity
- Use-case recommendations

**Best for:** Data analysis, integration, programmatic access, building decision matrices

**Sample entry structure:**
```json
{
  "name": "CrewAI",
  "category": "Orchestration",
  "github_url": "https://github.com/crewAIInc/crewAI",
  "framework_type": "...",
  "key_features": [...],
  "multi_agent_support": {...},
  "llm_support": {...},
  "license": {...},
  "maturity_level": "stable/production",
  "github_stars": 51500,
  "relevance_to_agentic_engineers": "..."
}
```

---

### 2. **AI_FRAMEWORKS_ANALYSIS.md** (16 KB)
Comprehensive written analysis with detailed findings, insights, and recommendations.

**Contains:**
- Executive summary
- Detailed category breakdown (9 orchestration, 7 IDE, 5 CLI, 13 runtime, 5 local, 3 managed)
- Multi-agent support analysis (20 full support, 15 limited)
- LLM provider support matrix
- Licensing summary with breakdown
- Maturity & stability assessment
- Documentation quality evaluation
- Use-case recommendations
- Agentic-engineers relevance assessment
- Key insights and market trends
- Appendix with quick reference links

**Best for:** Understanding landscape, strategic decisions, detailed comparisons, trend analysis

**Key sections:**
- Top performers in each category with justification
- Multi-agent support breakdown
- License type analysis
- Production readiness assessment
- Market trends 2025-2026

---

### 3. **AI_FRAMEWORKS_COMPARISON.md** (12 KB)
Quick reference comparison tables and decision matrices.

**Contains:**
- Framework comparison tables by category
- Provider SDK comparison (Anthropic, OpenAI, Cohere, etc.)
- Local LLM runtime comparison
- IDE/Editor integration table
- CLI/Terminal tools table
- Managed cloud services table
- Language & framework support matrix
- Key decision matrix ("Choose X if...")
- License breakdown with examples
- Maturity & stability scale
- Documentation quality scale
- GitHub activity ranking
- Tier 1/2/3 recommendations for agentic-engineers

**Best for:** Quick lookups, side-by-side comparisons, decision trees, presentations

**Example table format:**
| Framework | Type | GitHub | Stars | License | Maturity | Multi-Agent |
|-----------|------|--------|-------|---------|----------|-------------|
| CrewAI | Orchestration | [repo] | 51.5K | MIT | Production | ⭐⭐⭐⭐⭐ |

---

### 4. **RESEARCH_SUMMARY.txt** (9.3 KB)
Executive summary with key findings and actionable recommendations.

**Contains:**
- Research scope overview
- Key findings (5 major insights)
- Top framework recommendations with brief rationale
- Licensing summary
- Critical insights for agentic-engineers
- GitHub activity metrics
- Recommendations by use case
- Next steps checklist
- Market trends 2025-2026
- Data quality notes

**Best for:** Quick orientation, leadership briefing, implementation planning, team communication

**Key sections:**
- 5 major findings about market maturity
- Top 3 frameworks per category
- Specific recommendations for multi-agent systems
- Enterprise deployment options
- Local development tools
- Implementation checklist

---

## Quick Navigation by Need

### "I need to understand the current landscape"
→ Start with **AI_FRAMEWORKS_ANALYSIS.md** (Executive Summary section)

### "I need to make a decision quickly"
→ Use **AI_FRAMEWORKS_COMPARISON.md** (Key Decision Matrix section)

### "I need to brief leadership"
→ Reference **RESEARCH_SUMMARY.txt**

### "I need detailed comparison data"
→ Use **AI_FRAMEWORKS_COMPARISON.md** (comparison tables)

### "I need all the raw data"
→ Parse **ai-frameworks-research.json**

### "I need specific framework details"
→ Search **ai-frameworks-research.json** by name

### "I need to integrate new frameworks"
→ Reference **AI_FRAMEWORKS_ANALYSIS.md** (Agentic-Engineers Relevance section)

---

## Key Recommendations at a Glance

### For Multi-Agent Orchestration
1. **CrewAI** - Fastest (5.76x vs LangGraph), MIT, 51.5K stars
2. **LangGraph** - Best state management, MIT, 32.1K stars
3. **Pydantic AI** - Type-safe, MIT, 17.1K stars

### For Local Development
1. **Ollama** - Dominant (171K stars), REST API, 100+ models
2. **LM Studio** - Best GUI, freemium, cross-platform
3. **Jan.ai** - OpenAI-compatible API, AGPL, privacy-focused

### For Enterprise
1. **Semantic Kernel** - Multi-language, enterprise plugins
2. **Temporal** - Durable execution, failure recovery
3. **AWS Bedrock / Google Vertex AI** - Managed services

### For Foundation
1. **Anthropic Python SDK** - Claude 3.5 Sonnet, MIT
2. **OpenAI Python SDK** - GPT-4o/GPT-4 Turbo, MIT

### For Developer Workflow
1. **Aider** - Terminal AI pairing, git integration
2. **Continue.dev** - IDE plugin, multi-IDE support

---

## Statistics Summary

| Metric | Value |
|--------|-------|
| Total Frameworks | 45 |
| Open-Source | 30 (67%) |
| Production-Ready | 38 (84%) |
| Excellent Documentation | 18 (40%) |
| Full Multi-Agent Support | 20 (44%) |
| MIT Licensed | 20 (44%) |
| Apache 2.0 Licensed | 10 (22%) |

### By Category
- Agent Orchestration: 9
- IDE/Editor: 7
- CLI/Terminal: 5
- Python/Runtime: 13
- Local LLM: 5
- Managed Services: 3

### By Maturity
- Production: 38
- Stable: 5
- Maintenance: 1
- Educational: 1

---

## Framework Categories Explained

### Agent Orchestration Frameworks
Specialized frameworks for building and coordinating multi-agent systems.
- **Key players:** CrewAI, LangGraph, Pydantic AI, Semantic Kernel, AutoGen
- **Best for:** Multi-agent team workflows, complex orchestration
- **Typical use:** Building agents that coordinate on tasks

### IDE/Editor Integration
Code editors with AI capabilities, not typically used for agent orchestration.
- **Key players:** Continue.dev, Zed, Cursor, GitHub Copilot
- **Best for:** Code writing and completion
- **Note:** Low relevance to agentic-engineers agent orchestration

### CLI/Terminal Tools
Command-line tools for AI-assisted development in the terminal.
- **Key players:** Aider, Mentat, Plandex
- **Best for:** Pair programming, terminal workflows
- **Typical use:** Interactive coding assistance

### Python/Runtime SDKs
Libraries and SDKs for building AI applications in Python and other languages.
- **Key players:** Anthropic SDK, OpenAI SDK, Cohere SDK, Vercel AI
- **Best for:** Foundation layer for LLM integration
- **Typical use:** Direct API access to LLM providers

### Local LLM Frameworks
Tools for running open-source language models locally without cloud connectivity.
- **Key players:** Ollama, LM Studio, Jan.ai, GPT4All
- **Best for:** Offline development, privacy, cost optimization
- **Typical use:** Local model inference and testing

### Managed Services
Cloud-based AI platforms provided by major cloud providers.
- **Key players:** AWS Bedrock, Google Vertex AI, Azure OpenAI
- **Best for:** Enterprise deployment, scale, security
- **Typical use:** Production agent systems at enterprise scale

---

## How to Use This Research

### For System Architecture Decisions
1. Review **AI_FRAMEWORKS_ANALYSIS.md** section: "Agentic-Engineers Framework Relevance Assessment"
2. Check tier recommendations in **AI_FRAMEWORKS_COMPARISON.md**
3. Reference decision matrices for your specific requirements

### For Implementation Planning
1. Review **RESEARCH_SUMMARY.txt** section: "NEXT STEPS FOR AGENTIC-ENGINEERS"
2. Use **AI_FRAMEWORKS_COMPARISON.md** key decision matrices
3. Reference **AI_FRAMEWORKS_ANALYSIS.md** for detailed integration guidance

### For Team Communication
1. Use **RESEARCH_SUMMARY.txt** for executive briefings
2. Share **AI_FRAMEWORKS_COMPARISON.md** for quick reference
3. Reference specific GitHub stars/metrics from **AI_FRAMEWORKS_ANALYSIS.md**

### For Technical Deep Dives
1. Extract framework details from **ai-frameworks-research.json**
2. Review full feature lists in **AI_FRAMEWORKS_ANALYSIS.md** category sections
3. Check GitHub repositories for latest documentation

### For Competitive Analysis
1. Review **RESEARCH_SUMMARY.txt** section: "GitHub Activity Metrics"
2. Check maturity assessment in **AI_FRAMEWORKS_ANALYSIS.md**
3. Compare licensing and community size metrics

---

## Key Statistics You Should Know

### Market Leaders
- **Ollama** dominates local runtimes with 171K GitHub stars
- **CrewAI** is fastest-growing orchestration framework (51.5K stars)
- **LangGraph** most starred in orchestration after AutoGen
- **Continue.dev** leading open-source IDE integration

### Maturity
- 84% of frameworks are production-ready (38/45)
- Only 1 framework in maintenance mode (AutoGen)
- 1 educational/experimental framework (Swarm)

### Community
- Top tier has 30K+ stars (CrewAI, LangGraph, Semantic Kernel, Ray, etc.)
- Strong engagement across MIT-licensed frameworks
- Clear consolidation around 3-5 market leaders

### Support
- 89% of frameworks have good or excellent documentation
- Model-agnostic approach dominates (reduce vendor lock-in)
- Open-source community providing strong support

---

## Important Notes

### Data Freshness
- Research completed: May 16, 2026
- GitHub stars and commit dates current as of research date
- Framework landscapes evolve; recommend reviewing annually

### Scope Limitations
- Focused on agent orchestration and related frameworks
- Some frameworks may have niche use cases not fully covered
- Proprietary frameworks included for reference but not endorsed

### Update Strategy
- Keep JSON file updated with new framework releases
- Monitor top framework GitHub repositories monthly
- Update comparison matrices as features evolve
- Track emerging frameworks in orchestration space

---

## Quick Links to Key Resources

### Orchestration Leaders
- CrewAI: https://docs.crewai.com
- LangGraph: https://docs.langchain.com/langgraph
- Pydantic AI: https://ai.pydantic.dev

### Essential Tools
- Ollama: https://ollama.com
- Continue.dev: https://continue.dev
- Aider: https://aider.chat

### Foundation SDKs
- Anthropic: https://docs.anthropic.com
- OpenAI: https://platform.openai.com/docs
- Cohere: https://docs.cohere.com

### Enterprise Options
- Semantic Kernel: https://learn.microsoft.com/semantic-kernel
- Temporal: https://temporal.io
- AWS Bedrock: https://aws.amazon.com/bedrock

---

## Document Maintenance

### Files Summary
- **JSON**: 58 KB, 45 frameworks, fully structured
- **Analysis MD**: 16 KB, comprehensive findings
- **Comparison MD**: 12 KB, quick reference tables
- **Summary TXT**: 9.3 KB, executive summary
- **Total**: ~95 KB organized documentation

### Version Info
- Research Date: May 16, 2026
- Data Completeness: Comprehensive (all 45 frameworks)
- Update Frequency: Recommend annual review

---

## How to Extend This Research

### To Add New Framework
1. Add entry to `ai-frameworks-research.json`
2. Include all required fields (use existing entries as template)
3. Update category summary statistics
4. Update relevant comparison tables in MD files

### To Update Existing Framework
1. Modify JSON entry with new data
2. Update category statistics if relevant
3. Update recommendation tiers if maturity changed
4. Update relevant MD tables

### To Create New Comparison
1. Query `ai-frameworks-research.json` for specific fields
2. Create new table in `AI_FRAMEWORKS_COMPARISON.md`
3. Reference in index sections

---

**Last Updated:** May 16, 2026  
**Comprehensive Research of 45 AI Frameworks**  
**For:** Agentic-Engineers Framework Selection & Integration Strategy
