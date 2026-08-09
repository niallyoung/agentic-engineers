"""
Tests for renderer/scripts/claude-delegate-guard.py — the Claude Code
PreToolUse hook that enforces the DELEGATE/HANDBACK protocol at Agent/Task
tool spawn time.

Root cause this hook closes: DELEGATE validation logic already existed in
this repo (src/skills/protocol-validator, src/orchestration/agents/
delegate_validator.py) but neither was ever invoked from the live Claude
Code harness's Agent-tool spawn path — a plain-English prompt to e.g.
"senior-engineer" sailed straight through with zero mechanical enforcement.

The module under test is loaded via importlib (not a plain `import`)
because its filename contains hyphens and is not part of a Python package —
it is designed to run as a standalone hook subprocess, invoked by Claude
Code as `python3 <path>`.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD_SCRIPT = REPO_ROOT / "renderer" / "scripts" / "claude-delegate-guard.py"


def _load_guard_module():
    spec = importlib.util.spec_from_file_location("claude_delegate_guard", GUARD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def guard():
    return _load_guard_module()


# A real DELEGATE prompt in the exact shape framework agents receive it —
# modeled on an actual production DELEGATE (note: no "skill" field, which
# is deliberately not required by this hook; see module docstring in the
# hook itself for why).
VALID_DELEGATE_PROMPT = """handoff_type: DELEGATE
agent: senior-engineer
task_id: task-2026-08-09-example
model: fable-5
effort: high

scope: |
  Diagnose and fix the DELEGATE/HANDBACK protocol enforcement gap in the
  Claude Code harness of the agentic-engineers framework end to end.

context:
  - "Evidence: settings.json has no hooks."

plan:
  - "Step 1: Confirm root cause"
  - "Step 2: Design the hook"

success_criteria:
  - "AC1: Root cause documented"
