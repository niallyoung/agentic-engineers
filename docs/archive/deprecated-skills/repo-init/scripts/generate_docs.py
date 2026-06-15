# -*- coding: utf-8 -*-
"""
generate_docs.py — Phase 8: Documentation generation for repo-init.

Generates:
- docs/ONBOARDING.md  — New contributor guide
- docs/QUICK-START.md — 5-minute reference
- docs/AGENTS.md      — Repo-specific agent configuration

Author: Senior Engineer
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import List

_SKILL_ROOT = Path(__file__).parent.parent
_AGENTS_MD_TEMPLATE = _SKILL_ROOT / "assets" / "agents-md-template.md"


def generate_docs(cfg, analysis, dry_run: bool = False) -> List[Path]:
    """
    Phase 8: Write ONBOARDING.md, QUICK-START.md, AGENTS.md.

    Returns:
        List of Paths created.
    """
    created: List[Path] = []
    docs_dir = cfg.repo_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.date.today().isoformat()

    files = {
        docs_dir / "ONBOARDING.md": _onboarding_content(cfg, analysis, today),
        docs_dir / "QUICK-START.md": _quick_start_content(cfg, today),
        docs_dir / "AGENTS.md": _agents_md_content(cfg, today),
    }

    for path, content in files.items():
        if not path.exists() and not dry_run:
            path.write_text(content, encoding="utf-8")
            created.append(path)

    return created


def _onboarding_content(cfg, analysis, today: str) -> str:
    return f"""# Onboarding — {cfg.project_name}

**Framework Version:** {cfg.framework_version}  
**Generated:** {today} by repo-init v1.0

---

## Welcome

This repository uses the **agentic-engineers** framework for AI-assisted development.
All work flows through specialized AI agents via a delegation queue.

---

## Prerequisites

Before you begin, ensure you have:

1. **Python 3.8+** — `python3 --version`
2. **git** — `git --version`
3. **Model harness configured** — See §3 below
4. Access to the repository

---

## Model Harness Setup

This repo is configured for: **{cfg.model_harness}**

{'### Claude (Anthropic)' if cfg.model_harness == 'claude' else '### GPT-5 (OpenAI)' if cfg.model_harness == 'gpt5' else '### Local Models'}

{'Set `ANTHROPIC_API_KEY` in your shell environment.' if cfg.model_harness == 'claude' else 'Set `OPENAI_API_KEY` in your shell environment.' if cfg.model_harness == 'gpt5' else 'Start Ollama: `ollama serve` or LM Studio.'}

Validate your setup:
```bash
make validate-compat
```

---

## Your First Task

All tasks enter through the Orchestrator queue as DELEGATE blocks.

### Example: Submit a Bug Fix

```yaml
DELEGATE:
  task: Fix null pointer in user login
  effort: low
  model: claude-haiku-4.5
  context: |
    The login endpoint at /api/auth/login throws a null pointer
    when username is empty. Fix and add a test.
  acceptance_criteria:
    - Login endpoint handles empty username gracefully
    - Returns 400 with clear error message
    - Test added: test_login_empty_username_returns_400
```

The Orchestrator routes this to an Engineer, who returns a HANDBACK.

---

## Agent Team

| Role | When to Use |
|------|-------------|
| Engineer | Bug fixes, routine implementation |
| Senior Engineer | Complex features, debugging |
| Lead Engineer | Code review, standards |
| Quality Engineer | Testing, coverage |
| Security Engineer | Security reviews |
| Principal Engineer | Architecture decisions |

See `docs/AGENTS.md` for full routing table and model assignments.

---

## DELEGATE/HANDBACK Protocol

### DELEGATE Block

```yaml
DELEGATE:
  task: <description>
  effort: low | medium | high
  model: <model-name>
  priority: priority | standard | future
  context: |
    <Additional context>
  acceptance_criteria:
    - Criterion 1
    - Criterion 2
```

### HANDBACK Block

```yaml
HANDBACK:
  status: SUCCESS | FAILED | PARTIAL
  agent: <role>
  summary: |
    <What was done>
  deliverables:
    - path/to/file.py
  tests_passed: true
  coverage: 87
  warnings: []
  next_steps: []
```

---

## Quality Gates

All work must pass before HANDBACK is accepted:

| Gate | Requirement |
|------|-------------|
| Test coverage | ≥ {85 if cfg.model_harness != 'local' else 70}% |
| HANDBACK format | Required |
| Spec compliance | {'Required' if cfg.model_harness != 'local' else 'Recommended'} |
| Zero lint errors | Required |

---

## TODO.md

`TODO.md` is the source of truth for all approved work items.

- 🔴 **Priority** — Blocking items; do first
- 🟡 **Standard** — Normal backlog
- 🔵 **Optional** — Nice-to-have
- 🔮 **Future** — Not yet scheduled

Do not add items to `TODO.md` manually unless you are Lead Engineer or above.
All new items come through the delegation queue.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `make validate-compat` fails | Check tool installation and API keys |
| HANDBACK rejected | Check test coverage and lint errors |
| Init marker missing | Re-run `repo-init` with `--force-reinit` |
| Agent not routing | Check `docs/AGENTS.md` routing table |

