---
name: Integration Guide
description: How to invoke and use the agentic-engineers skill framework
---

# agentic-engineers Integration Guide

Complete framework for orchestrating software engineering work across 10 specialist agents.

## Quick Start

### 1. Install for your harness

```bash
# Claude CLI
make -f Makefile.platform install-claude

# OR Copilot CLI
make -f Makefile.platform install-copilot
```

This installs rendered skills to:
- `~/.claude/` (Claude CLI)
- `~/.copilot/` (Copilot CLI)

### 2. Invoke the General Orchestrator

```bash
claude ask "You are the General Orchestrator. Route this task: [task description]"
```

The orchestrator evaluates against the 6-point decision tree and routes to the appropriate specialist agent.

### 3. Follow the routing decision

The orchestrator returns a **Routing Decision**:

```
ROUTING DECISION
────────────────
Agent: Engineer
Confidence: 0.88
Rationale: Clear scope, well-defined plan
Task Summary: Implement JWT validation...
```

### 4. Invoke the specialized agent

```bash
claude ask "You are the Engineer agent (from src/roles/engineer.md). Execute: [task]"
```

The agent works and returns a **HANDBACK** with results and metrics.

## Complete Skill Map

| Phase | Role | Model | Purpose |
|-------|------|-------|---------|
| **6.0** | General Orchestrator | Haiku | Route tasks to specialists (6-point decision tree) |
| **6.1** | Model Engineer | Haiku | Track token/time efficiency, update confidence tables |
| **6.1** | Quality Gate Aggregator | Haiku | Aggregate sub-agent HANDBACKs, detect trends |
| **6.1** | Config Enforcement Verifier | Haiku | Validate fixes resolved issues |
| **7** | Engineer | Haiku | Execute well-scoped planned tasks |
| **7** | Senior Engineer | Sonnet | Analyze/plan complex unscoped work |
| **7** | Quality Engineer | Sonnet | Post-implementation validation (8-point checklist) |
| **8** | Lead Engineer | Sonnet | Code review (8-point checklist) |
| **8** | Security Engineer | Opus | Threat modeling + vulnerability assessment |
| **8** | Principal Engineer | Opus | Cross-service architecture design |

## Workflow Examples

### Simple Task (Well-Scoped)

```
1. General Orchestrator: "This looks like planned, scoped work → Engineer"
2. Engineer: Executes step-by-step
3. Quality Engineer: Validates 8-point checklist
4. Lead Engineer: Code review (8-point checklist)
5. HANDBACK with metrics flows to Model Engineer + QG Aggregator
```

### Complex Task (Unscoped)

```
1. General Orchestrator: "Complex, no plan → Senior Engineer"
2. Senior Engineer: Root cause analysis + 3 design options + recommended plan
3. HANDBACK (plan) goes to Engineer
4. Engineer: Executes the plan
5. Quality Engineer: Validates
6. Lead Engineer: Reviews
7. Model Engineer: Analyzes efficiency
```

### Security-Scoped Task

```
1. General Orchestrator: "Security-focused → Security Engineer"
2. Security Engineer: STRIDE threat modeling + vulnerability assessment
3. HANDBACK with threat model goes to Principal Engineer (if architectural)
   OR back to appropriate executor (if code/config)
4. Executor implements mitigations
5. Security Engineer validates mitigations
```

### Cross-Service Refactor

```
1. General Orchestrator: "Affects 3 repos → Principal Engineer"
2. Principal Engineer: 2-3 design options + recommendations + roadmap
3. Senior Engineer: Detailed execution plan for each phase
4. Engineer: Implements each phase (possibly multiple Engineers in parallel)
5. Quality Engineer + Lead Engineer: Validate each phase
6. Security Engineer: Reviews security implications
```

## HANDBACK Protocol

Every agent returns a **HANDBACK** message:

```
HANDBACK
────────
Agent: [name]
Task: [original task]
Status: [COMPLETE | ESCALATE | REWORK]
Quality Score: [0-100] (if applicable)
Metrics:
  - token_used: N
  - duration: Xs
  - quality_score: N/100
  - routing_confidence: 0.XX
  - [agent-specific metrics]
Result: [summary of work]
Next Steps: [if any]
```

### Where HANDBACKs Flow

1. **Model Engineer:** Receives all HANDBACKs
   - Analyzes token_used, duration, quality_score, routing_confidence
   - Updates confidence tables for future routing decisions
   - Weekly trend reports

2. **Quality Gate Aggregator:** Receives HANDBACK status (COMPLETE/ESCALATE/REWORK)
   - Tracks quality trends across all agents
   - Detects anomalies (escalation spikes, quality drops)
   - Recommends threshold adjustments

