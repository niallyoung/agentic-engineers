# Claude Code Harness Extension Guide

This guide covers advanced customization and extension points in the Claude Code harness.

## Overview

The Claude Code harness can be extended through configuration files and custom agent/skill definitions. Extensions allow you to:

- Override model assignments for specific roles
- Customize effort-based model selection
- Add new agent roles or modify existing ones
- Configure token budgets and timeouts
- Apply per-project settings

All customizations are made via JSONC configuration files in `~/.claude/config/` or project-specific `.claude/` directories.

## Configuration File Locations

```
~/.claude/
├── config/
│   ├── claude.jsonc              # Global harness config (model aliases, timeouts)
│   ├── agents/                   # Agent definitions (rendered)
│   │   ├── orchestrator.md
│   │   ├── engineer.md
│   │   └── ...
│   └── skills/                   # Skill documentation (rendered)
│
~/.claude/projects/
├── {project-name}/
│   └── agents.jsonc              # Per-project agent overrides
│
{project-root}/
└── .claude/
    ├── agents.jsonc              # Project-specific agent config
    ├── skills.jsonc              # Project-specific skill config
    └── claude.jsonc              # Project-specific harness config
```

## Override Model Pins

### Global Model Aliases

Edit `~/.claude/config/claude.jsonc` to customize model mappings:

```jsonc
// Global model alias configuration
{
  "models": {
    "aliases": {
      "haiku": "claude-haiku-4.5",
      "sonnet": "claude-sonnet-4",
      "opus": "claude-opus-4"
    }
  }
}
```

### Per-Session Model Overrides

Override model assignments for a specific session:

```jsonc
// ~/.claude/sessions/{session-id}/config.jsonc
{
  "model_overrides": {
    "orchestrator": "opus",        // Always use Opus
    "engineer": "sonnet",          // Force Sonnet for engineers
    "senior-engineer": "opus",     // Upgrade senior engineers
    "quality-engineer": "haiku"    // Use cheaper model for QE
  }
}
```

### Per-Project Model Overrides

Create project-specific model assignments:

```jsonc
// ~/git/agentic-engineers/.claude/agents.jsonc
{
  "agents": {
    "engineer": {
      "model": "sonnet",           // Override global default
      "temperature": 0.3,          // Custom parameter
      "max_tokens": 4000
    },
    "orchestrator": {
      "model": "opus",             // High-complexity projects use Opus
      "temperature": 0.5,
      "max_tokens": 8000
    }
  }
}
```

## Override Effort Tiers

Customize which model is used for each effort level:

```jsonc
// ~/.claude/config/claude.jsonc
{
  "effort_tiers": {
    "low": "haiku",        // Simple, <30 min: Use Haiku
    "medium": "sonnet",    // Moderate, 1-2 hrs: Use Sonnet
    "high": "opus"         // Complex, 2+ hrs: Use Opus
  }
}
```

Or override per-project:

```jsonc
// ~/.claude/projects/my-project/agents.jsonc
{
  "effort_tiers": {
    "low": "sonnet",       // This project requires more accuracy
    "medium": "opus",
    "high": "opus"
  }
}
```

## Add New Agent Role

### Step 1: Create Agent Definition

Create a new agent file in `~/.claude/config/agents/`:

```markdown
# ~/.claude/config/agents/my-new-agent.md

---
frontmatter:
  role: my-new-agent
  model: claude-opus-4
  temperature: 0.7
  max_tokens: 8000
---

# My Custom Agent

**Purpose:** Describe what this agent does.

**Capabilities:**
- Capability 1
- Capability 2

**Constraints:**
- Constraint 1
- Constraint 2

## Responsibilities

- Responsibility 1
- Responsibility 2

## Example DELEGATE

...example block...
```

### Step 2: Register Agent in Configuration

Add the agent to `~/.claude/config/claude.jsonc`:

```jsonc
{
  "agents": {
    "my-new-agent": {
      "file": "agents/my-new-agent.md",
      "model": "claude-opus-4",
      "enabled": true
    }
  }
}
```

### Step 3: Update Routing Rules

If your new agent should receive certain types of tasks, update the routing decision tree:

