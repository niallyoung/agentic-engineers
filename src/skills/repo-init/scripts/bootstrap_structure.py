# -*- coding: utf-8 -*-
"""
bootstrap_structure.py — Phase 3: Directory structure creation for repo-init.

Creates the agentic-engineers directory layout in the target repository:
  agents/, skills/, tests/, docs/, ~/.agentic-engineers/

All writes are idempotent (skip if already exists unless force_reinit=True).

Author: Senior Engineer
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import List, Tuple


def bootstrap_structure(cfg, analysis, dry_run: bool = False) -> List[Path]:
    """
    Phase 3: Create agentic-engineers directory layout.

    Args:
        cfg: RepoInitConfig
        analysis: AnalysisResult from Phase 1
        dry_run: If True, plan but don't write.

    Returns:
        List of Paths created.
    """
    created: List[Path] = []
    today = datetime.date.today().isoformat()

    dirs_to_create = [
        cfg.repo_root / ".agentic-engineers",
        cfg.repo_root / "agents",
        cfg.repo_root / "skills",
        cfg.repo_root / "tests",
        cfg.repo_root / "docs",
        cfg.repo_root / "artifacts" / "queue" / "incoming",
        cfg.repo_root / "artifacts" / "queue" / "done",
        cfg.repo_root / "artifacts" / "queue" / "failed",
    ]

    for d in dirs_to_create:
        if not d.exists() and not dry_run:
            d.mkdir(parents=True, exist_ok=True)

    # ── agents/README.md ──────────────────────────────────────────────────────
    agents_readme = cfg.repo_root / "agents" / "README.md"
    if not agents_readme.exists() and not dry_run:
        agents_readme.write_text(
            _agents_readme_content(cfg, analysis), encoding="utf-8"
        )
        created.append(agents_readme)

    # ── skills/README.md ──────────────────────────────────────────────────────
    skills_readme = cfg.repo_root / "skills" / "README.md"
    if not skills_readme.exists() and not dry_run:
        skills_readme.write_text(
            _skills_readme_content(cfg), encoding="utf-8"
        )
        created.append(skills_readme)

    # ── tests/README.md ───────────────────────────────────────────────────────
    tests_readme = cfg.repo_root / "tests" / "README.md"
    if not tests_readme.exists() and not dry_run:
        tests_readme.write_text(
            _tests_readme_content(cfg, analysis), encoding="utf-8"
        )
        created.append(tests_readme)

    # ── tests/conftest.py ────────────────────────────────────────────────────
    conftest = cfg.repo_root / "tests" / "conftest.py"
    if not conftest.exists() and not dry_run:
        conftest.write_text(
            _conftest_content(cfg), encoding="utf-8"
        )
        created.append(conftest)

    # ── tests/test_framework_init.py ─────────────────────────────────────────
    smoke_test = cfg.repo_root / "tests" / "test_framework_init.py"
    if not smoke_test.exists() and not dry_run:
        smoke_test.write_text(
            _smoke_test_content(cfg), encoding="utf-8"
        )
        created.append(smoke_test)

    # ── docs/index.md ─────────────────────────────────────────────────────────
    docs_index = cfg.repo_root / "docs" / "index.md"
    if not docs_index.exists() and not dry_run:
        docs_index.write_text(
            _docs_index_content(cfg), encoding="utf-8"
        )
        created.append(docs_index)

    # ── ~/.agentic-engineers/.gitkeep ──────────────────────────────────────────────
    for subdir in ("incoming", "done", "failed"):
        gitkeep = cfg.repo_root / ".agentic-engineers" / subdir / ".gitkeep"
        if not gitkeep.exists() and not dry_run:
            gitkeep.write_text("")
            created.append(gitkeep)

    return created


# ── Template content generators ───────────────────────────────────────────────

def _agents_readme_content(cfg, analysis) -> str:
    return f"""# Agents — {cfg.project_name}

**Framework Version:** {cfg.framework_version}  
**Generated:** {datetime.date.today().isoformat()} by repo-init v1.0

## Enabled Agents

| Role | Description |
|------|-------------|
| Engineer | Code implementation, bug fixes, routine tasks |
| Senior Engineer | Complex features, deep debugging, mentoring |
| Lead Engineer | Code review, standards enforcement |
| Quality Engineer | Testing, coverage, quality gates |
| Security Engineer | Security reviews, vulnerability analysis |
| Principal Engineer | Architecture decisions, org-wide standards |
| Orchestrator | Routes all tasks via delegation queue |

## Routing

See `docs/AGENTS.md` for the task-type → agent routing table and model assignments.

## Agent Definitions

Agent role definitions are in individual `.md` files in this directory.
These are copied from the agentic-engineers framework and can be customized.

## Usage

All work enters through the Orchestrator queue:
```yaml
DELEGATE:
  task: <describe the task>
  effort: low | medium | high
  model: <model-name>
  context: |
    <Additional context>
```
"""


def _skills_readme_content(cfg) -> str:
    return f"""# Skills — {cfg.project_name}

**Framework Version:** {cfg.framework_version}  
**Generated:** {datetime.date.today().isoformat()} by repo-init v1.0

## Available Skills

| Skill | Purpose |
|-------|---------|
| usage-tracking | Token usage monitoring and forecasting |

## Adding Skills

To add a new skill, use the `skill-creator` skill via delegation:

```yaml
DELEGATE:
  task: create-skill
  skill: skill-creator
  name: my-skill
  role: engineer
  description: What this skill does and when to use it.
```

## Skill Structure

