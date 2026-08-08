# Agent Availability Verification Guide

## Overview

The Claude Code harness includes a comprehensive agent verification system that validates all 8 agents are available, correctly configured, and can be instantiated without errors.

This guide covers:
- How verification works
- Understanding verification reports
- Troubleshooting common issues
- Adding new agents and passing verification

---

## Quick Start

### Running Verification

From the repository root:

```bash
# Run verification and print report
python3 -c "from src.claude.agent_verifier import AgentVerifier; AgentVerifier().print_report(AgentVerifier().verify_all_agents())"

# Generate JSON report
python3 -c "from src.claude.agent_verifier import AgentVerifier; AgentVerifier().generate_json_report(Path('agent_verification.json'))"
```

### Startup Check

The startup checker runs automatically when the Claude Code harness initializes:

```bash
# Run startup check
python3 -c "from src.claude.startup_check import StartupChecker; print(StartupChecker().get_quick_status())"

# Clear cached results
python3 -c "from src.claude.startup_check import StartupChecker; StartupChecker().clear_cache()"
```

---

## Understanding Verification Results

### Agent Enumeration

Verifies that all expected agents are found:

```
✅ enumeration [PASS]
  Agents: 8/8 found
  Expected: orchestrator, engineer, senior-engineer, lead-engineer,
            quality-engineer, model-engineer, principal-engineer, security-engineer
```

### Agent Definition

Each agent is validated for:

- **name** (required): Agent identifier (lowercase, hyphen-separated for multi-word names)
- **role** (required): Same as name in current framework
- **model** (required): One of the known Claude models (canonical format with dots)
- **description** (recommended): Brief description of agent's purpose
- **effort** (optional): Task complexity estimate (low/medium/high/max)
- **thinking_mode** (optional): Extended thinking enabled/disabled

Valid models (canonical source format):
- Haiku: `claude-haiku-4.5`, `claude-haiku-4.6`
- Sonnet: `claude-sonnet-4.5`, `claude-sonnet-4.6`
- Opus: `claude-opus-4.5`, `claude-opus-4.6`, `claude-opus-4.7`, `claude-opus-4.8`

### Agent Instantiation

Verifies the agent definition can be instantiated by:
- Checking all required fields are present and valid
- Validating model is in KNOWN_MODELS
- Ensuring agent file is readable and non-empty

Example result:

```
✅ engineer_instantiation [PASS]
  Model: claude-haiku-4.5
  Instantiable: true
```

### Agent Routing

Verifies agents are assigned the correct models according to the routing table:

| Agent | Expected Model | Rationale |
|-------|---|---|
| orchestrator | claude-haiku-4.5 | Cheap routing, no thinking |
| engineer | claude-haiku-4.5 | Cheap execution, well-scoped tasks |
| senior-engineer | claude-sonnet-4.5 | Multi-file work, planning |
| lead-engineer | claude-sonnet-4.6 | Code review, architecture |
| quality-engineer | claude-sonnet-4.6 | Post-implementation validation |
| model-engineer | claude-sonnet-4.5 | HANDBACK metrics analysis |
| principal-engineer | claude-opus-4.6 | Hard debugging, cross-service |
| security-engineer | claude-fable-5 | Threat modeling, compliance |

---

## Troubleshooting

### "Agent file not found"

**Problem:** Agent markdown file doesn't exist or is in the wrong location.

**Solution:**
1. Verify file exists: `ls src/agents/{agent-name}-agent.md`
2. Ensure filename matches agent name in frontmatter:
   - Frontmatter: `name: my-agent`
   - Filename: `my-agent-agent.md`
3. If missing, create the file or restore from git

### "Missing required field: model"

**Problem:** Agent markdown has no `model:` field in frontmatter.

**Solution:**
1. Open `src/agents/{agent-name}-agent.md`
2. Add `model:` field to YAML frontmatter:
   ```yaml
   ---
   name: my-agent
   description: My agent does X
   model: claude-haiku-4.5
   ---
   ```
3. Use canonical format (with dots): `claude-haiku-4.5` not `haiku` or `claude-haiku_4_5`

### "Unknown model"

**Problem:** Agent uses a model not in KNOWN_MODELS.

**Solution:**
1. Check the model name format (must use dots for versions):
   - ✅ Correct: `claude-haiku-4.5`
   - ❌ Wrong: `gpt-4`, `claude-haiku`, `claude-haiku_4_5`
2. Verify model exists in valid set:
   - Haiku: 4.5, 4.6
   - Sonnet: 4.5, 4.6
   - Opus: 4.5, 4.6, 4.7, 4.8
3. Update agent to use valid model:
   ```yaml
   model: claude-sonnet-4.6
   ```

### "Model mismatch for agent"

**Problem:** Agent's assigned model doesn't match expected routing.

**Solution:**
1. Check the expected model from the routing table above
2. Compare to the agent's current model:
   ```bash
   grep "^model:" src/agents/{agent-name}-agent.md
   ```
