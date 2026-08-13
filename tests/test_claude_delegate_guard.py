"""
Tests for renderer/scripts/claude-delegate-guard.py — the Claude Code
PreToolUse hook that is the live enforcement point for the DELEGATE protocol
(see src/AGENTS.md > Direct Sub-Agent Spawn Execution Model).

tests/test_claude_hook_installation.py covers installation mechanics (hook
file written, wired into settings.json, marker files, install/uninstall
idempotency) but never exercises the guard's actual allow/deny decision
logic — this file closes that gap by piping PreToolUse-shaped JSON payloads
into the script over stdin/stdout, exactly as Claude Code's hook runtime
does, and asserting the resulting permission decision.

The old tests/test_fable5_defensive_gate.py (deleted in WP-1, framework
slimdown) targeted src/orchestration's DelegateValidator, a simulated-pipeline
component with no bearing on a live harness session. This is not a revival of
that file — claude-delegate-guard.py is a different implementation with a
different (hook) contract; see the module's own docstring for why it is
deliberately not a thin wrapper around any of the older validators.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GUARD = REPO_ROOT / "renderer" / "scripts" / "claude-delegate-guard.py"
AGENTS_MD = REPO_ROOT / "src" / "AGENTS.md"

VALID_DELEGATE_PROMPT = """\
handoff_type: DELEGATE
agent: engineer
task_id: fix-login-timeout-bug
scope: |
  Fix the login timeout bug in the authentication service by extending the
  grace period and adding a regression test for the expired-token path.
plan:
  - "Step 1: Reproduce the timeout with a failing test"
  - "Step 2: Extend the grace period and verify the test passes"
success_criteria:
  - "AC1: Regression test passes"
"""


def run_guard(payload):
    """Pipe a PreToolUse payload into the guard and return the parsed
    hookSpecificOutput dict, or None if the hook printed nothing (allow)."""
    result = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"guard must always exit 0 (fail open), got {result.returncode}: {result.stderr}"
    )
    out = result.stdout.strip()
    if not out:
        return None
    return json.loads(out)["hookSpecificOutput"]


def _task_payload(subagent_type, prompt):
    return {
        "tool_name": "Task",
        "tool_input": {"subagent_type": subagent_type, "prompt": prompt},
    }


class TestValidDelegateAllowed:
    def test_valid_delegate_to_specialist_is_allowed(self):
        payload = _task_payload("engineer", VALID_DELEGATE_PROMPT)
        assert run_guard(payload) is None, "a well-formed DELEGATE must be allowed (no output)"

    def test_valid_delegate_wrapped_in_fenced_block_is_allowed(self):
        prompt = "Please run this task:\n\n```yaml\n" + VALID_DELEGATE_PROMPT + "\n```\n"
        payload = _task_payload("engineer", prompt)
        assert run_guard(payload) is None


class TestMissingOrMalformedFieldsDenied:
    def test_no_delegate_block_at_all_is_denied(self):
        payload = _task_payload("engineer", "Please just fix the bug, thanks.")
        decision = run_guard(payload)
        assert decision["permissionDecision"] == "deny"
        assert "requires a canonical" in decision["permissionDecisionReason"]

    def test_missing_scope_is_denied(self):
        prompt = VALID_DELEGATE_PROMPT.replace(
            'scope: |\n  Fix the login timeout bug in the authentication service by extending the\n  grace period and adding a regression test for the expired-token path.\n',
            "",
        )
        decision = run_guard(_task_payload("engineer", prompt))
        assert decision["permissionDecision"] == "deny"
        assert "scope" in decision["permissionDecisionReason"]

    def test_short_scope_is_denied(self):
        prompt = VALID_DELEGATE_PROMPT.replace(
            "Fix the login timeout bug in the authentication service by extending the\n  grace period and adding a regression test for the expired-token path.",
            "Too short.",
        )
        decision = run_guard(_task_payload("engineer", prompt))
        assert decision["permissionDecision"] == "deny"
        assert ">=15 words" in decision["permissionDecisionReason"]

    def test_agent_field_mismatch_with_subagent_type_is_denied(self):
        # DELEGATE targets 'engineer' but the Agent-tool call spawns 'lead-engineer'.
        decision = run_guard(_task_payload("lead-engineer", VALID_DELEGATE_PROMPT))
        assert decision["permissionDecision"] == "deny"
        assert "mismatch" in decision["permissionDecisionReason"]

    def test_invalid_task_id_shape_is_denied(self):
        prompt = VALID_DELEGATE_PROMPT.replace(
            "task_id: fix-login-timeout-bug", "task_id: NOT_kebab_case!"
        )
        decision = run_guard(_task_payload("engineer", prompt))
        assert decision["permissionDecision"] == "deny"
        assert "task_id" in decision["permissionDecisionReason"]


class TestNonFrameworkAgentsIgnored:
    @pytest.mark.parametrize(
        "subagent_type", ["Explore", "general-purpose", "Plan", "claude", "statusline-setup"]
    )
    def test_generic_agent_is_not_gated(self, subagent_type):
        # No DELEGATE block at all — would be denied for a framework role.
        payload = _task_payload(subagent_type, "Go find where X is defined.")
        assert run_guard(payload) is None

    def test_non_task_tool_is_ignored(self):
        payload = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
        assert run_guard(payload) is None


class TestFailsOpen:
    def test_unparseable_stdin_exits_zero_and_allows(self):
        result = subprocess.run(
            [sys.executable, str(GUARD)],
            input="not json at all {{{",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""


class TestGuardDecisionSurface:
    """Extended decision-surface tests for edge cases and field variations."""

    def test_agent_tool_name_allowed_like_task_tool_name(self):
        """The guard should accept 'Agent' tool_name equally to 'Task'."""
        payload = {
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "engineer", "prompt": VALID_DELEGATE_PROMPT},
        }
        assert run_guard(payload) is None, "Agent tool with valid DELEGATE must be allowed"

    def test_deprecated_type_discriminator_is_accepted(self):
        """The guard accepts the deprecated 'type: DELEGATE' discriminator for compatibility."""
        prompt = VALID_DELEGATE_PROMPT.replace("handoff_type: DELEGATE", "type: DELEGATE")
        payload = _task_payload("engineer", prompt)
        assert run_guard(payload) is None, "deprecated 'type: DELEGATE' must still be allowed"

    def test_decoy_fenced_block_before_real_delegate(self):
        """A non-DELEGATE fenced block followed by a real DELEGATE should pass."""
        prompt = """\
