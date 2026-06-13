---
name: doc-quality-monitor
description: >
  Automated documentation-quality monitoring (MONITORING-001). Scans a markdown
  documentation tree for broken internal links, missing required sections,
  stale docs, placeholder/TODO leakage, and structural/readability issues.
  Produces a structured JSON + human-readable report with a configurable
  health-score gate.
license: Proprietary
compatibility: agentic-engineers framework v5.10+. Requires Python 3.8+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: monitoring
  role: security-engineer
  model: claude-haiku-4.5
  effort: medium
  thinking: false
  trigger: on-demand | scheduled | pre-merge
  tdd_phase: GREEN  # 37/37 tests passing
  dependencies: []
---

# doc-quality-monitor

## Overview

**doc-quality-monitor** continuously checks the health of repository
documentation. It is a zero-dependency (stdlib-only; optional PyYAML for YAML
config) scanner that walks a markdown tree and emits a structured report with a
single, configurable health score so it can be wired into CI as a quality gate.

**What it checks (per markdown document):**

| Check | Category | Default severity |
|-------|----------|------------------|
| Broken internal links (relative file links + `#anchor`/`?query` stripping) | `BROKEN_LINK` | error |
| Missing required section headings (configurable, case-insensitive) | `MISSING_SECTION` | warning |
| Staleness — `mtime` older than `staleness_days` (default 30) | `STALE_DOC` | info |
| Placeholder / leakage markers (TODO, FIXME, TBD, XXX, WIP, lorem ipsum, …) | `PLACEHOLDER` | warning |
| Structure / readability — missing H1 title, below `min_word_count` | `STRUCTURE` | warning / info |
| Phantom references — references to removed classes/paths (AutomationController, etc.) | `PHANTOM_REFERENCE` | warning |
| Stale docstrings — SKILL.md YAML headers with version drift | `STALE_DOCSTRING` | warning |

External links (`http://`, `https://`, `mailto:`, `tel:`, protocol-relative)
are intentionally **not** fetched — the monitor is fully offline and
deterministic. Markdown image embeds (`![alt](src)`) are excluded from the
broken-link check.

**Why it matters:**

- **Drift detection** — surfaces broken cross-references before they reach users.
- **Freshness** — flags docs that have not been touched within a window.
- **No leakage** — catches `TODO`/placeholder text shipped into published docs.
- **CI gate** — exit code is non-zero when `health_score < fail_under`.

## Layout

```
src/skills/doc-quality-monitor/
├── SKILL.md
├── __init__.py
├── scripts/
│   ├── __init__.py
│   └── doc_quality_monitor.py     # MonitorConfig, Issue, DocQualityReport, DocQualityMonitor, CLI
└── tests/
    └── __init__.py
tests/test_doc_quality_monitor.py  # canonical suite (pytest testpaths=tests)
```

## Usage (CLI)

```bash
python src/skills/doc-quality-monitor/scripts/doc_quality_monitor.py \
    --root docs \
    --required-section Overview \
    --staleness-days 30 \
    --fail-under 90 \
    --report-json doc-quality.json \
    --report-md doc-quality.md
```

Flags:

| Flag | Description |
|------|-------------|
| `--root` | Directory to scan (default `docs`) |
| `--config` | JSON/YAML config file (see `MonitorConfig` fields) |
| `--required-section` | Repeatable required heading name |
| `--staleness-days` | Override staleness threshold |
| `--fail-under` | Minimum health score to exit 0 (default 90) |
| `--report-json` / `--report-md` | Write machine- / human-readable reports |
| `--quiet` | Suppress stdout summary |

Exit codes: `0` pass · `1` health below threshold · `2` root path missing.

## Usage (library)

```python
from pathlib import Path
import importlib

m = importlib.import_module(
    "src.skills.doc-quality-monitor.scripts.doc_quality_monitor"
)

cfg = m.MonitorConfig(required_sections=["Overview"], staleness_days=14)
report = m.DocQualityMonitor(root=Path("docs"), config=cfg).run()

print(report.health_score, report.passed, report.by_category)
report.write(json_path=Path("out/doc-quality.json"),
             text_path=Path("out/doc-quality.md"))
```

## Configuration (`MonitorConfig`)

| Field | Default | Meaning |
|-------|---------|---------|
| `staleness_days` | `30` | Age (days) before a doc is flagged stale |
| `required_sections` | `[]` | Heading names every doc must contain |
| `placeholder_patterns` | TODO/FIXME/TBD/XXX/WIP/lorem ipsum/… | Regexes treated as leakage |
| `min_word_count` | `20` | Below this, a doc is flagged short |
| `check_*` | `True` | Toggle each check independently |
| `exclude_globs` | `[]` | Globs (relative to root) to skip |
| `extensions` | `[".md", ".markdown"]` | Files discovered |
| `fail_under` | `90.0` | Health-score gate |

Health score = `100 − Σ penalties`, where penalties are 5 (error), 2 (warning),
0.5 (info) per finding, floored at 0.

## Testing

```bash
python -m pytest tests/test_doc_quality_monitor.py -q
# 37 passed
```

## Safety / isolation notes

- Writes **only** to caller-supplied report paths; never to `~/.agentic-engineers`
  or any global location.
- Pure, side-effect-free analysis over file contents; no network access.