```jsonc
// ~/.claude/config/claude.jsonc
{
  "routing_rules": {
    "my-new-agent": {
      "conditions": ["task_type == 'my-domain'"],
      "confidence": 0.9
    }
  }
}
```

### Step 4: Test Agent Loading

Restart Claude Code and verify the agent loads:

```bash
# Check console for agent load errors
claude-code start

# In browser, verify agent appears in UI
# (Help → Agents or similar, depending on UI layout)
```

## Token Budget Tuning

### Session-Level Budget

Set limits for a single session:

```jsonc
// ~/.claude/config/claude.jsonc
{
  "token_budget": {
    "session_limit": 1000000,   // Max tokens per session (1M)
    "daily_limit": 5000000,      // Max tokens per calendar day (5M)
    "hard_stop": true            // Block when limit reached (vs. warn)
  }
}
```

### Cost-Based Budget

Enforce spending limits instead of token counts:

```jsonc
// ~/.claude/config/claude.jsonc
{
  "cost_budget": {
    "session_limit_usd": 10.00,    // Max $10 per session
    "daily_limit_usd": 50.00,       // Max $50 per day
    "hard_stop": false              // Warn but don't block
  }
}
```

### Budget Allocation by Agent

Assign per-agent token quotas:

```jsonc
// ~/.claude/config/claude.jsonc
{
  "agent_budgets": {
    "orchestrator": 100000,      // 100K tokens
    "engineer": 500000,          // 500K tokens
    "quality-engineer": 50000    // 50K tokens
  }
}
```

## Custom Timeout Policies

### Global Timeouts

Set default timeouts for all operations:

```jsonc
// ~/.claude/config/claude.jsonc
{
  "timeouts": {
    "skill_invocation": 30000,    // Skills must complete within 30s
    "handback_validation": 10000, // Schema validation within 10s
    "code_execution": 60000,      // Linting/tests within 60s
    "agent_response": 120000      // Agents must respond within 120s
  }
}
```

### Per-Agent Timeouts

Customize timeouts for specific agents:

```jsonc
// ~/.claude/config/claude.jsonc
{
  "agent_timeouts": {
    "principal-engineer": 300000,    // 5 min for complex work
    "engineer": 120000,              // 2 min for standard work
    "quality-engineer": 60000        // 1 min for QA checks
  }
}
```

### Per-Skill Timeouts

Override timeout for specific skills:

```jsonc
// ~/.claude/config/claude.jsonc
{
  "skill_timeouts": {
    "orchestrator/task-routing": 15000,     // 15s
    "consistency-checker": 30000,           // 30s
    "code-review": 120000                   // 2 min (complex analysis)
  }
}
```

## Testing Your Changes

### Syntax Validation

Verify JSONC configuration is valid:

```bash
python3 << 'EOF'
import json
import re
import os
import sys

config_file = os.path.expanduser("~/.claude/config/claude.jsonc")

try:
    with open(config_file) as f:
        content = f.read()
        # Remove comments for validation
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'/\*[\s\S]*?\*/', '', content)
        json.loads(content)
    print(f"✅ {config_file} is valid JSON")
except json.JSONDecodeError as e:
    print(f"❌ Error in {config_file}: {e}")
    sys.exit(1)
except FileNotFoundError:
    print(f"⚠️  {config_file} not found (using defaults)")
EOF
```

### Configuration Reload

After editing configuration, reload without restarting:

```bash
# Signal Claude Code to reload config
curl -X POST http://localhost:3000/api/config/reload

# Or restart manually
pkill claude-code
sleep 2
claude-code start
```

### Agent Loading Verification

Verify agents load correctly with your customizations:

```bash
# Start Claude Code with verbose logging
CLAUDE_DEBUG=1 claude-code start

# Check agent load logs
tail -f ~/.claude/sessions/{session-id}/logs/agent-load.log

# Expected output:
# [INFO] Loading agent: orchestrator from agents/orchestrator.md
# [INFO] Loading agent: engineer from agents/engineer.md
# ...
# [INFO] All 8 agents loaded successfully
```

### Test Model Assignment

Verify the correct model is assigned to each agent:

