# Source Agent Definitions

This directory contains the canonical, provider-independent definitions of all agentic-engineers agents.

## Structure

```
src/agents/
├── engineer.md                          # Implementation executor
├── senior-engineer.md                   # Complex architecture & debugging
├── orchestrator.md                      # Task routing & metrics
├── principal-engineer.md                # Organization-wide strategy
├── lead-engineer.md                     # Code reviews & quality
├── security-engineer.md                 # Security & compliance
├── quality-engineer.md                  # Testing strategy & automation
├── model-engineer.md                    # Cost optimization
├── metrics.md                           # Token tracking
├── testing.md                           # Test execution
├── spec-engineer.md                     # Specification validation
├── healing-engineer.md                  # System debugging
└── spec-engineer-orchestrator.md        # Spec + routing
```

## Format

Each agent definition follows this structure:

```markdown
---
name: Agent Name
description: Brief description of what this agent does
model: claude-haiku-4.5 | claude-sonnet-5 | claude-opus-5 | claude-fable-5
---

# Agent Name

Detailed explanation of the agent's role and responsibilities.

## Your Responsibilities

1. Responsibility 1
2. Responsibility 2
...

## When Escalated To

- Condition 1 → Next agent
- Condition 2 → Next agent

## Example Workflow

1. Step 1
2. Step 2
...

Your goal is to...
```

## Agent Categories

### Core Agents (4)
These are the primary agents for task execution:
- **engineer** — Executes well-scoped, planned work
- **senior-engineer** — Handles complex, unscoped problems
- **orchestrator** — Routes tasks and optimizes efficiency
- **principal-engineer** — Organization-wide architecture

### Specialized Agents (5)
Domain-specific agents for particular tasks:
- **lead-engineer** — Code reviews and critical issues
- **security-engineer** — Security architecture and compliance
- **quality-engineer** — Testing strategy and automation
- **spec-engineer** — Specification validation and drift detection
- **healing-engineer** — System health and debugging

### Support Agents (4)
Infrastructure and operational agents:
- **model-engineer** — Token efficiency and cost optimization
- **metrics** — Token usage tracking and reporting
- **testing** — Test execution and coverage validation
- **spec-engineer-orchestrator** — Spec validation + task routing

## Model Assignment

Agents use appropriate models based on task complexity:

| Model | Cost | Used For | Agents |
|-------|------|----------|--------|
| **Haiku** | 1x | Well-scoped work, implementation | engineer, orchestrator, metrics, testing |
| **Sonnet** | 3x | Complex reasoning, design, reviews | senior-engineer, quality-engineer, lead-engineer, security-engineer, spec-engineer, healing-engineer, model-engineer, spec-engineer-orchestrator |
| **Opus** | 5x | High-stakes decisions, security, architecture | principal-engineer, security-engineer |

## Editing Agents

To update an agent definition:

1. Edit the source file:
   ```bash
   vim src/agents/engineer.md
   ```

2. Update the Markdown content (description, responsibilities, etc.)

3. Install to all targets (renders and installs):
   ```bash
   make install
   ```
   This automatically:
   - Renders agents from `src/agents/` 
   - Installs to `~/.copilot/agents/` (Copilot CLI)
   - Installs to `~/.claude/agents/` (Claude Code)
   - And all associated skills

4. Verify the output:
   ```bash
   head ~/.copilot/agents/engineer.agent.md
   ```

5. Test with Copilot CLI:
   ```bash
   copilot --agent=engineer --prompt "..."
   ```

6. Commit:
   ```bash
   git add src/agents/engineer.md
   git commit -m "Update engineer agent description"
   ```

## Rendering Pipeline

These source definitions are rendered to Copilot CLI format via:

```
src/agents/*.md → [renderer/scripts/render-copilot-agents.py] → ~/.copilot/agents/*.agent.md
```

**Key points**:
- Sources are the "ground truth"
- Output files (`~/.copilot/agents/*.agent.md`) are generated, not edited
- Re-rendering is idempotent (safe to run multiple times)
- See `AGENT-RENDERING-PIPELINE.md` for details

