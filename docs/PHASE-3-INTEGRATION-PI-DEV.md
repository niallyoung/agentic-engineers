# Phase 3 Integration Guide — π.dev Harness

**Task ID**: 2026-05-17-phase-d-integration-pi-dev  
**Author**: Senior Engineer  
**Date**: 2026-05-17  
**Status**: Complete  
**Harness**: π.dev (`renderer/scripts/render-pi-dev.py`)

---

## Overview

The π.dev harness renders agentic-engineers configuration into `~/.pi/agent/` for use with the [π.dev](https://pi.dev) AI assistant platform. It is a **renderer** — it installs static configuration files. The Phase 3 monitoring features (token tracking, budget checking, CLI formatting) are available through the Python orchestration stack, which runs independently of the renderer.

---

## Installation

```bash
# Default install (source: renderer/pi-dev-src/, dest: ~/.pi)
python3 renderer/scripts/render-pi-dev.py

# Explicit paths
python3 renderer/scripts/render-pi-dev.py --src renderer/pi-dev-src/ --dest ~/.pi

# Check status
python3 renderer/scripts/render-pi-dev.py --status

# Uninstall
python3 renderer/scripts/render-pi-dev.py --uninstall
```

---

## Phase 3 Monitoring Features

### Token Tracking

Token tracking is available via `src/orchestration/monitoring/token_tracker.py`. When running the orchestrator within the π.dev context:

```python
from src.orchestration.monitoring.metrics import MetricsRegistry
from src.orchestration.monitoring.token_tracker import TokenTracker

registry = MetricsRegistry()
tracker = TokenTracker(registry)

# Record tokens after each agent invocation
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
```

### Budget Checking

Budget enforcement is available via `src/orchestration/monitoring/budget_checker.py`:

```python
from src.orchestration.monitoring.budget_checker import BudgetChecker, BudgetStatus

checker = BudgetChecker(config_path="config/token_budget.yaml")
result = checker.check(stats)

if result.status == BudgetStatus.BLOCKED:
    print("Budget exhausted — blocking new tasks")
elif result.status == BudgetStatus.WARNING:
    print(f"Warning: {result.pct_used:.1f}% of budget used")
```

### CLI Formatting

ANSI-colored output is available via `src/orchestration/monitoring/cli_formatter.py`:

```python
from src.orchestration.monitoring.cli_formatter import CLIFormatter

# Respects NO_COLOR environment variable automatically
formatter = CLIFormatter()
print(formatter.format_task_line(metrics, session_cost=0.12))
print(formatter.format_session_summary(stats, budget_usd=10.0))
```

To disable colors: `NO_COLOR=1 python3 your_script.py`

---

## Renderer Output Features (Phase D additions)

The renderer now supports:

- **ANSI-colored progress output**: Green ✅ for success, yellow ⚠️ for warnings, red ❌ for errors
- **NO_COLOR support**: Set `NO_COLOR=1` to disable all ANSI codes
- **Per-file timing**: Each rendered file shows elapsed time in dim text
- **Total install timing**: Summary shows total elapsed time

```
π.dev Harness Renderer (agentic-engineers)
======================================================================

Source: /path/to/renderer/pi-dev-src
Destination: /home/user/.pi/agent

  ✅ SYSTEM.md (0.01s)
  ✅ AGENTS.md (0.01s)
  ✅ settings.json (0.00s)
  ✅ pi.yml (0.00s)
  ✅ SUB_AGENT_SETUP.md (0.01s)

✅ 5 files rendered, 0 errors, hooks: ✅ (0.1s total)
```

---

## Troubleshooting

### PyYAML not installed

```
⚠️  PyYAML not available — pi.yml validation skipped
```

Install with: `pip install pyyaml`

### Source directory not found

```
❌ Source directory not found: /path/to/renderer/pi-dev-src
```

Ensure you're running from the repo root or use `--src` to specify the path.

### Argument parsing deprecation warning

Single positional argument is no longer supported (removed heuristic). Use explicit flags:

```bash
# Old (deprecated, now errors)
python3 render-pi-dev.py ~/.pi

# New (correct)
python3 render-pi-dev.py --dest ~/.pi
```

---

## Files Managed

| File | Destination | Purpose |
|------|-------------|---------|
| `SYSTEM.md` | `~/.pi/agent/SYSTEM.md` | Complete system prompt |
| `AGENTS.md` | `~/.pi/agent/AGENTS.md` | Global agent context |
| `settings.json` | `~/.pi/agent/settings.json` | Model and UI settings |
| `pi.yml` | `~/.pi/agent/pi.yml` | Sub-agent orchestration config |
| `SUB_AGENT_SETUP.md` | `~/.pi/agent/SUB_AGENT_SETUP.md` | User documentation |

---

## Architecture Notes

The π.dev harness is a **static file renderer** — it does not execute Python monitoring code. All Phase 3 monitoring features (token tracking, budget checking, CLI formatting) are available by importing from `src/orchestration/monitoring/` in your own scripts or by running the orchestrator directly.

The renderer itself is intentionally minimal: it copies files, validates YAML/JSON, and installs git hooks. This keeps the renderer fast, dependency-light, and easy to audit.