---

## Further Reading

- [QUICK-START.md](QUICK-START.md) — 5-minute reference
- [AGENTS.md](AGENTS.md) — Agent configuration
- [SPEC.md](SPEC.md) — Project specification
- [agentic-engineers framework](https://github.com/{your-org}/agentic-engineers)
"""


def _quick_start_content(cfg, today: str) -> str:
    return f"""# Quick Start — {cfg.project_name}

**Framework Version:** {cfg.framework_version}  
**Generated:** {today} by repo-init v1.0

---

## In 5 Minutes

```bash
# 1. Verify initialization
make init-check

# 2. Validate compatibility  
make validate-compat

# 3. Run smoke tests
make test

# 4. Review task queue
cat TODO.md
```

---

## DELEGATE Block Template

```yaml
DELEGATE:
  task: <task description — be specific>
  effort: low          # low | medium | high
  model: claude-haiku-4.5   # cheapest capable model
  context: |
    <What the agent needs to know>
    Include: current state, desired state, constraints.
  acceptance_criteria:
    - Specific measurable outcome 1
    - Specific measurable outcome 2
```

---

## TDD Workflow

**RED → GREEN → REFACTOR**

```bash
# RED: Write failing test first
# Commit: git commit -m "test(wip): Add RED-phase test for <feature>"

# GREEN: Write minimum code to pass
python3 -m pytest tests/test_my_feature.py -v

# REFACTOR: Clean up
python3 -m pytest tests/ -v --cov=. --cov-report=term-missing
```

**Test naming:** `test_<action>_<scenario>_<expected>`

```python
def test_create_user_valid_returns_201():
def test_login_invalid_password_returns_401():
def test_delete_nonexistent_user_returns_404():
```

---

## Queue Commands

```bash
# Check incoming queue
ls ~/.agentic-engineers/incoming/

# Check completed tasks
ls ~/.agentic-engineers/done/

# View a task
cat ~/.agentic-engineers/incoming/<task_id>.yaml
```

---

## Common DELEGATE Templates

### Bug Fix
```yaml
DELEGATE:
  task: Fix <bug description>
  effort: low
  model: claude-haiku-4.5
  context: |
    Bug: <what's broken>
    Location: <file/function>
    Expected: <correct behavior>
  acceptance_criteria:
    - Bug fixed
    - Test added: test_<what>_<scenario>_<expected>
```

### Feature
```yaml
DELEGATE:
  task: Implement <feature>
  effort: medium
  model: claude-haiku-4.5
  context: |
    Feature: <description>
    Inputs: <what goes in>
    Outputs: <what comes out>
    Constraints: <any limits>
  acceptance_criteria:
    - Feature works as described
    - Tests added with ≥85% coverage
    - HANDBACK includes working example
```

### Code Review
```yaml
DELEGATE:
  task: Review PR #<N>
  effort: medium
  model: claude-sonnet-4.6
  context: |
    PR: <URL or description>
    Focus areas: <security, performance, correctness>
  acceptance_criteria:
    - All issues documented with severity
    - Blocking issues clearly identified
    - Approval or rejection with justification
```

---

## Top 5 Mistakes

1. **Skipping the test** — Always write tests first (TDD RED)
2. **Effort too high** — Default to `low`; escalate only when needed
3. **Vague context** — Be specific: current state, desired state, constraints
4. **Missing acceptance criteria** — How will you know it worked?
5. **Editing SPEC.md directly** — Use `spec-management` skill instead
"""


def _agents_md_content(cfg, today: str) -> str:
    """Generate AGENTS.md from template with substitutions."""
    template = _AGENTS_MD_TEMPLATE.read_text(encoding="utf-8")

    # Model assignments by harness
    harness_models = {
        "claude": {
            "engineer_model": "claude-haiku-4.5",
            "senior_model": "claude-sonnet-4.6",
            "lead_model": "claude-sonnet-4.6",
            "principal_model": "claude-opus-4.8",
        },
        "gpt5": {
            "engineer_model": "gpt-4o-mini",
            "senior_model": "gpt-4o",
            "lead_model": "gpt-4o",
            "principal_model": "gpt-4",
        },
        "local": {
            "engineer_model": "ollama/llama3.2",
            "senior_model": "ollama/llama3.2",
            "lead_model": "ollama/llama3.2",
            "principal_model": "ollama/llama3.1:70b",
        },
        "copilot": {
            "engineer_model": "claude-haiku-4.5",
            "senior_model": "claude-sonnet-4.6",
            "lead_model": "claude-sonnet-4.6",
            "principal_model": "claude-opus-4.8",
        },
    }

    models = harness_models.get(cfg.model_harness, harness_models["claude"])

    return (
        template
        .replace("{project_name}", cfg.project_name)
        .replace("{framework_version}", cfg.framework_version)
        .replace("{date}", today)
        .replace("{model_harness}", cfg.model_harness)
        .replace("{engineer_model}", models["engineer_model"])
        .replace("{senior_model}", models["senior_model"])
        .replace("{lead_model}", models["lead_model"])
        .replace("{principal_model}", models["principal_model"])
    )
