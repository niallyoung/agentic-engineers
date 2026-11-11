#!/usr/bin/env python3
"""
claude-delegate-guard.py — PreToolUse hook for Claude Code.

Enforces the DELEGATE/HANDBACK protocol at the one place it was previously
unenforced: the moment a live Claude Code session spawns one of the
agentic-engineers framework specialist agents via the Agent/Task tool, or
resumes one via SendMessage (src/AGENTS.md § Sub-Agent Reuse — a
continuation is a second delegation channel and carries a full DELEGATE).

Root cause this closes: DELEGATE validation logic exists in this repo
(src/skills/protocol-validator/scripts/protocol_validator.py), but was
written for the *simulated* Python orchestration pipeline, not the live
harness. When a real Claude Code session uses the Agent tool to spawn e.g.
"senior-engineer", nothing on the Claude Code side ever calls the
validator — a plain English prompt sails straight through. This script is
the missing mechanical gate for that exact path.

Deliberately NOT a thin wrapper around the existing protocol_validator.py:
  - protocol_validator.py additionally requires "skill" and "context" core
    fields and imports PyYAML. This hook only enforces the field subset the
    installing DELEGATE specified (handoff_type, agent, task_id, scope,
    plan, success_criteria; plus the optional depth/ancestry extension
    fields when present — see src/AGENTS.md § Recursion Limits and
    "Recursion-limit checks" below) and avoids
    a hard PyYAML dependency, because it runs as a subprocess under
    whatever bare `python3` is first on PATH at hook-execution time — not
    necessarily the repo's own virtualenv.
  - Historical note: delegate_validator.py (deleted after framework slimdown)
    used underscored role names (`senior_engineer`) inherited from an earlier
    convention; the live harness (agent frontmatter, src/AGENTS.md, rendered
    ~/.claude/agents/) uses hyphenated names throughout, which this hook
    enforces correctly.

Recursion-limit checks (what is and is not trusted):
  - The delegation depth is DERIVED from the ancestry length. ``ancestry``
    is the root-to-parent role chain, inclusive, so the agent being spawned
    sits at depth len(ancestry). A self-declared ``depth`` is never the
    basis for allowing a spawn: it is only cross-checked against that
    derived value, and any disagreement is refused. (Previously ``depth``
    was taken at face value and the ancestry length was never counted, so
    "depth: 1" with five ancestors — or a six-role ancestry with no depth
    at all — was allowed.)
  - A repeated ``ancestry:`` or ``depth:`` line anywhere in the prompt is
    refused. The flat parser keeps the last value for a repeated key, so a
    short decoy could override the real chain.
  - Still out of reach for a stateless, one-call-at-a-time hook: a DELEGATE
    that omits both fields, an ancestry that simply lies about the chain,
    concurrent fan-out, and a SendMessage to an opaque agent id that
    carries no DELEGATE block (the id cannot be mapped back to a role).

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
# src/AGENTS.md "Valid agents" list. Generic/utility agents (Explore, Plan,
# general-purpose, claude, statusline-setup, ...) are intentionally out of
# scope: they never accept [DELEGATE] in their frontmatter and are not bound
# by the protocol.
#
# Deliberately a hardcoded literal, NOT parsed from src/AGENTS.md at runtime:
# this script is stdlib-only (no PyYAML) and runs as a Claude Code PreToolUse
# hook subprocess outside the repo's own environment (see module docstring),
# so it cannot assume the repo — or even src/AGENTS.md — is reachable at
# hook-execution time. Roster drift between this literal and the canonical
# src/AGENTS.md table is instead caught repo-side by
# tests/test_claude_delegate_guard.py::TestFrameworkRolesMatchRoster, which
# parses the live roster with renderer/lib/agents_table.py and asserts the
# two sets are identical.
FRAMEWORK_ROLES = {
    "orchestrator",
    "engineer",
    "senior-engineer",
    "lead-engineer",
    "principal-engineer",
    "security-engineer",
    "quality-engineer",
}

# task_id: kebab-case, 3-50 chars — matches protocol_validator.py's TASK_ID_PATTERN.
TASK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$")

# src/AGENTS.md § Recursion Limits: max delegation depth 3 (depth 0 = root
# Orchestrator DELEGATE). An agent at depth 3 MUST NOT itself spawn.
MAX_DELEGATION_DEPTH = 3

# Tools that hand a prompt to a sub-agent. Task/Agent spawn one (the role is
# tool_input.subagent_type, the prompt is tool_input.prompt); SendMessage
# resumes one (the recipient is tool_input.to, the prompt is
# tool_input.message). Keep in sync with the matcher that
# renderer/scripts/render-claude.sh writes into settings.json — a tool
# missing from the matcher never reaches this script at all.
SPAWN_TOOLS = ("Task", "Agent")
CONTINUE_TOOLS = ("SendMessage",)

# Extension keys that may appear at most once in a prompt. Matched at any
# indentation and with optional quotes: an indented or quoted repeat is
# swallowed into the preceding field by parse_flat_fields(), but whoever
# reads the prompt still sees two competing values.
_SINGLETON_KEYS = ("ancestry", "depth")
_SINGLETON_KEY_RE = re.compile(
    r"""^[ \t]*['"]?(%s)['"]?[ \t]*:""" % "|".join(_SINGLETON_KEYS),
    re.MULTILINE,
)

