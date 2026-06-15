# -*- coding: utf-8 -*-
"""
init_todo.py — Phase 7: TODO.md initialization for repo-init skill.

Generates a bootstrapped TODO.md from the analysis result with:
- Fixed priority items (INIT-001, INIT-002)
- Conditional items based on analysis findings
- Standard backlog items (INIT-003 through INIT-005)
- Future items (INIT-F01, INIT-F02)

Author: Senior Engineer
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import List

_SKILL_ROOT = Path(__file__).parent.parent
_TODO_TEMPLATE = _SKILL_ROOT / "assets" / "todo-template.md"


def init_todo(cfg, analysis, dry_run: bool = False) -> List[Path]:
    """
    Phase 7: Write or skip TODO.md.

    Returns:
        List of Paths created (empty if dry_run or already exists).
    """
    todo_path = cfg.repo_root / "TODO.md"

    if todo_path.exists() and not cfg.force_reinit:
        return []

    content = _build_todo(cfg, analysis)

    if dry_run:
        return []

    todo_path.write_text(content, encoding="utf-8")
    return [todo_path]


def _build_todo(cfg, analysis) -> str:
    """Render TODO.md content from template + conditional items."""
    today = datetime.date.today().isoformat()
    template = _TODO_TEMPLATE.read_text(encoding="utf-8")

    priority_items = _build_priority_conditionals(analysis, today)
    standard_items = _build_standard_conditionals(analysis, today)
    future_items = _build_future_conditionals(analysis, today)

    return (
        template
        .replace("{project_name}", cfg.project_name)
        .replace("{date}", today)
        .replace("{framework_version}", cfg.framework_version)
        .replace("{priority_conditional_items}", priority_items)
        .replace("{standard_conditional_items}", standard_items)
        .replace("{future_conditional_items}", future_items)
    )


def _build_priority_conditionals(analysis, today: str) -> str:
    items: list[str] = []

    if not analysis.has_readme:
        items.append(
            f"- [ ] **INIT-R01:** Review and extend generated README.md\n"
            f"  - No README.md was detected; a stub was generated\n"
            f"  - Owner: Engineer\n"
            f"  - Added: {today}"
        )

    if analysis.total_files >= 1000:
        items.append(
            f"- [ ] **INIT-L01:** Run architecture audit before agent delegation\n"
            f"  - Large codebase detected ({analysis.total_files} files)\n"
            f"  - Understand structure before queuing implementation work\n"
            f"  - Owner: Principal Engineer\n"
            f"  - Added: {today}"
        )

    return "\n\n".join(items)


def _build_standard_conditionals(analysis, today: str) -> str:
    items: list[str] = []

    if analysis.test_framework == "unknown":
        fw = _suggest_test_framework(analysis.primary_language)
        items.append(
            f"- [ ] **INIT-T01:** Create test suite foundation\n"
            f"  - No test framework detected; add {fw}\n"
            f"  - Owner: Engineer\n"
            f"  - Added: {today}"
        )

    if analysis.ci_provider == "none":
        items.append(
            f"- [ ] **INIT-C01:** Add CI/CD workflow\n"
            f"  - No CI/CD detected; add GitHub Actions or equivalent\n"
            f"  - Reference: `docs/ONBOARDING.md#cicd`\n"
            f"  - Owner: Engineer\n"
            f"  - Added: {today}"
        )

    if analysis.is_monorepo:
        items.append(
            f"- [ ] **INIT-M01:** Configure per-package agent scoping\n"
            f"  - Monorepo structure detected\n"
            f"  - Configure agents per package/service boundary\n"
            f"  - Owner: Senior Engineer\n"
            f"  - Added: {today}"
        )

    if analysis.contributor_count > 5:
        items.append(
            f"- [ ] **INIT-X01:** Share ONBOARDING.md with team\n"
            f"  - {analysis.contributor_count} contributors detected\n"
            f"  - Distribute `docs/ONBOARDING.md` to team\n"
            f"  - Owner: Lead Engineer\n"
            f"  - Added: {today}"
        )

    return "\n\n".join(items)


def _build_future_conditionals(analysis, today: str) -> str:
    items: list[str] = []

    if analysis.is_monorepo:
        items.append(
            f"- [ ] **INIT-F03:** Evaluate per-package TODO.md files\n"
            f"  - Monorepo repos may benefit from package-level task tracking\n"
            f"  - Added: {today}"
        )

    return "\n\n".join(items)


def _suggest_test_framework(language: str) -> str:
    mapping = {
        "python": "pytest",
        "typescript": "jest or vitest",
        "javascript": "jest",
        "go": "go test (built-in)",
        "rust": "cargo test (built-in)",
        "java": "JUnit 5",
        "kotlin": "JUnit 5 or Kotest",
        "ruby": "RSpec",
        "csharp": "xUnit or NUnit",
    }
    return mapping.get(language, "an appropriate test framework")