## Adding New Agents

To add a new agent:

1. Create new source file:
   ```bash
   touch src/agents/new-agent.md
   ```

2. Write the agent definition (use existing agents as templates):
   ```markdown
   ---
   name: New Agent
   description: What this agent does
   model: claude-haiku-4.5
   ---
   
   # New Agent
   ...
   ```

3. Install (rendering is automatic):
   ```bash
   make install
   ```

4. Test:
   ```bash
   copilot --agent=new-agent --prompt "..."
   ```

5. Commit both source and update documentation

## YAML Frontmatter

Every agent must have valid YAML frontmatter with three required fields:

| Field | Type | Example | Required |
|-------|------|---------|----------|
| `name` | string | "Engineer" | Yes |
| `description` | string | "Executes well-scoped implementation tasks..." | Yes |
| `model` | string | "claude-haiku-4.5" | Yes |

The renderer validates these fields and will fail if any are missing.

## Best Practices

1. **Keep descriptions concise**: 1-2 sentences, under 200 characters
2. **Be specific about responsibilities**: Not "helps with code" but "Executes well-scoped implementation tasks following TDD patterns"
3. **Clear escalation paths**: When should this agent delegate? To whom?
4. **Example workflow**: Include a concrete example of how the agent works
5. **Goal statement**: End with "Your goal is to..."
6. **Consistent formatting**: Use same markdown structure as other agents

## Agent Autonomy Guidance

All agents operate in **reduced autonomy mode**. This means:

### When to Continue Working Autonomously

- ✓ Current task is complete AND
- ✓ Additional todos exist in `TODO.md` (repository root) marked as pending (`- [ ]`)
- ✓ TODO.md is the ONLY source of truth for remaining work
- → **Action:** Continue to next todo and report progress

### When to Pause and Wait for Input

- ✓ Assigned task scope is complete
- ✓ All success criteria are met
- ✓ No documented additional todos in TODO.md (all marked `- [x]` or no pending items)
- ✓ Uncertainty about whether more work exists
- → **Action:** Summarize completion and explicitly state: "Pausing here. Ready for next task or input."

### TODO Tracking (MANDATORY)

**Use TODO.md in repository ONLY. Do NOT use SQL databases, session artifacts, or spreadsheets.**

- Agents read `TODO.md` from repository root to check for remaining work
- Todos are marked as `- [ ]` (pending) or `- [x]` (done) in markdown
- Agents update TODO.md directly by editing the file
- TODO.md is the canonical, authoritative source of all work items
- **PROHIBITED:** Do not use SQL `todos` table, `todo_deps`, session workspace plan.md, or any external tracking

### Why This Matters

Reduced autonomy prevents:
- ✗ Agents inventing work that wasn't requested
- ✗ Scope creep from well-defined tasks
- ✗ Unauthorized continuation beyond assigned boundaries

But maintains autonomy for:
- ✓ Known multi-step tasks with explicit todos in TODO.md
- ✓ Continuous improvement within documented scope
- ✓ Iterative work on complex features

### Implementation Pattern

Every agent definition should include a section like this:

```markdown
## Autonomy & Task Boundaries

When current task is complete, check TODO.md for remaining work:
- Pending todos (`- [ ]`) in TODO.md? → Continue to next
- All todos done or TODO.md doesn't exist? → Pause and ask

Always pause if uncertain about scope boundaries.
```

See individual agent definitions (`engineer.md`, `senior-engineer.md`, etc.) for role-specific autonomy guidance.

## Documentation

- `AGENT-RENDERING-PIPELINE.md` — How sources render to Copilot CLI format
- `README.md` in `~/.copilot/agents/` — User-facing documentation
- [Copilot CLI Documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli)

## See Also

- `renderer/` — Build system for rendering agents
- `renderer/scripts/render-copilot-agents.py` — Python renderer
- `renderer/Makefile` — Build targets