3. **Config Enforcement Verifier:** Receives HANDBACKs for fixes
   - Validates fixes actually resolved underlying issues
   - Tracks success rates by issue type
   - Updates confidence scores for auto-fixes

## Invocation Patterns

### Via Claude CLI

```bash
claude ask "You are the General Orchestrator. 

Route this task:
[task description]

Use the 6-point decision tree from AGENTS.md."
```

### Via Copilot CLI

```bash
copilot ask "You are the Engineer agent (from ~/.copilot/roles/engineer.md).

Execute this task:
[task description]

Return HANDBACK with results."
```

## Directory Structure

```
ers/
├── AGENTS.md                  ← General Orchestrator definition
├── SKILLS.md                  ← Skills index
├── INTEGRATION.md             ← This file
├── src/
│   └── roles/                 ← 10 agent skill files (provider-agnostic)
│       ├── engineer.md
│       ├── senior-engineer.md
│       ├── quality-engineer.md
│       ├── lead-engineer.md
│       ├── security-engineer.md
│       ├── principal-engineer.md
│       ├── model-engineer.md
│       ├── quality-gate-aggregator.md
│       ├── config-enforcement-verifier.md
│       └── general-orchestrator.md
├── render/
│   └── main.py                ← Rendering pipeline (generic → provider-specific)
├── models.yaml                ← Model registry (canonical + all provider mappings)
├── dist/                      ← Generated (do not commit)
│   ├── copilot/roles/         ← 10 rendered skills (OpenAI models)
│   └── claude/roles/          ← 10 rendered skills (Claude models)
├── Makefile.platform          ← Rendering targets
└── scripts/
    └── install-platform.sh    ← Installation script

~/.claude/                      ← Installed Claude CLI skills
├── roles/
│   └── [10 rendered skill files with claude-haiku, claude-sonnet, claude-opus]
└── models.json

~/.copilot/                     ← Installed Copilot CLI skills
└── roles/
    └── [10 rendered skill files with gpt-4o-mini, gpt-4, gpt-4o]
```

## Metrics Collection (Delegate Protocol)

HANDBACKs contain structured metrics for later analysis:

```
Model Engineer collects:
  - tokens_used
  - duration
  - quality_score
  - routing_confidence
  - task_complexity
  - task_category

Quality Gate Aggregator collects:
  - status (COMPLETE/ESCALATE/REWORK)
  - quality_score
  - agent_name

Config Enforcement Verifier collects:
  - issue_type
  - fix_applied
  - fix_success
  - verification_method
```

**Future:** Store these metrics in DynamoDB/S3 for trend analysis and BI dashboards.

## Customization

### Add a New Skill

1. Create `src/roles/{agent-name}.md` with frontmatter + structure
2. Add entry to `models.yaml` with provider mappings
3. Render: `make render-all`
4. Install: `make install-claude` (or your provider)

### Change a Model Mapping

Edit `models.yaml`:
```yaml
your_role:
  canonical: "claude-haiku"
  providers:
    copilot: "gpt-4o-mini"     ← edit here
    claude: "claude-haiku-4-5"
    openai: "gpt-4o-mini"
```

Then re-render: `make render-all`

### Add a New Provider

1. Add provider config to `models.yaml` (provider_features section)
2. Add model mappings for all roles
3. Update `Makefile.platform` with render target
4. Render: `make render-{provider}`

## Troubleshooting

**Skills not loading?**
```bash
# Verify installation
ls ~/.claude/roles/
ls ~/.copilot/roles/

# Re-install
make install-claude
make install-copilot
```

**Wrong models in output?**
```bash
# Check models.yaml
grep -A 5 "your_role:" models.yaml

# Re-render
make render-all
```

**HANDBACK not being collected?**
- Ensure each agent returns HANDBACK with metrics
- Check Model Engineer is parsing HANDBACK format
- Verify Quality Gate Aggregator receiving status updates

## Next Steps

**Short-term:**
- Test each skill locally via Claude/Copilot CLI
- Validate HANDBACK format matches protocol
- Run integration test: Orchestrator → Engineer → Quality Engineer workflow

**Medium-term:**
- Implement metrics persistence (DynamoDB/S3)
- Build dashboard for Model Engineer trends
- Add webhook integration for CI/CD triggers

**Long-term:**
- Automated task routing via webhook (GitHub events, linear issues, etc)
- Real-time metrics dashboard
- Cost optimization via vendor routing
- Multi-provider failover

---

## Support

For questions about specific skills, see:
- [AGENTS.md](AGENTS.md) — Orchestrator logic
- [SKILLS.md](SKILLS.md) — Skills index
- `src/roles/*.md` — Individual skill definitions
- `models.yaml` — Model mappings and provider features
