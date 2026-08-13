#!/usr/bin/env python3
"""agents_table.py — canonical Python parser for src/AGENTS.md's Agent Roster table.

This is the single Python-side source of truth for parsing the

    | Role | Model | Effort | Multi-Model? | Use When |

table in src/AGENTS.md. It is the Python twin of parse_agents_md() in
renderer/lib/render-lib.sh (the canonical bash-side parser, used by
render-claude.sh, .githooks/pre-commit's frontmatter-drift check, and
lookup_agent_metadata()). The two implementations are pinned together by
tests/test_agents_table_parity.py, which runs both over the live
src/AGENTS.md and asserts identical (role, model, effort, description)
tuples — if you change one parser's semantics, change the other and rerun
that test.

Table-format contract (must hold for both parsers to agree):
  - Data rows look like:
      "| **Role Name** | model-id | effort | Multi-Model col | Use When text |"
    The bold "**Role Name**" cell is what identifies a data row — header and
    separator rows (`| Role | Model | ... |`, `|---|---|...`) are skipped
    because they don't start with "| **".
  - At least 5 pipe-delimited fields are required after stripping exactly one
    leading "| " and one trailing " |": Role, Model, Effort, Multi-Model?,
    Use When.
  - The Multi-Model? column may contain a literal escaped pipe (\\|) to
    separate a default/fallback pair, e.g.
    "opus-5 (default) \\| 4.8 (fallback)". That escaped pipe must NOT be
    treated as a column separator: it is protected with a placeholder before
    splitting and restored afterwards, exactly like render-lib.sh's
    __ESCAPED_PIPE__ trick. (A prior generation of the OpenCode and Codex
    renderers each hand-rolled their own split without this protection, which
    silently shifted the Principal/Security Engineer rows' description field
    to a fragment of the Multi-Model column — fixed by routing both through
    this shared parser.)
  - The returned "role" is derived from the Role cell: strip the ** bold
    markers, lowercase, replace spaces with hyphens (e.g. "Senior Engineer"
    -> "senior-engineer").
  - A row is only emitted if role, model, effort, and description are all
    non-empty after trimming.

Usage:
    from agents_table import parse_agents_table
    rows = parse_agents_table(Path("src/AGENTS.md"))
    # -> [{"role": "orchestrator", "model": "claude-sonnet-5", "effort": "low",
    #      "description": "All entry points; ..."}, ...]
"""
from __future__ import annotations

import re
from pathlib import Path

_ESCAPED_PIPE_PLACEHOLDER = "__ESCAPED_PIPE__"

# Mirrors awk's /^\| \*\*[A-Za-z]/ — a data row starts with "| **" followed by
# a letter. Header ("| Role | ...") and separator ("|---|---|...") rows don't
# match and are skipped.
_ROW_RE = re.compile(r"^\| \*\*[A-Za-z]")


def parse_agents_table(agents_md: Path) -> list[dict[str, str]]:
    """Parse the canonical Agent Roster table from src/AGENTS.md.

    Returns a list of {"role": kebab-case, "model": str, "effort": str,
    "description": str} dicts, one per data row, in table order. Returns an
    empty list if the file does not exist. See the module docstring for the
    table-format contract this depends on.
    """
    agents_md = Path(agents_md)
    if not agents_md.is_file():
        return []

    rows: list[dict[str, str]] = []
    for line in agents_md.read_text(encoding="utf-8").splitlines():
        if not _ROW_RE.match(line):
            continue

        # Strip exactly one leading "| " and one trailing " |" (mirrors the
        # awk gsub(/^\| /, "") / gsub(/ \|$/, "") pair).
        body = re.sub(r"^\| ", "", line)
        body = re.sub(r" \|$", "", body)

        # Protect escaped pipes (e.g. in the Multi-Model? column) from being
        # mistaken for column separators.
        body = body.replace("\\|", _ESCAPED_PIPE_PLACEHOLDER)

        fields = body.split("|")
        if len(fields) < 5:
            continue
        fields = [f.strip().replace(_ESCAPED_PIPE_PLACEHOLDER, "|") for f in fields]

        role_raw, model, effort, description = fields[0], fields[1], fields[2], fields[4]
        role = re.sub(r"\*\*", "", role_raw).strip()
        role_kebab = role.lower().replace(" ", "-")

        if role_kebab and model and effort and description:
            rows.append(
                {
                    "role": role_kebab,
                    "model": model,
                    "effort": effort,
                    "description": description,
                }
            )

    return rows