"""


class TestFileExistsAndExecutable:
    def test_hook_script_exists(self):
        assert GUARD_SCRIPT.exists(), f"Hook script not found: {GUARD_SCRIPT}"

    def test_hook_script_executable(self):
        import os
        assert os.access(GUARD_SCRIPT, os.X_OK), f"Hook script not executable: {GUARD_SCRIPT}"

    def test_hook_script_has_shebang(self):
        first_line = GUARD_SCRIPT.read_text().splitlines()[0]
        assert first_line.startswith("#!/"), f"Missing shebang: {first_line}"


class TestParseFlatFields:
    def test_extracts_simple_scalar(self, guard):
        fields = guard.parse_flat_fields("task_id: my-task\nagent: engineer\n")
        assert fields["task_id"] == "my-task"
        assert fields["agent"] == "engineer"

    def test_extracts_block_scalar(self, guard):
        fields = guard.parse_flat_fields("scope: |\n  line one\n  line two\nplan:\n  - a\n")
        assert "line one" in fields["scope"]
        assert "line two" in fields["scope"]

    def test_extracts_list_field(self, guard):
        fields = guard.parse_flat_fields('plan:\n  - "Step 1: do a thing"\n  - "Step 2: do another"\n')
        assert fields["plan"].count("-") == 2

    def test_ignores_nested_colons(self, guard):
        # A nested "context:" style line inside a block scalar must not be
        # mistaken for a new top-level field (it's indented).
        fields = guard.parse_flat_fields("scope: |\n  indented: not a new key\nplan:\n  - x\n")
        assert "indented: not a new key" in fields["scope"]
        assert "plan" in fields


class TestFindDelegate:
    def test_finds_delegate_in_plain_prompt(self, guard):
        fields = guard.find_delegate(VALID_DELEGATE_PROMPT)
        assert fields is not None
        assert fields["agent"] == "senior-engineer"

    def test_finds_delegate_in_fenced_yaml_block(self, guard):
        prompt = "Here's the task:\n\n```yaml\n" + VALID_DELEGATE_PROMPT + "```\n\nThanks!"
        fields = guard.find_delegate(prompt)
        assert fields is not None
        assert fields["agent"] == "senior-engineer"

    def test_finds_delegate_with_leading_prose(self, guard):
        prompt = "Please handle this:\n\n" + VALID_DELEGATE_PROMPT
        fields = guard.find_delegate(prompt)
        assert fields is not None

    def test_accepts_deprecated_type_discriminator(self, guard):
        prompt = VALID_DELEGATE_PROMPT.replace("handoff_type: DELEGATE", "type: DELEGATE")
        fields = guard.find_delegate(prompt)
        assert fields is not None

    def test_returns_none_for_plain_english(self, guard):
        fields = guard.find_delegate(
            "Please fix the bug in foo.py where token validation is off by one."
        )
        assert fields is None

    def test_returns_none_for_empty_prompt(self, guard):
        assert guard.find_delegate("") is None
        assert guard.find_delegate(None) is None

    def test_returns_none_for_handback_not_delegate(self, guard):
        handback = "handoff_type: HANDBACK\ntask_id: x\nstatus: success\n"
        assert guard.find_delegate(handback) is None


class TestValidateDelegate:
    def test_valid_delegate_has_no_errors(self, guard):
        fields = guard.find_delegate(VALID_DELEGATE_PROMPT)
        errors = guard.validate_delegate(fields, "senior-engineer")
        assert errors == []

    def test_missing_task_id(self, guard):
        prompt = VALID_DELEGATE_PROMPT.replace("task_id: task-2026-08-09-example\n", "")
        fields = guard.find_delegate(prompt)
        errors = guard.validate_delegate(fields, "senior-engineer")
        assert any("task_id" in e for e in errors)

    def test_bad_task_id_format(self, guard):
        prompt = VALID_DELEGATE_PROMPT.replace(
            "task_id: task-2026-08-09-example", "task_id: NOT_kebab_case!"
        )
        fields = guard.find_delegate(prompt)
        errors = guard.validate_delegate(fields, "senior-engineer")
        assert any("task_id" in e for e in errors)

    def test_scope_too_short(self, guard):
        prompt = VALID_DELEGATE_PROMPT.split("scope:")[0] + "scope: fix it\nplan:\n  - a\nsuccess_criteria:\n  - b\n"
        fields = guard.find_delegate(prompt)
        errors = guard.validate_delegate(fields, "senior-engineer")
        assert any("scope" in e for e in errors)

    def test_missing_plan(self, guard):
        lines = [l for l in VALID_DELEGATE_PROMPT.splitlines() if not l.startswith("plan") and l.strip() != '- "Step 1: Confirm root cause"' and l.strip() != '- "Step 2: Design the hook"']
        fields = guard.parse_flat_fields("\n".join(lines))
        errors = guard.validate_delegate(fields, "senior-engineer")
        assert any("plan" in e for e in errors)

    def test_missing_success_criteria(self, guard):
        lines = [l for l in VALID_DELEGATE_PROMPT.splitlines() if not l.startswith("success_criteria") and l.strip() != '- "AC1: Root cause documented"']
        fields = guard.parse_flat_fields("\n".join(lines))
        errors = guard.validate_delegate(fields, "senior-engineer")
        assert any("success_criteria" in e for e in errors)

    def test_agent_not_a_framework_role(self, guard):
        prompt = VALID_DELEGATE_PROMPT.replace("agent: senior-engineer", "agent: not-a-real-role")
        fields = guard.find_delegate(prompt)
        errors = guard.validate_delegate(fields, "senior-engineer")
        assert any("invalid agent" in e for e in errors)

    def test_agent_subagent_type_mismatch(self, guard):
        fields = guard.find_delegate(VALID_DELEGATE_PROMPT)  # agent: senior-engineer
        errors = guard.validate_delegate(fields, "engineer")  # spawned as engineer
        assert any("mismatch" in e for e in errors)

    def test_skill_and_context_not_required(self, guard):
        """This hook deliberately does not require 'skill' or 'context' —
        narrower than the full protocol-validator (see hook docstring)."""
        fields = guard.find_delegate(VALID_DELEGATE_PROMPT)
        assert "skill" not in fields
        errors = guard.validate_delegate(fields, "senior-engineer")
        assert errors == []


class TestDecide:
    def test_allows_non_agent_tool(self, guard):
        decision, reason = guard.decide({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        assert decision == "allow"

    def test_allows_non_framework_subagent(self, guard):
        decision, reason = guard.decide({
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "general-purpose", "prompt": "go explore the repo"},
        })
        assert decision == "allow"

    def test_allows_valid_delegate(self, guard):
        decision, reason = guard.decide({
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "senior-engineer", "prompt": VALID_DELEGATE_PROMPT},
        })
        assert decision == "allow"

    def test_allows_valid_delegate_via_task_tool_name(self, guard):
        decision, reason = guard.decide({
            "tool_name": "Task",
            "tool_input": {"subagent_type": "senior-engineer", "prompt": VALID_DELEGATE_PROMPT},
        })
        assert decision == "allow"

    def test_denies_plain_english_prompt_to_framework_role(self, guard):
        decision, reason = guard.decide({
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "engineer",
                "prompt": "Please fix the token validation bug in foo.py.",
            },
        })
        assert decision == "deny"
        assert "DELEGATE" in reason
        assert "handoff_type: DELEGATE" in reason  # canonical schema included for retry

    def test_denies_malformed_delegate(self, guard):
        prompt = VALID_DELEGATE_PROMPT.replace("task_id: task-2026-08-09-example\n", "")
        decision, reason = guard.decide({
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "senior-engineer", "prompt": prompt},
        })
        assert decision == "deny"
        assert "task_id" in reason

    def test_denies_missing_prompt(self, guard):
        decision, reason = guard.decide({
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "engineer"},
        })
        assert decision == "deny"


class TestSubprocessContract:
    """End-to-end tests invoking the hook exactly as Claude Code would:
    JSON on stdin, JSON (or nothing) on stdout, exit code 0 always."""

    def _run(self, payload):
        proc = subprocess.run(
            [sys.executable, str(GUARD_SCRIPT)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return proc

    def test_exit_code_always_zero_on_allow(self):
        proc = self._run({
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "senior-engineer", "prompt": VALID_DELEGATE_PROMPT},
        })
        assert proc.returncode == 0
        assert proc.stdout.strip() == ""

    def test_exit_code_always_zero_on_deny(self):
        proc = self._run({
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "engineer", "prompt": "just do it"},
        })
        assert proc.returncode == 0
        payload = json.loads(proc.stdout)
        hso = payload["hookSpecificOutput"]
        assert hso["hookEventName"] == "PreToolUse"
        assert hso["permissionDecision"] == "deny"
        assert "permissionDecisionReason" in hso

    def test_fails_open_on_malformed_stdin(self):
        proc = subprocess.run(
            [sys.executable, str(GUARD_SCRIPT)],
            input="not valid json {{{",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc.returncode == 0
        assert proc.stdout.strip() == ""

    def test_fails_open_on_missing_tool_input(self):
        proc = self._run({"tool_name": "Agent"})
        # subagent_type missing/empty -> not a framework role -> allow
        assert proc.returncode == 0
        assert proc.stdout.strip() == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