Here is some example code:

```python
def example():
    type: "not a DELEGATE"
    pass
```

Now the real task:

```yaml
handoff_type: DELEGATE
agent: engineer
task_id: fix-login-timeout-bug
scope: |
  Fix the login timeout bug in the authentication service by extending the
  grace period and adding a regression test for the expired-token path.
plan:
  - "Step 1: Reproduce the timeout with a failing test"
  - "Step 2: Extend the grace period and verify the test passes"
success_criteria:
  - "AC1: Regression test passes"
"""
        payload = _task_payload("engineer", prompt)
        assert run_guard(payload) is None, "real DELEGATE after decoy block must be allowed"

    def test_missing_subagent_type_allows_for_generic_agents(self):
        """If subagent_type is missing or not a framework role, the tool call is allowed."""
        payload = {
            "tool_name": "Task",
            "tool_input": {"prompt": "Just explore the codebase"},
        }
        assert run_guard(payload) is None, "missing subagent_type should allow (generic agent)"

    def test_scope_word_count_with_block_scalar_indentation(self):
        """Scope word count should correctly count words even with block-scalar indentation."""
        # Block scalar indentation should not be counted as extra words.
        prompt = """\
handoff_type: DELEGATE
agent: engineer
task_id: test-word-count
scope: |
  This scope text has at least fifteen words
  spread across multiple indented lines
  to verify the word-count logic correctly
  strips indentation and counts actual words
plan:
  - "Step 1: Test"
success_criteria:
  - "AC1: Passes"
"""
        payload = _task_payload("engineer", prompt)
        # Should pass because the scope has enough words when indentation is stripped.
        assert run_guard(payload) is None, "word count should ignore indentation"

    def test_scope_word_count_fails_on_insufficient_words(self):
        """Scope with fewer than 15 words should be denied."""
        prompt = """\
handoff_type: DELEGATE
agent: engineer
task_id: test-short-scope
scope: Not enough words here
plan:
  - "Step 1: Test"
success_criteria:
  - "AC1: Passes"
"""
        payload = _task_payload("engineer", prompt)
        decision = run_guard(payload)
        assert decision["permissionDecision"] == "deny"
        assert ">=15 words" in decision["permissionDecisionReason"]


class TestInstalledPathExecution:
    """G9 test: verify the guard runs correctly when installed to a temp DESTDIR."""

    def test_guard_installed_and_executed_as_hook_subprocess(self, tmp_path):
        """
        Render the harness into a temp DESTDIR, extract the PreToolUse hook
        command path from settings.json, execute it as a subprocess with a
        deny-worthy payload, and assert the deny JSON is returned.

        This proves the INSTALLED wiring (not just the repo copy) works end-to-end.
        """
        import tempfile
        import shutil

        # Create a temp install directory.
        destdir = tmp_path / "test-install"
        destdir.mkdir()

        # Run 'make install-claude DESTDIR=<destdir>' to render + install.
        result = subprocess.run(
            ["make", "install-claude", f"DESTDIR={destdir}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"make install-claude failed: {result.stderr}"

        # Load settings.json from the installed location.
        settings_json = destdir / ".claude" / "settings.json"
        assert settings_json.exists(), f"settings.json not found at {settings_json}"

        with open(settings_json) as f:
            settings = json.load(f)

        # Extract the PreToolUse hook command from settings.
        hooks = settings.get("hooks", {}).get("PreToolUse", [])
        assert hooks, "No PreToolUse hooks found in settings.json"

        hook_command = None
        for hook_entry in hooks:
            for hook in hook_entry.get("hooks", []):
                if hook.get("type") == "command":
                    hook_command = hook.get("command")
                    break

        assert hook_command, "No hook command found in settings.json"

        # The hook command should point to the installed guard script.
        assert "claude-delegate-guard.py" in hook_command, (
            f"Hook command doesn't reference claude-delegate-guard.py: {hook_command}"
        )

        # Execute the hook command via subprocess with a deny-worthy payload
        # (missing DELEGATE block).
        deny_payload = {
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "engineer",
                "prompt": "Please fix the bug without a DELEGATE block.",
            },
        }

        # Parse the hook command to extract the script path and args.
        import shlex
        hook_parts = shlex.split(hook_command)

        result = subprocess.run(
            hook_parts,
            input=json.dumps(deny_payload),
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, (
            f"installed hook must exit 0 (fail open), got {result.returncode}: {result.stderr}"
        )

        # The hook should output a deny JSON.
        assert result.stdout.strip(), "installed hook should produce deny output"
        output = json.loads(result.stdout)
        decision = output.get("hookSpecificOutput", {})
        assert (
            decision.get("permissionDecision") == "deny"
        ), f"installed hook should deny missing DELEGATE, got: {output}"
        assert (
            "requires a canonical" in decision.get("permissionDecisionReason", "")
        ), "deny reason should mention canonical DELEGATE"


class TestFrameworkRolesMatchRoster:
    """FRAMEWORK_ROLES in claude-delegate-guard.py is a hardcoded literal by
    design (see the module's own comment: the guard is stdlib-only and runs
    outside the repo as a Claude Code hook, so it deliberately does not parse
    src/AGENTS.md at runtime). That means it can silently drift from the
    canonical roster if a role is ever added, renamed, or removed in
    src/AGENTS.md without updating the hook. This test is the repo-side
    tripwire for that drift: it parses the live roster with the canonical
    Python parser (renderer/lib/agents_table.py — the same one
    render-codex.py uses, pinned to the bash parser by
    tests/test_agents_table_parity.py) and asserts the role sets match
    exactly.
    """

    @staticmethod
    def _load_guard_module():
        spec = importlib.util.spec_from_file_location("claude_delegate_guard", GUARD)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def _roster_roles():
        lib_dir = REPO_ROOT / "renderer" / "lib"
        if str(lib_dir) not in sys.path:
            sys.path.insert(0, str(lib_dir))
        from agents_table import parse_agents_table

        return {row["role"] for row in parse_agents_table(AGENTS_MD)}

    def test_framework_roles_equals_live_roster_roles(self):
        guard = self._load_guard_module()
        roster_roles = self._roster_roles()
        assert guard.FRAMEWORK_ROLES == roster_roles, (
            "renderer/scripts/claude-delegate-guard.py's hardcoded FRAMEWORK_ROLES "
            "has drifted from src/AGENTS.md's Agent Roster table. Update "
            "FRAMEWORK_ROLES to match (it must stay a hardcoded literal — see the "
            "guard's module docstring for why it doesn't parse AGENTS.md at "
            f"runtime).\nFRAMEWORK_ROLES: {sorted(guard.FRAMEWORK_ROLES)}\n"
            f"roster roles:    {sorted(roster_roles)}"
        )
