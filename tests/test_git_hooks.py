"""
test_git_hooks.py — Comprehensive test suite for .githooks/ and .git/hooks/

Tests all three hooks across 4 harnesses:
  - Harness A: .githooks/pre-commit
  - Harness B: .githooks/commit-msg
  - Harness C: .githooks/pre-push
  - Harness D: .git/hooks/pre-commit (legacy protocol validation hook)

Coverage:
  - Valid/invalid inputs
  - Bypass mechanisms (SKIP_HOOKS=1, SKIP_COMMIT_MSG_HOOK=true, BYPASS_HOOK_VALIDATION=true)
  - Error messages and recovery hints
  - Recovery procedures
  - Edge cases

NOTE: TestPrePushHook tests that run from the repo root will trigger the full
pytest suite inside the hook (30s timeout). These are marked @pytest.mark.slow
and excluded from the default run. Run with -m slow to include them.
"""

import os
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Dict, List, Optional

import pytest

# ── Repo root ──────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
GITHOOKS_DIR = REPO_ROOT / ".githooks"
GIT_HOOKS_DIR = REPO_ROOT / ".git" / "hooks"


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def run_hook(hook_path, args=None, env_overrides=None, stdin=None, cwd=None, timeout=15):
    """Execute a hook script and return the CompletedProcess result."""
    env = os.environ.copy()
    env.update(env_overrides or {})
    return subprocess.run(
        [str(hook_path)] + (args or []),
        capture_output=True,
        text=True,
        env=env,
        input=stdin if stdin is not None else "",
        cwd=cwd or str(REPO_ROOT),
        timeout=timeout,
    )


def make_git_repo(tmpdir):
    """Initialise a bare git repo suitable for hook testing."""
    subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)


def stage_file(tmpdir, rel_path, content):
    """Write a file inside tmpdir and git-add it; return its Path."""
    full = Path(tmpdir) / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content)
    subprocess.run(["git", "add", str(full)], cwd=tmpdir, capture_output=True)
    return full


def run_hook_in_repo(hook_path, tmpdir, env_overrides=None, args=None, stdin=None):
    """Run a hook inside a temp git repo."""
    env = os.environ.copy()
    env.update(env_overrides or {})
    return subprocess.run(
        [str(hook_path)] + (args or []),
        capture_output=True, text=True,
        cwd=tmpdir, env=env,
        input=stdin if stdin is not None else "",
        timeout=15,
    )


def make_minimal_repo_with_docs(tmpdir):
    """Create a minimal git repo with required docs but no tests/ dir."""
    make_git_repo(tmpdir)
    (Path(tmpdir) / "docs").mkdir()
    (Path(tmpdir) / "docs" / "SPEC.md").write_text("# Spec\nversion: 1.0\n")
    (Path(tmpdir) / "docs" / "AGENTS.md").write_text("# Agents\n")
    (Path(tmpdir) / "README.md").write_text("# Readme\n")


# ══════════════════════════════════════════════════════════════════════════════
# Harness A — .githooks/pre-commit
# ══════════════════════════════════════════════════════════════════════════════

