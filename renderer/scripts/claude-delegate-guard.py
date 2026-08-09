#!/usr/bin/env python3
"""
claude-delegate-guard.py — PreToolUse hook for Claude Code.

Enforces the DELEGATE/HANDBACK protocol at the one place it was previously
unenforced: the moment a live Claude Code session spawns one of the
agentic-engineers framework specialist agents via the Agent/Task tool.

Root cause this closes: DELEGATE validation logic already exists in this
repo (src/skills/protocol-validator/scripts/protocol_validator.py and
src/orchestration/agents/delegate_validator.py), but both were written for
the *simulated* Python orchestration pipeline, not the live harness. When a
real Claude Code session uses the Agent tool to spawn e.g. "senior-engineer",
nothing on the Claude Code side ever calls either validator — a plain
English prompt sails straight through. This script is the missing
mechanical gate for that exact path.

Deliberately NOT a thin wrapper around the two existing validators:
  - protocol_validator.py additionally requires "skill" and "context" core
    fields and imports PyYAML. This hook only enforces the field subset the
    installing DELEGATE specified (handoff_type, agent, task_id, scope,
    plan, success_criteria) and avoids a hard PyYAML dependency, because it
    runs as a subprocess under whatever bare `python3` is first on PATH at
    hook-execution time — not necessarily the repo's own virtualenv.
  - delegate_validator.py's DelegateValidator uses underscored role names
    (`senior_engineer`) inherited from an earlier convention; the live
    harness (agent frontmatter, src/AGENTS.md, rendered ~/.claude/agents/)
    uses hyphenated names throughout. Reusing it as-is would silently
    mismatch every role name it checks.

Contract (Claude Code PreToolUse hooks):
  stdin:  JSON with at least {"tool_name": ..., "tool_input": {...}}
  stdout: JSON {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                "permissionDecision": "allow"|"deny",
                "permissionDecisionReason": "..."}}
          (omitted entirely == defer to normal permission handling, i.e.
          allow, for tool calls this hook has no opinion about)
  exit code: always 0 — the decision is communicated via stdout, not via
             process exit status, so a hook bug fails open instead of
             wedging every Agent-tool call in the session.
"""
import json
import re
import sys

# The 8 framework specialist roles this hook governs. Sourced from
# src/AGENTS.md "Valid agents" list / VALID_AGENTS in protocol_validator.py.
# Generic/utility agents (Explore, Plan, general-purpose, claude,
# statusline-setup, ...) are intentionally out of scope: they never accept:
# [DELEGATE] in their frontmatter and are not bound by the protocol.
FRAMEWORK_ROLES = {
    "orchestrator",
    "engineer",
    "senior-engineer",
    "lead-engineer",
    "principal-engineer",
    "security-engineer",
    "quality-engineer",
    "model-engineer",
}

# task_id: kebab-case, 3-50 chars — matches protocol_validator.py's TASK_ID_PATTERN.
TASK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$")

# A line that opens a new top-level (column-0) YAML mapping key, e.g.
# "handoff_type: DELEGATE" or "plan:". Used both to segment the DELEGATE
# block into fields and to locate where a DELEGATE block starts inside a
# prompt that has leading prose.
_TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")

CANONICAL_SCHEMA = """\
handoff_type: DELEGATE
agent: <hyphenated-role>        # must match the subagent_type being spawned
task_id: my-task-id             # kebab-case, 3-50 chars
scope: |
  What will be done and what is out of scope (>=15 words).
plan:
  - "Step 1: ..."
  - "Step 2: ..."
success_criteria:
  - "AC1: describe done"
"""


def _count_words(text):
    return len(text.split())


def _strip_inline_comment(value):
    """Strip a trailing ' # comment' from a scalar YAML value, then trim."""
    return value.split(" #", 1)[0].split("\t#", 1)[0].strip()


def parse_flat_fields(text):
    """Best-effort, dependency-free extraction of top-level YAML mapping
    fields from ``text``.

    This is not a general YAML parser. It only needs to recover the small,
    flat set of DELEGATE core fields (scalars and block scalars/lists as
    multi-line blobs) well enough to validate their presence and shape —
    exactly what this hook checks. Nested/complex YAML content inside a
    field's value is preserved verbatim as that field's raw text; deeper
    structure is never interpreted.

    Returns a dict of {key: raw_value_text}.
    """
    fields = {}
    current_key = None
    current_lines = []

    for line in text.splitlines():
        m = _TOP_KEY_RE.match(line)
        # Only treat this as a new top-level key if it starts at column 0
        # (no leading whitespace) — nested keys are part of the current
        # field's value, not a new field.
        if m is not None and line == line.lstrip() and not line.startswith("-"):
            if current_key is not None:
                fields[current_key] = "\n".join(current_lines).strip()
            current_key = m.group(1)
            current_lines = [m.group(2)] if m.group(2) else []
        elif current_key is not None:
            current_lines.append(line)

    if current_key is not None:
        fields[current_key] = "\n".join(current_lines).strip()

    return fields