# SendMessage recipients may carry a " [ref]" disambiguation suffix
# ("engineer [3fa9c1]"); it is not part of the name.
_RECIPIENT_REF_RE = re.compile(r"\s*\[[^\]]*\]\s*$")

# A single ancestry list item: a bare or quoted role-like token, used both
# for inline-array form (ancestry: [a, "b"]) and block-list form
# (- a \n - "b").
_ANCESTRY_ITEM_RE = re.compile(r"""^\s*-\s*['"]?([A-Za-z0-9_\-]+)['"]?\s*$""")

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
# Optional: ancestry ([role, ...], root-to-parent chain) — at most 3 roles,
# must not contain the target agent. Optional: depth — must equal the number
# of roles in ancestry. Each key may appear only once.
# See src/AGENTS.md § Recursion Limits.
"""


def _count_words(text):
    return len(text.split())


def _strip_inline_comment(value):
    """Strip a trailing ' # comment' from a scalar YAML value, then trim."""
    return value.split(" #", 1)[0].split("\t#", 1)[0].strip()


def _ancestry_field_lines(raw):
    """Return the lines of an ``ancestry`` field's raw value that belong to
    the field, with comments and blank lines removed.

    parse_flat_fields() hands a field every line up to the next top-level
    key, so the last field of a block also collects whatever follows the
    block: a closing ``---`` or code fence, or trailing prose. The field
    ends at the first later line that starts in column 0 and is not a list
    item, a comment, or the closing bracket of a multi-line inline array;
    everything from there on is not part of the value.
    """
    lines = raw.strip().splitlines()
    kept = []
    for index, line in enumerate(lines):
        if index > 0 and line[:1] not in ("", " ", "\t", "-", "#", "]"):
            break
        if index > 0 and line.startswith("---"):
            break
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        kept.append(_strip_inline_comment(line))
    return [line for line in kept if line.strip()]


def _parse_ancestry_items(raw):
    """Best-effort extraction of role-name items from an ``ancestry`` field's
    raw value text.

    Handles both forms used in DELEGATE blocks:
      - inline array: ``[orchestrator, "security-engineer"]``
      - block list:   ``- orchestrator`` / ``- "security-engineer"`` on
        their own lines following ``ancestry:``

    Returns a list of parsed items, lower-cased so that the cycle check
    cannot be dodged with a case variant of a role name. The list is empty
    if the value could not be recovered in either form — including when it
    is not *entirely* one of the two forms (an inline array followed by a
    second array or by list items, a block list with a non-item line).
    Reading only the part that parses would undercount the chain, and the
    count is what bounds the delegation depth.
    """
    lines = _ancestry_field_lines(raw)
    if not lines:
        return []

    if lines[0].lstrip().startswith("["):
        m = re.match(r"\s*\[([^\[\]]*)\]\s*\Z", "\n".join(lines), re.DOTALL)
        if not m:
            return []
        items = []
        for tok in m.group(1).split(","):
            tok = tok.strip().strip("'\"").strip()
            if not tok:
                continue
            if not re.match(r"^[A-Za-z0-9_\-]+$", tok):
                return []
            items.append(tok.lower())
        return items

    items = []
    for line in lines:
        m = _ANCESTRY_ITEM_RE.match(line)
        if not m:
            return []
        items.append(m.group(1).lower())
    return items


def find_duplicate_singleton_keys(text):
    """Return the sorted list of _SINGLETON_KEYS that occur more than once
    as a mapping key anywhere in ``text``.

    Deliberately scans the whole prompt rather than only the block the
    DELEGATE was parsed from: the receiving agent reads the entire prompt,
    so a second ``ancestry:`` outside a fenced DELEGATE block is just as
    ambiguous as one inside it.
    """
    if not isinstance(text, str):
        return []
    counts = {}
    for m in _SINGLETON_KEY_RE.finditer(text):
        counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    return sorted(key for key, n in counts.items() if n > 1)


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


def validate_delegate(fields, subagent_type, prompt=""):
    """Validate the DELEGATE core fields this hook enforces.

    ``subagent_type`` is the role the tool call targets, or None when it
    cannot be known (a SendMessage addressed to an opaque agent id) — the
    agent/target mismatch check is skipped in that case only. ``prompt`` is
    the full prompt text the DELEGATE was found in, used for the
    duplicate-key check.

    Deliberately narrower than the full canonical protocol-validator:
    ``skill`` and ``context`` are treated as out of scope for this hook (see
    module docstring) — it only enforces the field subset named in the
    DELEGATE that commissioned this hook: handoff_type, agent, task_id,
    scope (>=15 words), plan, success_criteria. Additionally validates the
    optional ``depth`` and ``ancestry`` extension fields (src/AGENTS.md §
    Recursion Limits) when present in the block; their absence is not an
    error — a DELEGATE that omits both behaves exactly as it did before
    these checks existed. See the module docstring, "Recursion-limit
    checks", for what is derived versus trusted.

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
    elif subagent_type is not None and agent != subagent_type:
        errors.append(
            "agent: DELEGATE targets %r but this tool call addresses "
            "%r — mismatch" % (agent, subagent_type)
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

    # --- Optional extension fields (src/AGENTS.md § Recursion Limits) ---
    # Both are additive/optional: a DELEGATE that omits them validates exactly
    # as it did before this check existed. When present, they are checked
    # only against what this single prompt declares — this hook sees one
    # call at a time and cannot count concurrent fan-out or track state
    # across spawns.
    for key in find_duplicate_singleton_keys(prompt):
        errors.append(
            "%s: duplicate key — '%s:' appears more than once in the prompt; "
            "it must appear exactly once so there is a single unambiguous value"
            % (key, key)
        )

    # The depth this spawn lands at is DERIVED from the ancestry (root-to-
    # parent chain, inclusive => the spawned agent is at depth len(ancestry)).
    # No ancestry means "spawned by the root", i.e. depth 0.
    ancestry_items = []
    ancestry_ok = True
    if "ancestry" in fields:
        ancestry_items = _parse_ancestry_items(fields.get("ancestry", ""))
        if not ancestry_items:
            ancestry_ok = False
            errors.append(
                "ancestry: present but could not be parsed as a role list (expected "
                "exactly one inline array like [role-a, role-b], or a block list of "
                "'- role' items, with nothing else in the field)"
            )
        else:
            if agent and agent.lower() in ancestry_items:
                errors.append(
                    "ancestry: cycle detected — target role %r already appears in "
                    "ancestry %s" % (agent, ancestry_items)
                )
            if len(ancestry_items) > MAX_DELEGATION_DEPTH:
                errors.append(
                    "ancestry: %d roles in ancestry puts this spawn at depth %d, "
                    "which exceeds max delegation depth %d"
                    % (len(ancestry_items), len(ancestry_items), MAX_DELEGATION_DEPTH)
                )
    derived_depth = len(ancestry_items)

    if "depth" in fields:
        depth_raw = _strip_inline_comment(fields.get("depth", ""))
        try:
            depth_val = int(depth_raw)
        except ValueError:
            errors.append("depth: must be a non-negative integer (got %r)" % depth_raw)
        else:
            if depth_val < 0:
                errors.append("depth: must be a non-negative integer (got %r)" % depth_raw)
            else:
                if depth_val > MAX_DELEGATION_DEPTH:
                    errors.append(
                        "depth: depth %d exceeds max delegation depth %d"
                        % (depth_val, MAX_DELEGATION_DEPTH)
                    )
                if ancestry_ok and depth_val != derived_depth:
                    errors.append(
                        "depth: declared depth %d does not match the depth derived "
                        "from ancestry (%d role(s) => depth %d); depth > 0 requires "
                        "an ancestry listing every role from the root to the "
                        "spawning parent" % (depth_val, derived_depth, derived_depth)
                    )

    return errors


def _normalise_role(value):
    """Lower-case/trim a role-like string; non-strings become ''. A case
    variant ("Senior-Engineer", " engineer ") must be guarded exactly like
    the canonical spelling."""
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def _deny_missing(target, where):
    return "deny", (
        "BLOCKED: %s framework specialist '%s' requires a canonical "
        "DELEGATE block (handoff_type: DELEGATE) in the %s; none was "
        "found.\n\nCanonical schema — embed this in the %s:\n%s\n"
        "See ~/.claude/AGENTS.md § DELEGATE/HANDBACK Protocol for full detail."
        % (where[0], target, where[1], where[1], CANONICAL_SCHEMA)
    )


def _deny_malformed(target, errors):
    error_list = "\n".join("  - %s" % e for e in errors)
    return "deny", (
        "BLOCKED: DELEGATE block for framework specialist '%s' is "
        "malformed:\n%s\n\nCanonical schema:\n%s"
        % (target, error_list, CANONICAL_SCHEMA)
    )


def decide(payload):
    """Given the parsed PreToolUse hook payload, return (decision, reason)
    where decision is "allow" or "deny" and reason is a human-readable
    string (only meaningful when decision == "deny").
    """
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}

    if tool_name in SPAWN_TOOLS:
        subagent_type = _normalise_role(tool_input.get("subagent_type", ""))
        if subagent_type not in FRAMEWORK_ROLES:
            # Generic/utility agent (Explore, Plan, general-purpose, claude,
            # ...) — not bound by the DELEGATE/HANDBACK protocol.
            return "allow", None

        prompt = tool_input.get("prompt", "")
        fields = find_delegate(prompt)
        if fields is None:
            return _deny_missing(subagent_type, ("spawning", "prompt"))
        errors = validate_delegate(fields, subagent_type, prompt)
        if errors:
            return _deny_malformed(subagent_type, errors)
        return "allow", None

    if tool_name in CONTINUE_TOOLS:
        # SendMessage resumes an existing agent. The recipient is a name or
        # an opaque agent id, not a subagent_type, so the role is only known
        # when the agent was named after its role.
        message = tool_input.get("message", "")
        recipient = tool_input.get("to", "")
        if isinstance(recipient, str):
            recipient = _RECIPIENT_REF_RE.sub("", recipient)
        recipient = _normalise_role(recipient)
        fields = find_delegate(message)

        if recipient in FRAMEWORK_ROLES:
            # Continuing a specialist: a full DELEGATE is mandatory
            # (src/AGENTS.md § Sub-Agent Reuse, "Full DELEGATE, new task_id").
            if fields is None:
                return _deny_missing(recipient, ("messaging", "message"))
            errors = validate_delegate(fields, recipient, message)
            if errors:
                return _deny_malformed(recipient, errors)
            return "allow", None

        if fields is not None:
            # Recipient's role is unknown (opaque id, or an agent not named
            # after a role), but the message is a DELEGATE: hold it to the
            # same rules, minus the agent/recipient cross-check.
            errors = validate_delegate(fields, None, message)
            if errors:
                target = _strip_inline_comment(fields.get("agent", "")) or "unknown"
                return _deny_malformed(target, errors)
        # Ordinary message (a reply to "main", a note to a teammate, ...).
        return "allow", None

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
