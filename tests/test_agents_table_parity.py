"""Parity test between the bash and Python canonical Agent Roster table parsers.

There are exactly two independent implementations of "parse the | Role | Model
| Effort | Multi-Model? | Use When | table in src/AGENTS.md" left in this
repo after the multi-parser consolidation:

  - bash:   parse_agents_md() in renderer/lib/render-lib.sh
            (consumed by render-claude.sh, render-opencode.sh's
            docs_lookup_role(), and .githooks/pre-commit's frontmatter-drift
            check via lookup_agent_metadata())
  - python: parse_agents_table() in renderer/lib/agents_table.py
            (consumed by render-codex.py)

Both must agree on every (role, model, effort, description) tuple they parse
out of the live src/AGENTS.md. This test pins them together: if either
implementation's parsing semantics drift from the other, this fails.

Before consolidation, render-opencode.sh and render-codex.py each had their
own hand-rolled awk/regex parser that did not protect the Multi-Model?
column's escaped pipe (e.g. "opus-5 (default) \\| 4.8 (fallback)") from being
treated as a column separator, which silently corrupted the Principal
Engineer and Security Engineer rows' description field. This test's fixture
data intentionally exercises that escaped-pipe case so a regression of either
parser's escaping would be caught here rather than only showing up as a
rendered-output diff.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_MD = REPO_ROOT / "src" / "AGENTS.md"
RENDER_LIB = REPO_ROOT / "renderer" / "lib" / "render-lib.sh"
LIB_DIR = REPO_ROOT / "renderer" / "lib"

sys.path.insert(0, str(LIB_DIR))
from agents_table import parse_agents_table  # type: ignore  # noqa: E402


def _parse_via_bash(agents_md: Path) -> list[tuple[str, str, str, str]]:
    """Run the canonical bash parser and return its rows as tuples."""
    script = f'''
set -euo pipefail
source "{RENDER_LIB}"
parse_agents_md "{agents_md}"
'''
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"parse_agents_md failed: {result.stderr}"
    rows = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        role, model, effort, description = line.split("|", 3)
        rows.append((role, model, effort, description))
    return rows


def _parse_via_python(agents_md: Path) -> list[tuple[str, str, str, str]]:
    return [
        (row["role"], row["model"], row["effort"], row["description"])
        for row in parse_agents_table(agents_md)
    ]


def test_bash_and_python_parsers_agree_on_live_agents_md():
    bash_rows = _parse_via_bash(AGENTS_MD)
    python_rows = _parse_via_python(AGENTS_MD)

    assert bash_rows, "bash parser returned no rows — src/AGENTS.md roster table missing/malformed?"
    assert python_rows, "python parser returned no rows — src/AGENTS.md roster table missing/malformed?"
    assert bash_rows == python_rows, (
        "bash (render-lib.sh parse_agents_md) and python (agents_table.py "
        "parse_agents_table) disagree on src/AGENTS.md — they must stay pinned "
        f"together.\nbash:   {bash_rows}\npython: {python_rows}"
    )


def test_expected_roles_present_with_correct_role_model_effort_tuples():
    """Sanity-anchor on the known roster so a parser that silently drops or
    corrupts a row (not just diverges from its sibling) is also caught."""
    python_rows = {row[0]: row for row in _parse_via_python(AGENTS_MD)}

    expected = {
        "orchestrator": ("claude-sonnet-5", "low"),
        "engineer": ("claude-haiku-4.5", "high"),
        "quality-engineer": ("claude-sonnet-5", "medium"),
        "senior-engineer": ("claude-sonnet-5", "high"),
        "lead-engineer": ("claude-sonnet-5", "max"),
        "principal-engineer": ("claude-opus-5", "high"),
        "security-engineer": ("claude-fable-5", "max"),
        "model-engineer": ("claude-sonnet-5", "high"),
    }

    assert set(python_rows) == set(expected), (
        f"roster mismatch: got {sorted(python_rows)}, expected {sorted(expected)}"
    )
    for role, (model, effort) in expected.items():
        _, got_model, got_effort, description = python_rows[role]
        assert got_model == model, f"{role}: model {got_model!r} != {model!r}"
        assert got_effort == effort, f"{role}: effort {got_effort!r} != {effort!r}"
        assert description, f"{role}: description must be non-empty"


def test_escaped_pipe_in_multi_model_column_does_not_corrupt_description():
    """Regression guard for the specific bug fixed by consolidating onto the
    canonical parsers: Principal/Security Engineer rows carry an escaped pipe
    (\\|) inside the Multi-Model? column separating a default/fallback pair.
    A parser that splits on every literal '|' without protecting the escaped
    one shifts the description field to a fragment of that column instead."""
    python_rows = {row["role"]: row for row in parse_agents_table(AGENTS_MD)}

    principal_desc = python_rows["principal-engineer"]["description"]
    security_desc = python_rows["security-engineer"]["description"]

    assert "fallback" not in principal_desc, (
        f"principal-engineer description leaked Multi-Model column text: {principal_desc!r}"
    )
    assert "fallback" not in security_desc, (
        f"security-engineer description leaked Multi-Model column text: {security_desc!r}"
    )
    assert principal_desc.startswith("Cross-service architecture")
    assert security_desc.startswith("Security analysis")
