# Phase 3 Integration Guide — Copilot CLI Harness

**Task ID**: 2026-05-17-phase-d-integration-copilot-cli  
**Author**: Senior Engineer  
**Date**: 2026-05-17  
**Status**: Complete  
**Harness**: Copilot CLI (`renderer/scripts/render-copilot.sh` + `src/harnesses/copilot_cli/streaming.py`)

---

## Overview

The Copilot CLI harness renders agentic-engineers **skills** into `~/.copilot/skills/` for use with [GitHub Copilot CLI](https://githubnext.com/projects/copilot-cli). It renders skills only — agents are intentionally omitted because the Copilot CLI platform does not support custom agent registration.

The Copilot CLI harness is the **most feature-complete renderer** in the framework, with:
- Human-readable streaming progress (`--stream`)
- Structured JSON-lines streaming for CI/CD (`--stream=json`)
- Full `NO_COLOR` support
- Per-skill timing and byte-count reporting

---

## Installation

```bash
# Default install
bash renderer/scripts/render-copilot.sh /path/to/agentic-engineers ~/.copilot

# With human-readable streaming progress
bash renderer/scripts/render-copilot.sh /path/to/agentic-engineers ~/.copilot --stream

# With JSON-lines streaming (for CI/CD pipelines)
bash renderer/scripts/render-copilot.sh /path/to/agentic-engineers ~/.copilot --stream=json

# Check status
bash renderer/scripts/render-copilot.sh /path/to/agentic-engineers ~/.copilot --status

# Uninstall
bash renderer/scripts/render-copilot.sh /path/to/agentic-engineers ~/.copilot --uninstall
```

---

## Streaming Output

### Human-Readable Mode (`--stream`)

Provides real-time per-skill progress with ANSI colors (suppressed when `NO_COLOR` is set or stdout is not a TTY):

```
📦 Rendering skills → /home/user/.copilot/skills/...
  ✅ ab-testing                    (1s)
  ✅ agent-creator                 (0s)
  ✅ consistency-checker           (1s)
  ...
✅ Rendered 14 skill(s) to /home/user/.copilot/skills/ (8s, 57344KB)
```

### JSON-Lines Mode (`--stream=json`)

Delegates to `src/harnesses/copilot_cli/streaming.py` for structured output:

```json
{"type":"start","skill":"ab-testing","timestamp":"2026-05-17T10:00:00Z","data":{}}
{"type":"progress","skill":"ab-testing","timestamp":"2026-05-17T10:00:01Z","data":{"files_done":3}}
{"type":"complete","skill":"ab-testing","timestamp":"2026-05-17T10:00:01Z","data":{"duration_ms":1200,"bytes":4096}}
{"type":"summary","skill":null,"timestamp":"2026-05-17T10:00:08Z","data":{"count":14,"total_bytes":57344,"duration_ms":8200}}
```

Parse in CI/CD:
```bash
bash renderer/scripts/render-copilot.sh /path/to/repo ~/.copilot --stream=json | \
  python3 -c "
import sys, json
for line in sys.stdin:
    event = json.loads(line)
    if event['type'] == 'summary':
        print(f\"Installed {event['data']['count']} skills in {event['data']['duration_ms']}ms\")
"
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
```

### Budget Checking

```python
from src.orchestration.monitoring.budget_checker import BudgetChecker, BudgetStatus

checker = BudgetChecker(config_path="config/token_budget.yaml")
result = checker.check(stats)

if result.status == BudgetStatus.BLOCKED:
    print("Budget exhausted")
```

### CLI Formatting

```python
from src.orchestration.monitoring.cli_formatter import CLIFormatter

formatter = CLIFormatter()  # Respects NO_COLOR automatically
print(formatter.format_task_line(metrics, session_cost=0.12))
```

---

## Python Streaming Helper

`src/harnesses/copilot_cli/streaming.py` provides a standalone Python API for programmatic use:

```python
from src.harnesses.copilot_cli.streaming import StreamingRenderer

renderer = StreamingRenderer(
    src_dir="src/skills",
    dst_dir=str(Path.home() / ".copilot/skills"),
    marker=".agentic-engineer-managed"
)

for event in renderer.render_all():
    print(event.to_json(), flush=True)
    
    # Cancellation support
    if should_stop:
        renderer.cancel()
```

Event types: `start`, `progress`, `complete`, `skip`, `error`, `summary`

---

## NO_COLOR Support

The Copilot CLI harness fully respects the `NO_COLOR` environment variable:

```bash
# Disable colors
NO_COLOR=1 bash renderer/scripts/render-copilot.sh /path/to/repo ~/.copilot --stream

# Colors are also suppressed automatically when stdout is not a TTY
bash renderer/scripts/render-copilot.sh /path/to/repo ~/.copilot --stream | tee install.log
```

The Python streaming helper (`CLIFormatter`) also respects `NO_COLOR`:
```python
formatter = CLIFormatter()  # auto-detects NO_COLOR
formatter_no_color = CLIFormatter(no_color=True)  # explicit override
```

---

## Architecture Notes

The Copilot CLI harness renders **skills only** — this is intentional. The Copilot CLI platform does not support custom agent registration, so only skills (which extend Copilot's capabilities) are installed.

The streaming Python helper (`src/harnesses/copilot_cli/streaming.py`) is the reference impl for structured streaming output. It could be generalized to support other harnesses if needed, but the use case is currently narrow.

---

## Troubleshooting

### Skills not appearing in Copilot CLI

```bash
bash renderer/scripts/render-copilot.sh /path/to/repo ~/.copilot --status
```

### Streaming JSON parse errors

Ensure Python 3.7+ is available:
```bash
python3 --version
```

### rsync not found

The renderer requires `rsync`. Install with:
```bash
# macOS
brew install rsync

# Ubuntu/Debian
sudo apt-get install rsync
```

### Cancellation in Python helper

```python
import threading

renderer = StreamingRenderer(src_dir, dst_dir, marker)

# Cancel after 30 seconds
timer = threading.Timer(30.0, renderer.cancel)
timer.start()

for event in renderer.render_all():
    print(event.to_json())

timer.cancel()
```