3. Update if incorrect:
   ```yaml
   model: claude-sonnet-4.6  # Use correct model
   ```
4. Re-run verification to confirm

### Agent enumeration failed

**Problem:** Not all 8 agents were found.

**Solution:**
1. List agents found:
   ```bash
   ls src/agents/*-agent.md
   ```
2. Check for missing agents (should have 8 total):
   - orchestrator-agent.md
   - engineer-agent.md
   - senior-engineer-agent.md
   - lead-engineer-agent.md
   - quality-engineer-agent.md
   - model-engineer-agent.md
   - principal-engineer-agent.md
   - security-engineer-agent.md
3. If missing, restore from git or create new agent (see "Adding New Agents" below)

### Cache-related issues

**Problem:** Startup check is using stale cached results.

**Solution:**
```bash
python3 -c "from src.claude.startup_check import StartupChecker; StartupChecker().clear_cache()"
```

The cache TTL is 1 hour by default. Cache is automatically invalidated if any agent file changes.

---

## Adding New Agents

### Step 1: Create Agent Markdown File

Create `src/agents/{agent-name}-agent.md`:

```markdown
---
name: my-agent
description: Brief description of what this agent does
model: claude-haiku-4.5
effort: medium
thinking_mode: enabled
---

# My Agent

## Your Responsibilities

1. Responsibility one
2. Responsibility two

## Boundaries

- Do not do X
- Do not do Y
```

### Step 2: Validate Agent Definition

```bash
python3 -c "
from src.claude.agent_verifier import AgentVerifier
from pathlib import Path

verifier = AgentVerifier()
verifier.enumerate_agents()
report = verifier.verify_all_agents()
verifier.print_report(report)
"
```

All verification checks must pass (status=PASS for all agents).

### Step 3: Register Agent in AGENTS.md

Update `src/AGENTS.md` Agent Roster table:

```markdown
| # | Role | Model | Thinking | Cost/Task | Purpose |
|---|------|-------|----------|-----------|---------|
| 9 | **My Agent** | `claude-haiku-4.5` | ❌ | $0.03 | Brief purpose |
```

### Step 4: Run Full Test Suite

```bash
python3 -m pytest tests/claude/test_agent_verifier.py -v
```

All tests must pass.

### Step 5: Update routing rules (if applicable)

If your agent has specific routing rules, update:
- `src/claude/agent_verifier.py` - Add to expected_routing dict
- `src/agents/README.md` - Update routing decision tree
- `src/AGENTS.md` - Update escalation triggers

---

## Verification Report Format

### JSON Report Structure

```json
{
  "timestamp": "2026-05-30T10:00:00.123456",
  "total_agents": 8,
  "passing": 25,
  "failing": 0,
  "warnings": 0,
  "results": [
    {
      "agent_name": "enumeration",
      "status": "PASS",
      "model": null,
      "errors": [],
      "warnings": [],
      "metadata": {
        "agents_found": 8,
        "expected_count": 8
      }
    },
    {
      "agent_name": "engineer",
      "status": "PASS",
      "model": "claude-haiku-4.5",
      "errors": [],
      "warnings": [],
      "metadata": {
        "name": "engineer",
        "role": "engineer",
        "model": "claude-haiku-4.5",
        "...": "..."
      }
    }
  ]
}
```

### Report Interpretation

- **passing** ≥ 25: All agents verified successfully (8 agents × ~3 checks each)
- **failing** > 0: At least one agent failed — investigate errors
- **warnings** > 0: Non-critical issues (e.g., missing description)

---

## Performance

### Startup Check Cache

The startup checker caches verification results to avoid repeated file I/O:

- **Cache location**: `~/.cache/agentic-engineers/agent_verification_cache.json`
- **TTL**: 3600 seconds (1 hour)
- **Invalidation**: Automatic if any agent file changes

Cache hit reduces startup overhead from ~200ms to ~1ms.

### Verification Time

Typical timings:
- Full verification (all checks): ~50–100ms
- Enumeration only: ~10–20ms
- Cache hit: ~1ms

---

## Integration with CI/CD

### Pre-commit Hook

Add to `.githooks/pre-commit`:

```bash
python3 -m pytest tests/claude/test_agent_verifier.py -v --tb=short
if [ $? -ne 0 ]; then
  echo "❌ Agent verification failed"
  exit 1
fi
```

### GitHub Actions

Add to `.github/workflows/verify-agents.yml`:

```yaml
- name: Verify Agent Availability
  run: |
    python3 -m pytest tests/claude/test_agent_verifier.py -v --cov=src/claude
    python3 -c "from src.claude.agent_verifier import AgentVerifier; AgentVerifier().print_report(AgentVerifier().verify_all_agents())"
```

---

## Support

For questions or issues:
1. Check this guide's troubleshooting section
2. Review agent verification logs: `python3 -m pytest tests/claude/test_agent_verifier.py -v -s`
3. Open an issue at https://github.com/anomalyco/agentic-engineers/issues