Each skill follows this layout:
```
skills/<skill-name>/
├── SKILL.md          # Required: metadata + instructions
├── scripts/          # Optional: executable code
└── references/       # Optional: detailed docs
```
"""


def _tests_readme_content(cfg, analysis) -> str:
    framework = analysis.test_framework if analysis.test_framework != "unknown" else "pytest"
    return f"""# Tests — {cfg.project_name}

**Test Framework:** {framework}  
**Generated:** {datetime.date.today().isoformat()} by repo-init v1.0

## Test Naming Convention

All tests MUST follow: `test_<action>_<scenario>_<expected>`

```python
# ✅ Correct
def test_create_user_valid_returns_201():
def test_login_invalid_password_returns_401():

# ❌ Incorrect  
def test_user_creation():
def testLogin():
```

## Running Tests

```bash
# All tests
python3 -m pytest tests/ -v

# With coverage
python3 -m pytest tests/ --cov=. --cov-report=term-missing

# Smoke tests only (framework init)
python3 -m pytest tests/test_framework_init.py -v
```

## Coverage Requirement

Minimum {85}% coverage required before HANDBACK is accepted.

## TDD Workflow

1. **RED** — Write a failing test first (`test(wip):` commit)
2. **GREEN** — Write minimum code to pass
3. **REFACTOR** — Clean up, ensure all tests still pass
"""


def _conftest_content(cfg) -> str:
    return f'''# conftest.py — pytest configuration for {cfg.project_name}
# Generated by repo-init v1.0
import pytest
from pathlib import Path

# Repository root (parent of tests/)
REPO_ROOT = Path(__file__).parent.parent


@pytest.fixture
def repo_root():
    """Absolute path to repository root."""
    return REPO_ROOT


@pytest.fixture
def tmp_repo(tmp_path):
    """Temporary directory initialized as a git repo (for integration tests)."""
    import os
    import subprocess
    env = {{
        **os.environ,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@test.com",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@test.com",
    }}
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        env=env,
    )
    return tmp_path
'''


def _smoke_test_content(cfg) -> str:
    return f'''# test_framework_init.py — Smoke tests for agentic-engineers framework init
# Generated by repo-init v1.0
# Pattern: test_<action>_<scenario>_<expected>
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def test_directory_exists_agents_present():
    """agents/ directory should exist after framework init."""
    assert (REPO_ROOT / "agents").is_dir(), "agents/ directory missing"


def test_directory_exists_skills_present():
    """skills/ directory should exist after framework init."""
    assert (REPO_ROOT / "skills").is_dir(), "skills/ directory missing"


def test_directory_exists_docs_present():
    """docs/ directory should exist after framework init."""
    assert (REPO_ROOT / "docs").is_dir(), "docs/ directory missing"


def test_file_exists_spec_md_present():
    """docs/SPEC.md should exist after framework init."""
    assert (REPO_ROOT / "docs" / "SPEC.md").is_file(), "docs/SPEC.md missing"


def test_file_exists_agents_md_present():
    """docs/AGENTS.md should exist after framework init."""
    assert (REPO_ROOT / "docs" / "AGENTS.md").is_file(), "docs/AGENTS.md missing"


def test_file_exists_todo_md_present():
    """TODO.md should exist after framework init."""
    assert (REPO_ROOT / "TODO.md").is_file(), "TODO.md missing"


def test_file_exists_init_marker_present():
    """.agentic-engineers/INIT-COMPLETE.yaml should exist after successful init."""
    marker = REPO_ROOT / ".agentic-engineers" / "INIT-COMPLETE.yaml"
    assert marker.is_file(), ".agentic-engineers/INIT-COMPLETE.yaml missing"


def test_todo_md_contains_priority_section():
    """TODO.md must contain a Priority section."""
    content = (REPO_ROOT / "TODO.md").read_text()
    assert "🔴 Priority" in content or "Priority" in content, "TODO.md missing Priority section"


def test_todo_md_contains_standard_section():
    """TODO.md must contain a Standard section."""
    content = (REPO_ROOT / "TODO.md").read_text()
    assert "🟡 Standard" in content or "Standard" in content, "TODO.md missing Standard section"


def test_spec_md_contains_agent_team_section():
    """docs/SPEC.md must contain Agent Team section."""
    content = (REPO_ROOT / "docs" / "SPEC.md").read_text()
    assert "Agent Team" in content, "docs/SPEC.md missing Agent Team section"


def test_spec_md_contains_quality_gates_section():
    """docs/SPEC.md must contain Quality Gates section."""
    content = (REPO_ROOT / "docs" / "SPEC.md").read_text()
    assert "Quality Gates" in content or "quality" in content.lower(), \\
        "docs/SPEC.md missing Quality Gates section"


def test_gitignore_contains_framework_entries():
    """'.gitignore' should contain agentic-engineers entries."""
    gitignore = REPO_ROOT / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        has_entry = any(
            marker in content
            for marker in ("~/.agentic-engineers/", "agentic-engineers", ".agentic-engineers")
        )
        assert has_entry, ".gitignore missing agentic-engineers entries"
'''


def _docs_index_content(cfg) -> str:
    return f"""# Documentation — {cfg.project_name}

**Framework Version:** {cfg.framework_version}  
**Generated:** {datetime.date.today().isoformat()} by repo-init v1.0

---

## Getting Started

- [ONBOARDING.md](ONBOARDING.md) — New contributor guide
- [QUICK-START.md](QUICK-START.md) — 5-minute reference

## Framework Configuration

- [SPEC.md](SPEC.md) — Project specification (read-only; edit via spec-management skill)
- [AGENTS.md](AGENTS.md) — Agent team configuration and routing table

## Development

- See `../TODO.md` for current task queue
- See `../agents/` for agent role definitions
- See `../skills/` for available skills
- See `../tests/` for test suite
"""