def _candidate_blocks(prompt):
    """Yield candidate substrings of ``prompt`` that might contain a
    DELEGATE block, most-specific first.
    """
    # 1. Fenced code blocks that look like they carry a DELEGATE.
    for m in re.finditer(r"```(?:ya?ml)?\s*\n(.*?)```", prompt, re.DOTALL):
        block = m.group(1)
        if "handoff_type" in block or re.search(r"^\s*type\s*:\s*DELEGATE\b", block, re.MULTILINE):
            yield block

    # 2. The whole prompt verbatim — the common case, since DELEGATE blocks
    #    are typically passed as the entire Agent-tool prompt with no
    #    wrapping prose (see src/AGENTS.md "Handover Packet Protocol").
    yield prompt

    # 3. From the first plausible DELEGATE-block opening key onward, in case
    #    the prompt has leading prose before the block.
    for m in re.finditer(r"^(handoff_type|task_id|type)\s*:\s*\S", prompt, re.MULTILINE):
        yield prompt[m.start():]


def find_delegate(prompt):
    """Locate a DELEGATE block inside a free-form Agent-tool prompt string.

    Returns the parsed field dict, or None if no block carrying the
    ``handoff_type: DELEGATE`` (or deprecated ``type: DELEGATE``)
    discriminator could be found.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        return None

    for candidate in _candidate_blocks(prompt):
        fields = parse_flat_fields(candidate)
        discriminator = _strip_inline_comment(
            fields.get("handoff_type") or fields.get("type") or ""
        )
        if discriminator == "DELEGATE":
            return fields
    return None


def validate_delegate(fields, subagent_type):
    """Validate the DELEGATE core fields this hook enforces.

    Deliberately narrower than the full canonical protocol-validator:
    ``skill`` and ``context`` are treated as out of scope for this hook (see
    module docstring) — it only enforces the field subset named in the
    DELEGATE that commissioned this hook: handoff_type, agent, task_id,
    scope (>=15 words), plan, success_criteria.

    Returns a list of error strings (empty == valid).
    """
    errors = []

    task_id = _strip_inline_comment(fields.get("task_id", ""))
    if not task_id:
        errors.append("task_id: required, must be a non-empty string")
    elif not TASK_ID_PATTERN.match(task_id):
        errors.append("task_id: must be kebab-case, 3-50 chars (got %r)" % task_id)

    agent = _strip_inline_comment(fields.get("agent", ""))
    if not agent:
        errors.append("agent: required, must be a non-empty string")
    elif agent not in FRAMEWORK_ROLES:
        errors.append(
            "agent: invalid agent %r (must be one of %s)" % (agent, sorted(FRAMEWORK_ROLES))
        )
    elif agent != subagent_type:
        errors.append(
            "agent: DELEGATE targets %r but this Agent-tool call spawns "
            "subagent_type %r — mismatch" % (agent, subagent_type)
        )

    scope = fields.get("scope", "")
    if not scope.strip():
        errors.append("scope: required, must be a non-empty string")
    elif _count_words(scope) < 15:
        errors.append("scope: must be >=15 words (%d provided)" % _count_words(scope))

    plan = fields.get("plan", "")
    plan_items = re.findall(r"^\s*-\s+\S", plan, re.MULTILINE)
    if "plan" not in fields:
        errors.append("plan: required")
    elif len(plan_items) < 1:
        errors.append("plan: must be a non-empty list")

    sc = fields.get("success_criteria", "")
    sc_items = re.findall(r"^\s*-\s+\S", sc, re.MULTILINE)
    if "success_criteria" not in fields:
        errors.append("success_criteria: required")
    elif len(sc_items) < 1:
        errors.append("success_criteria: must be a non-empty list")

    return errors


def decide(payload):
    """Given the parsed PreToolUse hook payload, return (decision, reason)
    where decision is "allow" or "deny" and reason is a human-readable
    string (only meaningful when decision == "deny").
    """
    tool_name = payload.get("tool_name", "")
    if tool_name not in ("Task", "Agent"):
        return "allow", None

    tool_input = payload.get("tool_input") or {}
    subagent_type = tool_input.get("subagent_type", "")
    if subagent_type not in FRAMEWORK_ROLES:
        # Generic/utility agent (Explore, Plan, general-purpose, claude, ...)
        # — not bound by the DELEGATE/HANDBACK protocol.
        return "allow", None

    prompt = tool_input.get("prompt", "")
    fields = find_delegate(prompt)
    if fields is None:
        return "deny", (
            "BLOCKED: spawning framework specialist '%s' requires a canonical "
            "DELEGATE block (handoff_type: DELEGATE) in the prompt; none was "
            "found.\n\nCanonical schema — embed this in the prompt:\n%s\n"
            "See ~/.claude/AGENTS.md § DELEGATE/HANDBACK Protocol for full detail."
            % (subagent_type, CANONICAL_SCHEMA)
        )

    errors = validate_delegate(fields, subagent_type)
    if errors:
        error_list = "\n".join("  - %s" % e for e in errors)
        return "deny", (
            "BLOCKED: DELEGATE block for framework specialist '%s' is "
            "malformed:\n%s\n\nCanonical schema:\n%s"
            % (subagent_type, error_list, CANONICAL_SCHEMA)
        )

    return "allow", None


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, TypeError):
        # Can't parse our own input — fail open rather than break the
        # calling session over a hook bug.
        sys.exit(0)

    try:
        decision, reason = decide(payload)
    except Exception:
        # Any unexpected failure in the guard itself must never block a
        # legitimate tool call — fail open.
        sys.exit(0)

    if decision == "deny":
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }))
    # decision == "allow": print nothing, defer to normal permission flow.
    sys.exit(0)


if __name__ == "__main__":
    main()