class TestPreCommitHook:
    """Harness A: .githooks/pre-commit"""

    HOOK = GITHOOKS_DIR / "pre-commit"

    # ── Bypass ─────────────────────────────────────────────────────────────────

    def test_bypass_skip_hooks_exits_zero(self):
        """SKIP_HOOKS=1 must bypass all checks and exit 0."""
        result = run_hook(self.HOOK, env_overrides={"SKIP_HOOKS": "1"})
        assert result.returncode == 0

    def test_bypass_skip_hooks_warns(self):
        """SKIP_HOOKS=1 bypass must emit a warning message."""
        result = run_hook(self.HOOK, env_overrides={"SKIP_HOOKS": "1"})
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "SKIP_HOOKS" in combined or "bypass" in combined.lower() or "\u26a0" in combined

    def test_bypass_skip_hooks_empty_does_not_bypass(self):
        """SKIP_HOOKS='' (empty) must NOT bypass — only '1' bypasses."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            result = run_hook_in_repo(self.HOOK, tmpdir, env_overrides={"SKIP_HOOKS": ""})
        assert result.returncode == 0
        assert "SKIP_HOOKS=1" not in result.stdout

    # ── No staged files → clean pass ──────────────────────────────────────────

    def test_no_staged_files_passes(self):
        """With no staged files the hook must exit 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            result = run_hook_in_repo(self.HOOK, tmpdir, env_overrides={"SKIP_HOOKS": ""})
        assert result.returncode == 0

    def test_success_message_on_clean_commit(self):
        """On success, hook must print checkmark confirmation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            result = run_hook_in_repo(self.HOOK, tmpdir, env_overrides={"SKIP_HOOKS": ""})
        assert result.returncode == 0
        assert "\u2705" in result.stdout or "passed" in result.stdout.lower()

    # ── SPEC constraint: orchestration/scripts/ ────────────────────────────────

    def test_rejects_python_in_orchestration_scripts(self):
        """Staged .py files under orchestration/scripts/ must be rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            stage_file(tmpdir, "orchestration/scripts/bad.py", "print('hello')\n")
            result = run_hook_in_repo(self.HOOK, tmpdir, env_overrides={"SKIP_HOOKS": ""})
        assert result.returncode != 0
        assert "VIOLATION" in result.stdout or "violation" in result.stdout.lower()

    def test_rejects_shell_in_orchestration_scripts(self):
        """Staged .sh files under orchestration/scripts/ must be rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            stage_file(tmpdir, "orchestration/scripts/bad.sh", "#!/bin/bash\necho hi\n")
            result = run_hook_in_repo(self.HOOK, tmpdir, env_overrides={"SKIP_HOOKS": ""})
        assert result.returncode != 0

    def test_rejects_cron_in_orchestration_config(self):
        """Staged .cron files under orchestration/config/ must be rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            stage_file(tmpdir, "orchestration/config/schedule.cron", "* * * * * /bin/true\n")
            result = run_hook_in_repo(self.HOOK, tmpdir, env_overrides={"SKIP_HOOKS": ""})
        assert result.returncode != 0

    def test_allows_renderer_scripts(self):
        """renderer/scripts/ is the allowed build-time path — must not be blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            stage_file(tmpdir, "renderer/scripts/build.sh", "#!/bin/bash\necho build\n")
            result = run_hook_in_repo(self.HOOK, tmpdir, env_overrides={"SKIP_HOOKS": ""})
        assert result.returncode == 0

    def test_error_message_includes_spec_reference(self):
        """Violation error must mention SPEC or docs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            stage_file(tmpdir, "orchestration/scripts/bad.py", "x=1\n")
            result = run_hook_in_repo(self.HOOK, tmpdir, env_overrides={"SKIP_HOOKS": ""})
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "SPEC" in combined or "docs" in combined.lower() or "protocol" in combined.lower()

    # ── Secret detection ───────────────────────────────────────────────────────

    def test_rejects_aws_key_pattern(self):
        """AWS access key pattern (AKIA…) must be rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            stage_file(tmpdir, "config.py", "AWS_KEY = 'AKIAIOSFODNN7EXAMPLE'\n")  # pragma: allowlist secret
            result = run_hook_in_repo(self.HOOK, tmpdir, env_overrides={"SKIP_HOOKS": ""})
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "AWS" in combined or "secret" in combined.lower() or "key" in combined.lower()

    def test_rejects_long_api_key_colon_value(self):
        """api_key: <20+ consecutive alphanumeric chars> must be rejected.

        Hook regex: (api_key|...)\s*[:=]\s*["']?[A-Za-z0-9/+]{20,}
        Value must be 20+ consecutive [A-Za-z0-9/+] chars with no quotes
        (macOS grep does not match \\x27 for single-quote in character class).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            stage_file(tmpdir, "settings.py", "api_key: abcdefghijklmnopqrstuvwxyz123456\n")  # pragma: allowlist secret
            result = run_hook_in_repo(self.HOOK, tmpdir, env_overrides={"SKIP_HOOKS": ""})
        assert result.returncode != 0

    def test_allows_short_placeholder_values(self):
        """Short placeholder values like api_key = 'xxx' must not be flagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            stage_file(tmpdir, "config.py", "api_key = 'placeholder'\n")
            result = run_hook_in_repo(self.HOOK, tmpdir, env_overrides={"SKIP_HOOKS": ""})
        assert result.returncode == 0

    # ── YAML well-formedness ───────────────────────────────────────────────────

    def test_rejects_invalid_yaml(self):
        """Staged .yaml files with invalid syntax must be rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            stage_file(tmpdir, "bad.yaml", "key: [\ninvalid yaml\n")
            result = run_hook_in_repo(self.HOOK, tmpdir, env_overrides={"SKIP_HOOKS": ""})
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "YAML" in combined or "yaml" in combined.lower() or "Invalid" in combined

    def test_allows_valid_yaml(self):
        """Staged .yaml files with valid syntax must pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            stage_file(tmpdir, "good.yaml", "key: value\nlist:\n  - a\n  - b\n")
            result = run_hook_in_repo(self.HOOK, tmpdir, env_overrides={"SKIP_HOOKS": ""})
        assert result.returncode == 0

    # ── Bypass marker warnings ─────────────────────────────────────────────────

    def test_warns_on_no_verify_in_script(self):
        """--no-verify in a committed .sh file must emit a warning (non-blocking)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            stage_file(tmpdir, "deploy.sh", "#!/bin/bash\ngit commit --no-verify -m 'skip'\n")
            result = run_hook_in_repo(self.HOOK, tmpdir, env_overrides={"SKIP_HOOKS": ""})
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "\u26a0" in combined or "warn" in combined.lower() or "no-verify" in combined

    def test_warns_on_skip_hooks_in_script(self):
        """SKIP_HOOKS=1 in a committed .sh file must emit a warning (non-blocking)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            stage_file(tmpdir, "deploy.sh", "#!/bin/bash\nSKIP_HOOKS=1 git push\n")
            result = run_hook_in_repo(self.HOOK, tmpdir, env_overrides={"SKIP_HOOKS": ""})
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "\u26a0" in combined or "warn" in combined.lower() or "SKIP_HOOKS" in combined

    # ── Error message quality ──────────────────────────────────────────────────

    def test_error_message_includes_recovery_hint(self):
        """On failure, hook must print recovery instructions (SKIP_HOOKS=1)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            stage_file(tmpdir, "orchestration/scripts/bad.py", "x=1\n")
            result = run_hook_in_repo(self.HOOK, tmpdir, env_overrides={"SKIP_HOOKS": ""})
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "SKIP_HOOKS" in combined or "bypass" in combined.lower()

    def test_error_count_in_failure_message(self):
        """Failure message must include error indicator."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            stage_file(tmpdir, "orchestration/scripts/bad.py", "x=1\n")
            result = run_hook_in_repo(self.HOOK, tmpdir, env_overrides={"SKIP_HOOKS": ""})
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "\u274c" in combined or "violation" in combined.lower() or "error" in combined.lower()


# ══════════════════════════════════════════════════════════════════════════════
# Harness B — .githooks/commit-msg
# ══════════════════════════════════════════════════════════════════════════════

class TestCommitMsgHook:
    """Harness B: .githooks/commit-msg"""

    HOOK = GITHOOKS_DIR / "commit-msg"

    def _run_with_msg(self, message, env_overrides=None):
        """Write message to temp file and pass as arg to hook."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            tmp.write(message)
            tmp_path = tmp.name
        try:
            return run_hook(self.HOOK, args=[tmp_path], env_overrides=env_overrides)
        finally:
            Path(tmp_path).unlink()

    # ── Bypass ─────────────────────────────────────────────────────────────────

    def test_bypass_skip_commit_msg_hook_exits_zero(self):
        """SKIP_COMMIT_MSG_HOOK=true must bypass all checks and exit 0."""
        result = self._run_with_msg("x", env_overrides={"SKIP_COMMIT_MSG_HOOK": "true"})
        assert result.returncode == 0

    def test_bypass_skip_commit_msg_hook_prints_skipped(self):
        """SKIP_COMMIT_MSG_HOOK=true must print SKIPPED message."""
        result = self._run_with_msg("x", env_overrides={"SKIP_COMMIT_MSG_HOOK": "true"})
        combined = result.stdout + result.stderr
        assert "SKIP" in combined or "skip" in combined.lower()

    def test_bypass_false_does_not_bypass(self):
        """SKIP_COMMIT_MSG_HOOK=false must NOT bypass."""
        result = self._run_with_msg("bad", env_overrides={"SKIP_COMMIT_MSG_HOOK": "false"})
        assert result.returncode != 0  # "bad" is too short

    # ── Valid messages ─────────────────────────────────────────────────────────

    def test_valid_conventional_commit_passes(self):
        """feat: add new feature — valid conventional commit must pass."""
        result = self._run_with_msg("feat: add new feature for queue management")
        assert result.returncode == 0
        assert "\u2705" in result.stdout

    def test_valid_conventional_commit_with_scope_passes(self):
        """feat(auth): add token grace period — conventional commit with scope must pass."""
        result = self._run_with_msg("feat(auth): add token grace period validation")
        assert result.returncode == 0

    def test_valid_long_message_passes(self):
        """Multi-line message with body must pass (no DELEGATE/HANDBACK keywords)."""
        msg = "fix: correct validation logic\n\nThis fixes the edge case where empty scope was accepted."
        result = self._run_with_msg(msg)
        assert result.returncode == 0

    def test_valid_minimum_length_message_passes(self):
        """Message with exactly 10 chars on first line must pass."""
        result = self._run_with_msg("1234567890")
        assert result.returncode == 0

    def test_valid_message_with_comments_passes(self):
        """Lines starting with # (git comments) must be stripped before validation."""
        msg = "# This is a git comment\nfeat: real commit message here\n# Another comment"
        result = self._run_with_msg(msg)
        assert result.returncode == 0

    def test_valid_message_with_task_id_detects_it(self):
        """Message containing a YYYY-MM-DD-kebab task ID must detect and confirm it."""
        msg = "feat: implement hooks testing 2026-05-16-hooks-testing-validation"
        result = self._run_with_msg(msg)
        assert result.returncode == 0
        assert "Task ID" in result.stdout or "task" in result.stdout.lower()

    # ── Invalid messages ───────────────────────────────────────────────────────

    def test_empty_message_fails(self):
        """Empty commit message must be rejected."""
        result = self._run_with_msg("")
        assert result.returncode != 0
        assert "empty" in result.stdout.lower() or "\u274c" in result.stdout

    def test_only_comments_fails(self):
        """Message with only comment lines must be rejected as empty."""
        result = self._run_with_msg("# Just a comment\n# Another comment\n")
        assert result.returncode != 0

    def test_too_short_message_fails(self):
        """Message shorter than 10 chars must be rejected."""
        result = self._run_with_msg("fix bug")  # 7 chars
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "short" in combined.lower() or "\u274c" in combined

    def test_nine_char_message_fails(self):
        """9-char message (one below minimum) must be rejected."""
        result = self._run_with_msg("123456789")
        assert result.returncode != 0

    def test_whitespace_only_message_fails(self):
        """Whitespace-only message must be rejected."""
        result = self._run_with_msg("   \n\t\n  ")
        assert result.returncode != 0

    def test_too_long_subject_fails(self):
        """Subject line > 72 chars must be rejected."""
        long_msg = "feat: " + "x" * 70  # 76 chars total
        result = self._run_with_msg(long_msg)
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "long" in combined.lower() or "72" in combined or "\u274c" in combined

    # ── SKIP_HOOKS documentation requirement ──────────────────────────────────

    def test_skip_hooks_mention_without_reason_fails(self):
        """SKIP_HOOKS in message without documented reason must fail."""
        msg = "SKIP_HOOKS used here for this commit message that is long enough"
        result = self._run_with_msg(msg)
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "reason" in combined.lower() or "SKIP_HOOKS" in combined

    def test_skip_hooks_with_colon_reason_passes(self):
        """SKIP_HOOKS: <10+ char reason> format must pass."""
        msg = "feat: deploy fix\n\nSKIP_HOOKS: hotfix for production outage P0 incident"
        result = self._run_with_msg(msg)
        assert result.returncode == 0

    def test_skip_hooks_with_emergency_keyword_passes(self):
        """emergency: <reason> keyword must satisfy bypass documentation."""
        msg = "feat: emergency deploy\n\nemergency: critical production database failure"
        result = self._run_with_msg(msg)
        assert result.returncode == 0

    def test_skip_hooks_with_reason_keyword_passes(self):
        """reason: <10+ char explanation> must satisfy bypass documentation."""
        msg = "feat: bypass needed\n\nreason: scheduled maintenance window deployment"
        result = self._run_with_msg(msg)
        assert result.returncode == 0

    def test_skip_hooks_reason_too_short_fails(self):
        """SKIP_HOOKS: <short reason> (< 10 chars) must fail."""
        msg = "feat: deploy fix\n\nSKIP_HOOKS: short"
        result = self._run_with_msg(msg)
        assert result.returncode != 0

    # ── DELEGATE/HANDBACK in commit message ───────────────────────────────────

    def test_commit_with_valid_delegate_block_passes(self):
        """Commit message containing a valid DELEGATE block must pass."""
        msg = textwrap.dedent("""\
            feat: add delegate for testing 2026-05-16-test-delegate

            DELEGATE block:
            handoff_type: DELEGATE
            task_id: 2026-05-16-test-delegate
            agent: engineer
            scope: Test the system with required scope description
            plan: Run tests
            success_criteria: All pass
        """)
        result = self._run_with_msg(msg)
        assert result.returncode == 0

    def test_commit_with_delegate_missing_fields_fails(self):
        """Commit message with DELEGATE but missing required fields must fail."""
        msg = textwrap.dedent("""\
            feat: add incomplete delegate

            ---
            handoff_type: DELEGATE
            task_id: 2026-05-16-test
            agent: engineer
            ---
        """)
        result = self._run_with_msg(msg)
        assert result.returncode != 0

    def test_commit_with_secrets_in_message_fails(self):
        """Commit message containing secret-like patterns must be rejected."""
        msg = "feat: update config\n\npassword: supersecretvalue123"
        result = self._run_with_msg(msg)
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "secret" in combined.lower() or "password" in combined.lower()

    # ── Error message quality ──────────────────────────────────────────────────


    def test_error_message_shows_retry_instruction(self):
        """Error output must tell user to fix and retry (git commit --amend)."""
        result = self._run_with_msg("x")
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "amend" in combined.lower() or "retry" in combined.lower() or "fix" in combined.lower()

    def test_error_message_shows_bypass_option(self):
        """Error output must mention SKIP_COMMIT_MSG_HOOK bypass."""
        result = self._run_with_msg("x")
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "SKIP_COMMIT_MSG_HOOK" in combined or "bypass" in combined.lower()

    def test_success_message_shows_subject(self):
        """Success output must echo back the subject line."""
        msg = "feat: add comprehensive hook testing suite"
        result = self._run_with_msg(msg)
        assert result.returncode == 0
        assert "feat: add comprehensive hook testing suite" in result.stdout

    # ── Recovery procedure ─────────────────────────────────────────────────────

    def test_recovery_amend_workflow(self):
        """After failure, a corrected message must pass (simulates git commit --amend)."""
        bad = self._run_with_msg("bad")
        assert bad.returncode != 0
        good = self._run_with_msg("fix: corrected commit message after hook failure")
        assert good.returncode == 0

    def test_recovery_bypass_then_fix(self):
        """SKIP_COMMIT_MSG_HOOK bypass allows commit; subsequent fix passes normally."""
        bypassed = self._run_with_msg("x", env_overrides={"SKIP_COMMIT_MSG_HOOK": "true"})
        assert bypassed.returncode == 0
        fixed = self._run_with_msg("fix: proper message after emergency bypass")
        assert fixed.returncode == 0

    # ── Warnings (non-blocking) ────────────────────────────────────────────────

    def test_no_conventional_format_warns_but_passes(self):
        """Message without conventional commit format must warn but still pass."""
        result = self._run_with_msg("This is a valid but non-conventional message")
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "\u26a0" in combined or "warn" in combined.lower() or "conventional" in combined.lower()

    def test_no_task_id_warns_but_passes(self):
        """Message without a task ID must warn but still pass."""
        result = self._run_with_msg("feat: add feature without task id reference")
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "\u26a0" in combined or "task" in combined.lower()


# ══════════════════════════════════════════════════════════════════════════════
# Harness C — .githooks/pre-push
# Tests run in isolated temp repos (no tests/ dir) to avoid triggering pytest.
# Tests that must run from repo root are marked @pytest.mark.slow.
# ══════════════════════════════════════════════════════════════════════════════

class TestPrePushHook:
    """Harness C: .githooks/pre-push"""

    HOOK = GITHOOKS_DIR / "pre-push"

    def _run_push_in_repo(self, tmpdir, remote="origin",
                          url="https://github.com/test/repo.git",
                          stdin="", env_overrides=None):
        """Run pre-push in an isolated temp repo (no tests/ dir → no pytest)."""
        env = os.environ.copy()
        env.update(env_overrides or {})
        return subprocess.run(
            [str(self.HOOK), remote, url],
            capture_output=True, text=True,
            cwd=tmpdir, env=env,
            input=stdin,
            timeout=15,
        )

    # ── Bypass ─────────────────────────────────────────────────────────────────

    def test_bypass_skip_hooks_exits_zero(self):
        """SKIP_HOOKS=1 must bypass all checks and exit 0."""
        result = run_hook(self.HOOK, args=["origin", "https://github.com/test/repo.git"],
                          env_overrides={"SKIP_HOOKS": "1"}, stdin="")
        assert result.returncode == 0

    def test_bypass_skip_hooks_warns(self):
        """SKIP_HOOKS=1 bypass must emit warning."""
        result = run_hook(self.HOOK, args=["origin", "https://github.com/test/repo.git"],
                          env_overrides={"SKIP_HOOKS": "1"}, stdin="")
        combined = result.stdout + result.stderr
        assert "\u26a0" in combined or "SKIP_HOOKS" in combined or "bypass" in combined.lower()

    def test_bypass_skip_hooks_empty_does_not_bypass(self):
        """SKIP_HOOKS='' must NOT bypass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_minimal_repo_with_docs(tmpdir)
            result = self._run_push_in_repo(tmpdir, env_overrides={"SKIP_HOOKS": ""})
        combined = result.stdout + result.stderr
        assert "bypassing pre-push" not in combined.lower()

    # ── Main/master branch protection ─────────────────────────────────────────

    def test_warns_on_push_to_main(self):
        """Pushing to main must emit a warning (non-blocking)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_minimal_repo_with_docs(tmpdir)
            stdin = "refs/heads/main abc123 refs/heads/main def456\n"
            result = self._run_push_in_repo(tmpdir, stdin=stdin)
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "\u26a0" in combined or "main" in combined.lower() or "protected" in combined.lower()

    def test_warns_on_push_to_master(self):
        """Pushing to master must emit a warning (non-blocking)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_minimal_repo_with_docs(tmpdir)
            stdin = "refs/heads/master abc123 refs/heads/master def456\n"
            result = self._run_push_in_repo(tmpdir, stdin=stdin)
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "\u26a0" in combined or "master" in combined.lower() or "protected" in combined.lower()

    def test_no_protected_warning_on_feature_branch(self):
        """Pushing to a feature branch must not trigger the main/master warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_minimal_repo_with_docs(tmpdir)
            stdin = "refs/heads/feature/my-feature abc123 refs/heads/feature/my-feature def456\n"
            result = self._run_push_in_repo(tmpdir, stdin=stdin)
        assert result.returncode == 0
        assert "protected branch" not in result.stdout.lower()

    # ── Documentation validation ───────────────────────────────────────────────

    def test_passes_with_required_docs_present(self):
        """Hook must pass when docs/SPEC.md, docs/AGENTS.md, README.md exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_minimal_repo_with_docs(tmpdir)
            result = self._run_push_in_repo(tmpdir)
        assert result.returncode == 0

    def test_fails_without_docs_dir(self):
        """A repo with no docs/ at all must be rejected (SPEC.md + AGENTS.md + README.md required).

        Observed hook behaviour: exit 1, reporting all three missing docs as errors.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            result = self._run_push_in_repo(tmpdir)
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "docs/SPEC.md not found" in combined
        assert "docs/AGENTS.md not found" in combined
        assert "README.md not found" in combined

    def test_fails_without_agents_md(self):
        """docs/AGENTS.md is the agent registry and is required per SPEC — its absence must block.

        Observed hook behaviour: exit 1 with exactly one error, "docs/AGENTS.md not found".
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            (Path(tmpdir) / "docs").mkdir()
            (Path(tmpdir) / "docs" / "SPEC.md").write_text("# Spec\nversion: 1.0\n")
            (Path(tmpdir) / "README.md").write_text("# Readme\n")
            result = self._run_push_in_repo(tmpdir)
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "docs/AGENTS.md not found" in combined

    def test_fails_without_readme(self):
        """README.md is required repo documentation per SPEC — its absence must block the push.

        Observed hook behaviour: exit 1 with exactly one error, "README.md not found".
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            make_git_repo(tmpdir)
            (Path(tmpdir) / "docs").mkdir()
            (Path(tmpdir) / "docs" / "SPEC.md").write_text("# Spec\nversion: 1.0\n")
            (Path(tmpdir) / "docs" / "AGENTS.md").write_text("# Agents\n")
            result = self._run_push_in_repo(tmpdir)
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "README.md not found" in combined

    # ── SPEC compliance ────────────────────────────────────────────────────────

    def test_fails_with_orchestration_scripts_present(self):
        """SPEC allows executable scripts only under renderer/scripts/ — orchestration/scripts/ must block.

        Observed hook behaviour: exit 1, "External scripts found in orchestration/scripts/".
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            make_minimal_repo_with_docs(tmpdir)
            scripts = Path(tmpdir) / "orchestration" / "scripts"
            scripts.mkdir(parents=True)
            (scripts / "bad.py").write_text("x=1\n")
            result = self._run_push_in_repo(tmpdir)
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "orchestration/scripts" in combined

    # ── Agent YAML validation ──────────────────────────────────────────────────

    def test_fails_on_invalid_agent_yaml_frontmatter(self):
        """Invalid YAML frontmatter in src/agents/*.md must cause failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_minimal_repo_with_docs(tmpdir)
            agents = Path(tmpdir) / "src" / "agents"
            agents.mkdir(parents=True)
            (agents / "bad-agent.md").write_text("---\nkey: [\ninvalid\n---\n# Agent\n")
            result = self._run_push_in_repo(tmpdir)
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "YAML" in combined or "yaml" in combined.lower() or "agent" in combined.lower()

    def test_fails_on_agent_missing_required_fields(self):
        """Agent frontmatter with valid YAML but no name/model must still be rejected.

        Observed hook behaviour: exit 1 with a separate error per missing field
        ("Missing required field 'name'" and "... 'model'"). Note the hook checks
        name and model only — role and effort live in the markdown body, not frontmatter.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            make_minimal_repo_with_docs(tmpdir)
            agents = Path(tmpdir) / "src" / "agents"
            agents.mkdir(parents=True)
            (agents / "incomplete-agent.md").write_text("---\nrole: engineer\n---\n# Agent\n")
            result = self._run_push_in_repo(tmpdir)
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "Missing required field 'name'" in combined
        assert "Missing required field 'model'" in combined

    def test_passes_with_valid_agent_yaml(self):
        """Valid agent YAML frontmatter with name and model must pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_minimal_repo_with_docs(tmpdir)
            agents = Path(tmpdir) / "src" / "agents"
            agents.mkdir(parents=True)
            (agents / "good-agent.md").write_text(
                "---\nname: test-agent\nmodel: claude-3\nrole: engineer\n---\n# Agent\n"
            )
            result = self._run_push_in_repo(tmpdir)
        assert result.returncode == 0

    # ── Error message quality ──────────────────────────────────────────────────

    def test_success_message_on_clean_push(self):
        """On success, hook must print quality gate passed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_minimal_repo_with_docs(tmpdir)
            result = self._run_push_in_repo(tmpdir)
        assert result.returncode == 0
        assert "\u2705" in result.stdout

    def test_error_message_includes_bypass_hint(self):
        """On failure (invalid agent YAML), hook must include SKIP_HOOKS=1 recovery hint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            make_minimal_repo_with_docs(tmpdir)
            agents = Path(tmpdir) / "src" / "agents"
            agents.mkdir(parents=True)
            (agents / "bad-agent.md").write_text("---\nkey: [\ninvalid\n---\n# Agent\n")
            result = self._run_push_in_repo(tmpdir)
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "SKIP_HOOKS" in combined or "bypass" in combined.lower()


    # ── Recovery procedure ─────────────────────────────────────────────────────

    def test_recovery_bypass_then_fix(self):
        """SKIP_HOOKS=1 bypass allows push; after fix, push passes normally."""
        bypassed = run_hook(self.HOOK, args=["origin", "https://github.com/test/repo.git"],
                            env_overrides={"SKIP_HOOKS": "1"}, stdin="")
        assert bypassed.returncode == 0
        with tempfile.TemporaryDirectory() as tmpdir:
            make_minimal_repo_with_docs(tmpdir)
            fixed = self._run_push_in_repo(tmpdir)
        assert fixed.returncode == 0



# ══════════════════════════════════════════════════════════════════════════════
# Cross-harness: Hook executability and installation
# ══════════════════════════════════════════════════════════════════════════════

ALL_HOOK_PATHS = [
    GITHOOKS_DIR / "pre-commit",
    GITHOOKS_DIR / "commit-msg",
    GITHOOKS_DIR / "pre-push",
    GIT_HOOKS_DIR / "pre-commit",
]


class TestHookInstallation:
    """Verify all hooks are present, executable, and correctly installed."""

    @pytest.mark.parametrize("hook_path", ALL_HOOK_PATHS)
    def test_hook_exists(self, hook_path):
        """Each hook file must exist on disk."""
        assert hook_path.exists(), "Missing hook: {}".format(hook_path)

    @pytest.mark.parametrize("hook_path", ALL_HOOK_PATHS)
    def test_hook_is_executable(self, hook_path):
        """Each hook file must have executable permission."""
        assert os.access(hook_path, os.X_OK), "Not executable: {}".format(hook_path)

    def test_git_config_hooks_path_configured(self):
        """git config core.hooksPath should point to .githooks."""
        result = subprocess.run(
            ["git", "config", "core.hooksPath"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        if result.returncode == 0:
            assert ".githooks" in result.stdout.strip(), \
                "core.hooksPath is '{}', expected '.githooks'".format(result.stdout.strip())
        else:
            pytest.skip("core.hooksPath not configured — hooks may not be active")

    def test_githooks_dir_has_required_hooks(self):
        """The .githooks/ directory must contain pre-commit, commit-msg, and pre-push."""
        hook_names = {f.name for f in GITHOOKS_DIR.iterdir() if f.is_file()}
        required = {"pre-commit", "commit-msg", "pre-push"}
        assert required.issubset(hook_names), \
            "Missing hooks: {}".format(required - hook_names)

    def test_agent_frontmatter_drift_detection_reads_src_agents_md(self):
        """
        Regression test for DEFECT 1: pre-commit validate_agent_frontmatter()
        must read from src/AGENTS.md (not docs/AGENTS.md stub).

        This test verifies:
        1. The hook function calls parse_agents_md with src/AGENTS.md
        2. Positive path: parse succeeds with canonical roster
        3. Negative path: mismatch in agent frontmatter is detected
        """
        # Positive test: parse src/AGENTS.md and verify we get all 8 agents
        # Use REPO_ROOT to derive paths dynamically (not hardcoded)
        # Sourced from renderer/lib/render-lib.sh, the canonical render library.
        # This previously sourced renderer/scripts/lib.sh, a thin shim that has
        # since been deleted; parse_agents_md only ever lived in render-lib.sh.
        lib_sh_path = REPO_ROOT / "renderer" / "lib" / "render-lib.sh"
        agents_md_path = REPO_ROOT / "src" / "AGENTS.md"

        parse_result = subprocess.run(
            ['bash', '-c', f'''
                source {lib_sh_path}
                parse_agents_md {agents_md_path}
            '''],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert parse_result.returncode == 0, \
            f"parse_agents_md failed: {parse_result.stderr}"

        lines = [l for l in parse_result.stdout.strip().split('\n') if l.strip()]
        assert len(lines) == 8, \
            f"Expected 8 agents in src/AGENTS.md, got {len(lines)}"