```bash
python3 << 'EOF'
import json
import os
import re

config_file = os.path.expanduser("~/.claude/config/claude.jsonc")

with open(config_file) as f:
    content = f.read()
    # Remove comments for validation
    content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
    config = json.loads(content)

print("Current model assignments:")
for role, spec in config.get("agents", {}).items():
    model = spec.get("model", "unspecified")
    print(f"  {role}: {model}")
EOF
```

### Integration Test

Create a simple task to verify the harness works:

```bash
# 1. Start Claude Code
claude-code start

# 2. Load your project
# (via UI: "Load project" → select ~/git/agentic-engineers)

# 3. Create a minimal DELEGATE
# In Claude Code, paste:
# ---
# handoff_type: DELEGATE
# task_id: test-harness-config
# agent: engineer
# scope: Test harness configuration by listing files in src/
# context:
#   - File: src/agents/
# plan:
#   1. List files in src/agents/ directory
# success_criteria:
#   - Output contains file listing
# ---

# 4. Verify HANDBACK is returned with correct structure
```

## Model Selection Flowchart

The Claude Code harness uses this decision tree to assign models:

```
Task received
  ↓
Is there a session override?
  ├─ YES → Use session_override
  │         ↓
  │         Done
  └─ NO ↓

Is there a project override?
  ├─ YES → Use project_override
  │         ↓
  │         Done
  └─ NO ↓

Is there a per-agent override?
  ├─ YES → Use agent_override
  │         ↓
  │         Done
  └─ NO ↓

Look up effort tier
  ├─ effort == "low" → Use haiku (or effort_tiers.low)
  ├─ effort == "medium" → Use sonnet (or effort_tiers.medium)
  └─ effort == "high" → Use opus (or effort_tiers.high)
  ↓
Is cost within budget?
  ├─ NO → Downgrade to cheaper model or block
  └─ YES → Proceed
  ↓
Assign model to task
  ↓
Done
```

## Precedence Order (Highest to Lowest)

When multiple configuration sources exist, they are applied in this order:

1. **Session Override** (`~/.claude/sessions/{session-id}/config.jsonc`)
2. **Project Override** (`./.claude/agents.jsonc` in project root)
3. **Per-Project Global** (`~/.claude/projects/{project-name}/agents.jsonc`)
4. **Global Config** (`~/.claude/config/claude.jsonc`)
5. **Default** (built-in framework defaults)

**Example:** If global config specifies `haiku` for engineers, but session config overrides it to `opus`, the session override wins.

## Common Extension Patterns

### Pattern 1: Upgrade Model for Critical Projects

```jsonc
// ~/.claude/projects/production/agents.jsonc
{
  "agents": {
    "engineer": {
      "model": "opus",              // Always use Opus for production
      "temperature": 0.3            // Conservative settings
    },
    "quality-engineer": {
      "model": "sonnet"             // Upgrade QE too
    }
  },
  "token_budget": {
    "session_limit": 2000000,       // Higher budget for prod
    "hard_stop": true               // Strict enforcement
  }
}
```

### Pattern 2: Cost-Optimized Development

```jsonc
// ~/.claude/projects/dev/agents.jsonc
{
  "effort_tiers": {
    "low": "haiku",                 // Very cost-sensitive
    "medium": "haiku",              // Prefer cheap models
    "high": "sonnet"                // Only escalate when necessary
  },
  "cost_budget": {
    "daily_limit_usd": 10.00,       // Strict daily limit
    "hard_stop": false              // Warn, don't block
  }
}
```

### Pattern 3: High-Complexity Research

```jsonc
// ~/.claude/projects/research/agents.jsonc
{
  "agents": {
    "principal-engineer": {
      "model": "opus",
      "temperature": 0.7,            // Higher creativity
      "max_tokens": 16000            // Allow long responses
    }
  },
  "timeouts": {
    "agent_response": 600000         // 10 min timeout for deep analysis
  },
  "token_budget": {
    "session_limit": 5000000         // High budget for exploration
  }
}
```

## Next Steps

- [Claude Code Harness Setup](./harness-setup/claude.md)
- [Troubleshooting Guide](../HARNESS-CLAUDE-TROUBLESHOOTING.md)
- [Harness Integration Reference](../src/harnesses/claude_code/INTEGRATION.md)
- [Complete Harness Comparison](./harness-setup/README.md)
