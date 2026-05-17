# Phase 3 Integration Guide — Claude Code Harness

**Task ID**: 2026-05-17-phase-d-integration-claude-code  
**Author**: Senior Engineer  
**Date**: 2026-05-17  
**Status**: Complete  
**Harness**: Claude Code (`renderer/scripts/render-claude.sh`)

---

## Overview

The Claude Code harness renders agentic-engineers configuration into `~/.claude/` for use with [Claude Code](https://claude.ai/code). It renders:

- **Skills** → `~/.claude/skills/<name>/` (SKILL.md + supporting files)
- **Agents** → `~/.claude/agents/<name>.md` (frontmatter transformed to Claude Code subagent shape)

The renderer is a bash script. Phase 3 monitoring features (token tracking, budget checking, CLI formatting) are available through the Python orchestration stack, which runs independently of the renderer.

---

## Installation

```bash
# Install (renders skills + agents + git hooks)
bash renderer/scripts/render-claude.sh /path/to/agentic-engineers ~/.claude

# Check status
bash renderer/scripts/render-claude.sh /path/to/agentic-engineers ~/.claude --status

# Uninstall
bash renderer/scripts/render-claude.sh /path/to/agentic-engineers ~/.claude --uninstall
```

---

## Phase 3 Monitoring Features

### Token Tracking

```python
from src.orchestration.monitoring.metrics import MetricsRegistry
from src.orchestration.monitoring.token_tracker import TokenTracker

registry = MetricsRegistry()
tracker = TokenTracker(registry)

tracker.record_task_tokens(
    task_id="task-123",
    agent="engineer",
    input_tokens=1000,
    output_tokens=500,
    cached_tokens=100,
    cost_usd=0.045
)

stats = tracker.get_stats()
print(f"Total cost: ${stats.total_cost_usd:.4f}")
print(f"Tokens by agent: {stats.agent_tokens}")
```

### Budget Checking

```python
from src.orchestration.monitoring.budget_checker import BudgetChecker, BudgetStatus

checker = BudgetChecker(config_path="config/token_budget.yaml")
result = checker.check(stats)

if result.status == BudgetStatus.BLOCKED:
    raise RuntimeError("Budget exhausted")
```

### CLI Formatting

```python
from src.orchestration.monitoring.cli_formatter import CLIFormatter

formatter = CLIFormatter()  # Respects NO_COLOR automatically
print(formatter.format_session_summary(stats, budget_usd=10.0))
```

To disable colors in Claude Code terminal: `NO_COLOR=1`

---

## Renderer Output Features (Phase D additions)

The renderer now supports:

- **ANSI-colored progress output**: Green ✅ for success, yellow ⚠️ for warnings
- **NO_COLOR support**: Set `NO_COLOR=1` to disable all ANSI codes  
- **Per-skill progress indicators**: Spinner during rsync, checkmark on completion
- **Total install timing**: Summary shows total elapsed time

```
📦 Rendering skills → /home/user/.claude/skills/...
  ✅ ab-testing (0s)
  ✅ agent-creator (0s)
  ✅ consistency-checker (0s)
  ...
📖 Parsing canonical agent definitions from docs/AGENTS.md...
📦 Rendering agents → /home/user/.claude/agents/...
  ✅ agent engineer
  ✅ agent orchestrator
  ...
✅ Rendered 14 skill(s), 8 agent(s) (2s total)
```

---

## Agent Frontmatter Transformation

The renderer transforms agentic-engineers agent frontmatter to Claude Code subagent shape:

**Source** (`src/agents/engineer-agent.md`):
```yaml
---
role: engineer
model: claude-haiku-4-5
effort: high
---
```

**Rendered** (`~/.claude/agents/engineer.md`):
```yaml
---
name: engineer
description: "Well-scoped task with pre-written plan; low-medium complexity coding/implementation"
model: haiku
---
```

Model mapping: `claude-haiku-*` → `haiku`, `claude-sonnet-*` → `sonnet`, `claude-opus-*` → `opus`

---

## Known Gaps vs. OpenCode Harness

| Feature | Claude Code | OpenCode | Notes |
|---------|-------------|----------|-------|
| ANSI colors | ✅ (Phase D) | ✅ | Added in Phase D |
| NO_COLOR support | ✅ (Phase D) | ✅ | Added in Phase D |
| Per-item timing | ✅ (Phase D) | ✅ | Added in Phase D |
| Streaming JSON output | ❌ | ❌ | Not needed for bash renderer |
| `opencode.jsonc` config | N/A | ✅ | Platform-specific |
| Full model IDs | ❌ (tier names only) | ✅ | Claude Code uses short names |

---

## Troubleshooting

### Agent not appearing in Claude Code

Check that the agent was rendered:
```bash
bash renderer/scripts/render-claude.sh /path/to/repo ~/.claude --status
```

If showing as "foreign", the file exists but wasn't created by this renderer. Move it aside:
```bash
mv ~/.claude/agents/engineer.md ~/.claude/agents/engineer.md.bak
bash renderer/scripts/render-claude.sh /path/to/repo ~/.claude
```

### YAML escaping issues in agent descriptions

The renderer uses `yaml_escape_inline` (from `lib.sh`) to safely escape description strings. If you see malformed YAML in rendered agents, check `lib.sh`:

```bash
source renderer/scripts/lib.sh
yaml_escape_inline "test string with 'quotes' and \"double quotes\""
```

### docs/AGENTS.md not found

The renderer requires `docs/AGENTS.md` to look up canonical agent metadata. Ensure you're passing the correct `REPO_ROOT`:

```bash
bash renderer/scripts/render-claude.sh $(pwd) ~/.claude
```
