"""
tests/test_model_pin_hooks.py - hooks and CI around config/models.yaml.

The single reference table (config/models.yaml) is the only gate: editing a role's pin needs
no trailer or approval in .githooks/commit-msg, .githooks/pre-push or CI. A rewrite of
pin_history only WARNS. The pre-commit hook still validates staged agents and the registry
through scripts/models.py instead of a version allowlist (SPEC I6).

No model version is hard-coded here: roles and models come from the real registry.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import models as models_cli  # noqa: E402

COMMIT_MSG = REPO_ROOT / ".githooks" / "commit-msg"
PRE_COMMIT = REPO_ROOT / ".githooks" / "pre-commit"

REGISTRY = models_cli.load_registry(REPO_ROOT)
ROLE = "engineer"
ROLE_PIN = REGISTRY["roles"][ROLE]["model"]
# Any other non-retired registry model: a valid alternative pin (shape is irrelevant to
# the hooks, which only compare roles.<role>.model before and after).
ALT_PIN = next(mid for mid, m in REGISTRY["models"].items()
               if mid != ROLE_PIN and m["status"] != "retired")


def git(cwd, *args, check=True, env=None):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          check=check, env={**os.environ, **(env or {})})


def make_repo(tmp_path, commit_registry=True):
    """Scratch repo whose config/models.yaml is a copy of the real registry."""
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "T")
    git(tmp_path, "config", "core.hooksPath", "/nonexistent")  # run hooks by hand only
    reg = tmp_path / "config" / "models.yaml"
    reg.parent.mkdir(parents=True)
    shutil.copy(REPO_ROOT / "config" / "models.yaml", reg)
    if commit_registry:
        git(tmp_path, "add", "config/models.yaml")
        git(tmp_path, "commit", "-q", "-m", "chore: seed registry for hook test")
    return tmp_path


def edit_registry(repo, mutate):
    path = repo / "config" / "models.yaml"
    text = path.read_text()
    new = mutate(text)
    assert new != text, "mutation did not change the registry"
    path.write_text(new)
    git(repo, "add", "config/models.yaml")


def change_pin(text):
    """Re-pin ROLE to ALT_PIN by editing only that role's `model:` line."""
    head, _, rest = text.partition(f"\n  {ROLE}:\n    model: {ROLE_PIN}\n")
    assert rest, "engineer role block not found"
    return head + f"\n  {ROLE}:\n    model: {ALT_PIN}\n" + rest


def change_fallback_only(text):
    """Edit only ROLE's fallback list (never its pin)."""
    cfg = REGISTRY["roles"][ROLE]
    old = f"    model: {ROLE_PIN}\n    effort: {cfg['effort']}\n    fallback: [{', '.join(cfg['fallback'])}]"
    assert old in text, "engineer role block not found in the expected inline form"
    alt = next(m for m in REGISTRY["models"] if m != ROLE_PIN and m not in cfg["fallback"])
    return text.replace(old, old.rsplit("fallback:", 1)[0] + f"fallback: [{alt}]", 1)


def change_effort_only(text):
    return text.replace("schema_version: 1", "schema_version: 1\n# a comment-only edit", 1)


def run_commit_msg(repo, message, **env):
    msg = repo / "MSG"
    msg.write_text(message)
    return subprocess.run([str(COMMIT_MSG), str(msg)], cwd=repo, capture_output=True, text=True,
                          env={**os.environ, **env}, timeout=30)


def out(result):
    return result.stdout + result.stderr


SUBJECT = "chore: change a role pin for testing the relaxed gate"
# Spelled in two parts: the old trailer name must not appear as a literal anywhere.
TRAILER_NAME = "Model-Pin-" + "Approved-By"


def rewrite_history(text):
    """Edit an EXISTING pin_history entry (an audit-record rewrite)."""
    new = text.replace("baseline: seeded from tree", "baseline: forged tree", 1)
    assert new != text
    return new


def append_history(text):
    return text.rstrip("\n") + (
        "\n  - {date: 2026-10-03, role: engineer, from: x, to: y, approval: \"test append\"}\n")


def pin_change_with_history(text):
    return append_history(change_pin(text))


class TestCommitMsgPinChangesAreFree:
    """A pin change needs no trailer and no approval; only a pin_history REWRITE warns."""

    def test_pin_change_without_trailer_passes(self, tmp_path):
        repo = make_repo(tmp_path)
        edit_registry(repo, change_pin)
        r = run_commit_msg(repo, SUBJECT + "\n")
        assert r.returncode == 0, out(r)
        assert TRAILER_NAME not in out(r)

    def test_pin_change_with_history_entry_passes_silently(self, tmp_path):
        repo = make_repo(tmp_path)
        edit_registry(repo, pin_change_with_history)
        r = run_commit_msg(repo, SUBJECT + "\n")
        assert r.returncode == 0, out(r)
        assert "pin_history" not in out(r)

    def test_a_trailer_is_simply_ignored(self, tmp_path):
        repo = make_repo(tmp_path)
        edit_registry(repo, change_pin)
        r = run_commit_msg(repo, SUBJECT + f"\n\n{TRAILER_NAME}: Jane Doe\n")
        assert r.returncode == 0, out(r)
        assert "approved" not in out(r).lower()

    def test_non_pin_registry_edit_passes(self, tmp_path):
        repo = make_repo(tmp_path)
        edit_registry(repo, change_effort_only)
        r = run_commit_msg(repo, "chore: comment-only registry edit\n")
        assert r.returncode == 0, out(r)

    def test_fallback_only_change_passes(self, tmp_path):
        repo = make_repo(tmp_path)
        edit_registry(repo, change_fallback_only)
        r = run_commit_msg(repo, "chore: change a fallback list only\n")
        assert r.returncode == 0, out(r)
        assert TRAILER_NAME not in out(r)

    def test_history_rewrite_warns_but_never_fails(self, tmp_path):
        repo = make_repo(tmp_path)
        edit_registry(repo, rewrite_history)
        r = run_commit_msg(repo, "chore: rewrite history entry\n")
        assert r.returncode == 0, out(r)
        assert "pin_history" in out(r) and "append-only" in out(r)

    def test_history_rewrite_warning_is_not_waived_or_escalated_by_skip_hooks(self, tmp_path):
        """SKIP_HOOKS is irrelevant: no pin text, and without a reason the usual SKIP rules apply."""
        repo = make_repo(tmp_path)
        edit_registry(repo, change_pin)
        r = run_commit_msg(repo, SUBJECT + "\n\nSKIP_HOOKS: incident INC-1234 outage rollback\n", SKIP_HOOKS="1")
        assert r.returncode == 0, out(r)
        assert "Model Pin" not in out(r) and "bypassed" not in out(r)

    def test_missing_pyyaml_warns_but_does_not_fail(self, tmp_path):
        repo = make_repo(tmp_path)
        edit_registry(repo, change_pin)
        block = tmp_path.parent / (tmp_path.name + "-noyaml")
        block.mkdir()
        (block / "yaml.py").write_text("raise ImportError('PyYAML blocked for test')\n")
        r = run_commit_msg(repo, SUBJECT + "\n", PYTHONPATH=str(block))
        assert r.returncode == 0, out(r)
        assert "PyYAML" in out(r)

    def test_hook_copy_outside_repo_tree_still_finds_models_py(self, tmp_path):
        """CI copies hooks into .git/hooks/: there ../scripts does not exist."""
        repo = make_repo(tmp_path)
        edit_registry(repo, rewrite_history)
        copy = repo / ".git" / "hooks" / "commit-msg"
        shutil.copy(COMMIT_MSG, copy)
        shutil.copytree(REPO_ROOT / "scripts", repo / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        msg = repo / "MSG"
        msg.write_text("chore: rewrite history entry\n")
        r = subprocess.run([str(copy), str(msg)], cwd=repo, capture_output=True, text=True, timeout=30)
        assert r.returncode == 0 and "pin_history" in out(r), out(r)

    def test_commit_not_touching_registry_passes(self, tmp_path):
        repo = make_repo(tmp_path)
        (repo / "x.txt").write_text("x")
        git(repo, "add", "x.txt")
        r = run_commit_msg(repo, "chore: unrelated change here\n")
        assert r.returncode == 0, out(r)

    def test_registry_first_added_passes(self, tmp_path):
        repo = make_repo(tmp_path, commit_registry=False)
        git(repo, "add", "config/models.yaml")
        r = run_commit_msg(repo, "chore: add the model registry file\n")
        assert r.returncode == 0, out(r)
        assert "pin_history" not in out(r)

    def test_skip_hooks_bypasses_the_advisory_audit(self, tmp_path):
        """SKIP_HOOKS=1 is the single bypass; it needs a documented reason and skips the audit."""
        repo = make_repo(tmp_path)
        edit_registry(repo, rewrite_history)
        r = run_commit_msg(repo, SUBJECT + "\n\nSKIP_HOOKS: incident INC-1234 outage rollback\n",
                           SKIP_HOOKS="1")
        assert r.returncode == 0 and "pin_history" not in out(r), out(r)

    def test_old_skip_commit_msg_hook_variable_is_gone(self, tmp_path):
        repo = make_repo(tmp_path)
        edit_registry(repo, rewrite_history)
        r = run_commit_msg(repo, SUBJECT + "\n", SKIP_COMMIT_MSG_HOOK="true", SKIP_HOOKS="")
        assert "pin_history" in out(r), out(r)
        assert "SKIP_COMMIT_MSG_HOOK" not in COMMIT_MSG.read_text()

    def test_existing_rules_unchanged_for_registry_commits(self, tmp_path):
        """Other commit-message rules still apply to registry commits."""
        repo = make_repo(tmp_path)
        edit_registry(repo, change_pin)
        r = run_commit_msg(repo, "chore: " + "x" * 80 + "\n")
        assert r.returncode == 1, out(r)
        assert "too long" in out(r)

    def test_real_repo_pin_change_flow_end_to_end(self, tmp_path):
        """The scratch registry is valid YAML and the pin really changed."""
        repo = make_repo(tmp_path)
        edit_registry(repo, change_pin)
        data = yaml.safe_load((repo / "config" / "models.yaml").read_text())
        assert data["roles"][ROLE]["model"] == ALT_PIN

    def test_hook_no_longer_mentions_the_trailer(self):
        assert TRAILER_NAME not in COMMIT_MSG.read_text()


class TestCommitMsgAmendPath:
    """`git commit --amend` replaces HEAD, so the hook still compares the index with HEAD^
    (a rewrite of pin_history introduced by the amended commit is still noticed). Real
    `git commit --amend` runs so git itself invokes the hook."""

    PIN_MSG = SUBJECT + "\n"

    @staticmethod
    def hooked_repo(tmp_path, commit_registry=True):
        (tmp_path / "repo").mkdir()
        repo = make_repo(tmp_path / "repo", commit_registry=commit_registry)
        hooks = tmp_path / "hooks"
        hooks.mkdir()
        shutil.copy(COMMIT_MSG, hooks / "commit-msg")
        # The hook resolves ../scripts/models.py next to itself.
        (tmp_path / "scripts").symlink_to(REPO_ROOT / "scripts")
        return repo, hooks

    def commit_with(self, repo, mutate, message=None):
        edit_registry(repo, mutate)
        git(repo, "commit", "-q", "-m", message or self.PIN_MSG)  # hooks still disabled here

    @staticmethod
    def amend(repo, hooks, message):
        git(repo, "config", "core.hooksPath", str(hooks))
        return git(repo, "commit", "--amend", "-q", "-m", message, check=False)

    def test_amend_of_pin_commit_without_trailer_passes(self, tmp_path):
        repo, hooks = self.hooked_repo(tmp_path)
        self.commit_with(repo, change_pin)
        r = self.amend(repo, hooks, SUBJECT + " (reworded)")
        assert r.returncode == 0, out(r)
        assert "reworded" in git(repo, "log", "-1", "--format=%s").stdout

    def test_amend_of_history_rewriting_commit_still_warns_via_head_parent(self, tmp_path):
        repo, hooks = self.hooked_repo(tmp_path)
        self.commit_with(repo, rewrite_history)
        r = self.amend(repo, hooks, "chore: rewrite history reworded")
        assert r.returncode == 0, out(r)
        assert "pin_history" in out(r), "amend must compare against HEAD^, not HEAD"

    def test_amend_of_non_registry_commit_is_silent(self, tmp_path):
        repo, hooks = self.hooked_repo(tmp_path)
        self.commit_with(repo, rewrite_history)
        (repo / "x.txt").write_text("x")
        git(repo, "add", "x.txt")
        git(repo, "commit", "-q", "-m", "chore: unrelated change here")
        r = self.amend(repo, hooks, "chore: unrelated change reworded")
        assert r.returncode == 0 and "pin_history" not in out(r), out(r)

    def test_new_commit_after_history_rewrite_is_silent(self, tmp_path):
        """Only an AMEND compares against HEAD^."""
        repo, hooks = self.hooked_repo(tmp_path)
        self.commit_with(repo, rewrite_history)
        (repo / "x.txt").write_text("x")
        git(repo, "add", "x.txt")
        git(repo, "config", "core.hooksPath", str(hooks))
        r = git(repo, "commit", "-q", "-m", "chore: unrelated follow-up", check=False)
        assert r.returncode == 0 and "pin_history" not in out(r), out(r)

    def test_amend_that_adds_a_pin_change_to_a_plain_commit_passes(self, tmp_path):
        repo, hooks = self.hooked_repo(tmp_path)
        (repo / "x.txt").write_text("x")
        git(repo, "add", "x.txt")
        git(repo, "commit", "-q", "-m", "chore: unrelated change here")
        edit_registry(repo, change_pin)
        r = self.amend(repo, hooks, "chore: unrelated change here")
        assert r.returncode == 0, out(r)

    def test_amend_of_registry_introducing_root_commit_passes(self, tmp_path):
        repo, hooks = self.hooked_repo(tmp_path, commit_registry=False)
        git(repo, "add", "config/models.yaml")
        git(repo, "commit", "-q", "-m", "chore: add the model registry file")
        r = self.amend(repo, hooks, "chore: add the model registry file")
        assert r.returncode == 0 and "pin_history" not in out(r), out(r)


class TestCommitMsgRebaseAndCherryPick:
    """git rebase reword/squash/fixup replace HEAD (the hook compares against HEAD^ using
    GIT_REFLOG_ACTION); other rebase/cherry-pick commits sit on HEAD. None of them can fail
    on a pin change any more; a history rewrite warns."""

    PIN_MSG = SUBJECT + "\n"
    hooked_repo = staticmethod(TestCommitMsgAmendPath.hooked_repo)

    @staticmethod
    def editor(tmp_path, message):
        """A GIT_EDITOR that replaces the whole message with *message*."""
        (tmp_path / "newmsg").write_text(message)
        script = tmp_path / "editor.sh"
        script.write_text(f'#!/bin/sh\ncat "{tmp_path / "newmsg"}" > "$1"\n')
        script.chmod(0o755)
        return str(script)

    def commit_then_plain(self, tmp_path, mutate=change_pin):
        repo, hooks = self.hooked_repo(tmp_path)
        edit_registry(repo, mutate)
        git(repo, "commit", "-q", "-m", self.PIN_MSG)  # hooks still disabled here
        (repo / "x.txt").write_text("x")
        git(repo, "add", "x.txt")
        git(repo, "commit", "-q", "-m", "chore: unrelated change here")
        git(repo, "config", "core.hooksPath", str(hooks))
        return repo

    @staticmethod
    def rebase(repo, tmp_path, todo_edit, message):
        env = {"GIT_SEQUENCE_EDITOR": todo_edit, "GIT_EDITOR": TestCommitMsgRebaseAndCherryPick.editor(tmp_path, message)}
        return git(repo, "rebase", "-i", "HEAD~2", check=False, env=env)

    def test_rebase_reword_of_pin_commit_without_trailer_passes(self, tmp_path):
        repo = self.commit_then_plain(tmp_path)
        r = self.rebase(repo, tmp_path, "sed -i.bak '1s/^pick/reword/'", SUBJECT + " (reworded)\n")
        assert r.returncode == 0, out(r)
        assert "reworded" in git(repo, "log", "-2", "--format=%s").stdout

    def test_rebase_reword_of_history_rewrite_commit_warns_but_passes(self, tmp_path):
        repo = self.commit_then_plain(tmp_path, rewrite_history)
        r = self.rebase(repo, tmp_path, "sed -i.bak '1s/^pick/reword/'", "chore: reworded rewrite\n")
        assert r.returncode == 0, out(r)
        assert "pin_history" in out(r)

    @pytest.mark.parametrize("action", ["rebase (reword)", "rebase -i (reword)", "rebase (squash)",
                                        "rebase (fixup)", "rebase -i (fixup)", "rebase (fixup -C)"])
    def test_amend_like_rebase_actions_compare_against_head_parent(self, tmp_path, action):
        """Env-only (no --amend in the parent process): GIT_REFLOG_ACTION alone must select HEAD^."""
        repo = self.commit_then_plain(tmp_path, rewrite_history)
        git(repo, "reset", "-q", "--hard", "HEAD~1")  # HEAD is the rewriting commit, index == HEAD
        r = run_commit_msg(repo, "chore: reworded rewrite\n", GIT_REFLOG_ACTION=action)
        assert r.returncode == 0 and "pin_history" in out(r), out(r)

    @pytest.mark.parametrize("action", ["rebase (continue)", "rebase (pick)", "cherry-pick", "rebase (start)"])
    def test_non_amend_actions_still_compare_against_head(self, tmp_path, action):
        """A new commit ON TOP of a rewriting commit has no rewrite of its own."""
        repo = self.commit_then_plain(tmp_path, rewrite_history)
        git(repo, "reset", "-q", "--hard", "HEAD~1")
        (repo / "y.txt").write_text("y")
        git(repo, "add", "y.txt")
        r = run_commit_msg(repo, "chore: another unrelated change\n", GIT_REFLOG_ACTION=action)
        assert r.returncode == 0 and "pin_history" not in out(r), out(r)

    def cherry_source(self, tmp_path, message):
        repo, hooks = self.hooked_repo(tmp_path)
        main = git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        git(repo, "checkout", "-q", "-b", "side")
        edit_registry(repo, change_pin)
        git(repo, "commit", "-q", "-m", message)  # hooks still disabled here
        sha = git(repo, "rev-parse", "HEAD").stdout.strip()
        git(repo, "checkout", "-q", main)
        git(repo, "config", "core.hooksPath", str(hooks))
        return repo, sha

    def test_cherry_pick_reworded_pin_commit_passes(self, tmp_path):
        repo, sha = self.cherry_source(tmp_path, self.PIN_MSG)
        env = {"GIT_EDITOR": self.editor(tmp_path, SUBJECT + " (picked)\n")}
        r = git(repo, "cherry-pick", "-e", sha, check=False, env=env)
        assert r.returncode == 0, out(r)

    def test_squash_of_a_pin_commit_passes_and_the_scanner_is_clean(self, tmp_path):
        repo = self.commit_then_plain(tmp_path)
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD~2")
        r = self.rebase(repo, tmp_path, "sed -i.bak '2s/^pick/squash/'", SUBJECT + "\n")
        assert r.returncode == 0, out(r)
        scan = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "check_pin_history.py"), "--strict"],
                              cwd=repo, capture_output=True, text=True)
        assert scan.returncode == 0, out(scan)

    def test_header_documents_the_advisory_behaviour(self):
        header = COMMIT_MSG.read_text().split("set -uo pipefail")[0]
        assert "needs no" in header and "pin_history" in header and "WARNS" in header
        assert "check_pin_history" in header


class TestCommitMsgPrintfNotEcho:
    """S4: messages are printed verbatim; `echo -e` expanded backslash escapes in
    user-controlled text (a bypass reason) and mangled the output."""

    def test_backslash_sequences_in_user_text_are_printed_literally(self, tmp_path):
        repo = make_repo(tmp_path)
        r = run_commit_msg(repo, "chore: document a bypass reason here\n\nSKIP_HOOKS: a\\nb\\tc\n",
                           SKIP_HOOKS="1")
        assert r.returncode == 1, out(r)
        assert "('a\\nb\\tc')" in out(r)

    def test_no_echo_dash_e_left_in_the_hook(self):
        assert "echo -e" not in COMMIT_MSG.read_text()


# ── CI: advisory pin_history audit over origin/main..HEAD + workflow permissions ───────

CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _ci():
    return yaml.safe_load(CI_YML.read_text())


def _scan_step_run():
    steps = _ci()["jobs"]["quality-gate"]["steps"]
    named = [s for s in steps if s.get("name") == "Model Pin History Audit (advisory)"]
    assert len(named) == 1, "CI must have exactly one 'Model Pin History Audit (advisory)' step"
    return named[0]["run"]


class TestCiPinHistoryAudit:
    """The scan logic lives in scripts/check_pin_history.py (tests/test_check_pin_history.py);
    the workflow step must only invoke it."""

    def test_step_just_invokes_the_script(self):
        run = _scan_step_run()
        assert "scripts/check_pin_history.py" in run
        assert "python3 -" not in run and "<<" not in run, "no inline python in the workflow step"
        # Only a small shell preamble that picks the scan base (the scan itself is the script):
        # a push scans the pushed range, everything else falls back to origin/main;
        # plus the exit-2 (environment problem) -> ::warning:: handling.
        assert len([ln for ln in run.splitlines() if ln.strip()]) <= 18
        assert "python3 scripts/check_pin_history.py" in run

    def test_untrusted_text_never_reaches_workflow_expressions(self):
        assert "${{" not in _scan_step_run()

    def test_step_is_advisory_not_strict(self):
        assert "--strict" not in _scan_step_run()

    def test_scanner_script_exists_and_is_executable_python(self):
        script = REPO_ROOT / "scripts" / "check_pin_history.py"
        assert script.is_file()
        assert script.read_text().startswith("#!/usr/bin/env python3")


class TestCiWorkflowPermissions:
    def test_workflow_parses_and_top_level_permissions_are_read_only(self):
        wf = _ci()
        assert wf["permissions"] == {"contents": "read"}

    def test_every_write_job_declares_its_own_permissions(self):
        wf = _ci()
        for name, job in wf["jobs"].items():
            if name == "auto-tag":
                assert job["permissions"] == {"contents": "write"}
            else:
                assert "write" not in str(job.get("permissions", "")), name

    def test_quality_gate_checks_out_full_history_for_the_audit(self):
        steps = _ci()["jobs"]["quality-gate"]["steps"]
        checkout = next(s for s in steps if str(s.get("uses", "")).startswith("actions/checkout"))
        assert checkout["with"]["fetch-depth"] == 0


# ── pre-push: local backstop scan of the commits being pushed ─────────────────

PRE_PUSH = REPO_ROOT / ".githooks" / "pre-push"
ZERO_SHA = "0" * 40


class TestPrePushPrintfNotEcho:
    """pre-push printed user-influenced text (file names, scanner output) through `echo -e`,
    which expands backslash escapes; colour codes now go through printf %b only."""

    def test_backslash_sequences_in_a_file_name_are_printed_literally(self, tmp_path):
        make_repo(tmp_path)
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "SPEC.md").write_text("# Spec\nversion: 1.0\n")
        (tmp_path / "docs" / "AGENTS.md").write_text("# Agents\n")
        (tmp_path / "README.md").write_text("# Readme\n")
        agents = tmp_path / "src" / "agents"
        agents.mkdir(parents=True)
        (agents / "x\\ty\\nz.md").write_text("---\nname: [unclosed\nmodel: m\n---\nbody\n")
        r = subprocess.run([str(PRE_PUSH), "origin", "x"], cwd=tmp_path, input="", capture_output=True,
                           text=True, timeout=30)
        assert r.returncode == 1, out(r)
        assert "x\\ty\\nz.md" in out(r)
        assert "\t" not in out(r).split("Invalid YAML frontmatter in agent:")[1].split("\n")[0]

    def test_no_echo_dash_e_left_in_any_githooks_file(self):
        offenders = []
        for path in sorted((REPO_ROOT / ".githooks").iterdir()):
            if path.is_file() and path.suffix != ".md":
                for n, line in enumerate(path.read_text().splitlines(), 1):
                    if re.search(r"\becho\s+-[A-Za-z]*e", line) and not line.lstrip().startswith("#"):
                        offenders.append(f"{path.name}:{n}: {line.strip()}")
        assert not offenders, offenders


class TestPrePushPinHistoryAudit:
    """pre-push runs scripts/check_pin_history.py over the commits being pushed (ref lines
    on stdin, githooks(5)) as an ADVISORY audit: pin changes push freely, a pin_history
    rewrite or an unusable scanner only warns. Real bare remote; git itself invokes the
    hook for the push tests."""

    @staticmethod
    def world(tmp_path):
        remote = tmp_path / "remote.git"
        remote.mkdir()
        git(remote, "init", "-q", "--bare")
        work = tmp_path / "work"
        work.mkdir()
        make_repo(work)
        for rel, text in {"docs/SPEC.md": "# Spec\nversion: 1.0\n", "docs/AGENTS.md": "# Agents\n",
                          "README.md": "# Readme\n"}.items():
            (work / rel).parent.mkdir(exist_ok=True)
            (work / rel).write_text(text)
        git(work, "add", "docs", "README.md")
        git(work, "commit", "-q", "-m", "chore: docs for the pre-push fixture")
        git(work, "branch", "-M", "main")
        git(work, "remote", "add", "origin", str(remote))
        git(work, "push", "-q", "origin", "main")  # hooks are still disabled here
        # The scanner and its registry loader, as the hook finds them next to the repo root.
        (work / "scripts").mkdir()
        for name in ("check_pin_history.py", "models.py"):
            shutil.copy(REPO_ROOT / "scripts" / name, work / "scripts" / name)
        hooks = tmp_path / "hooks"
        hooks.mkdir()
        shutil.copy(PRE_PUSH, hooks / "pre-push")
        git(work, "config", "core.hooksPath", str(hooks))
        git(work, "checkout", "-q", "-b", "feat")
        return work, remote

    @staticmethod
    def registry_commit(work, message, mutate=change_pin):
        edit_registry(work, mutate)
        git(work, "commit", "-q", "--no-verify", "-m", message)

    @staticmethod
    def push(work, *args, **env):
        return git(work, "push", *args, "origin", "feat", check=False, env=env)

    @staticmethod
    def remote_has(remote, branch="feat"):
        return git(remote, "rev-parse", "--verify", "-q", f"refs/heads/{branch}", check=False).returncode == 0

    @staticmethod
    def run_hook(work, stdin, **env):
        return subprocess.run([str(work.parent / "hooks" / "pre-push"), "origin", "x"], cwd=work, input=stdin, capture_output=True,
                              text=True, timeout=60, env={**os.environ, **env})

    def test_pin_commit_without_trailer_pushes(self, tmp_path):
        work, remote = self.world(tmp_path)
        self.registry_commit(work, SUBJECT)
        r = self.push(work)
        assert r.returncode == 0, out(r)
        assert self.remote_has(remote)
        assert TRAILER_NAME not in out(r)

    def test_pin_commit_with_history_entry_pushes_without_warning(self, tmp_path):
        work, remote = self.world(tmp_path)
        self.registry_commit(work, SUBJECT, pin_change_with_history)
        r = self.push(work)
        assert r.returncode == 0, out(r)
        assert "Pin history audit: refs/heads/feat" in out(r)
        assert self.remote_has(remote)

    def test_history_rewrite_push_warns_but_succeeds(self, tmp_path):
        work, remote = self.world(tmp_path)
        self.registry_commit(work, "chore: rewrite history", rewrite_history)
        r = self.push(work)
        assert r.returncode == 0, out(r)
        assert "Pin history audit for refs/heads/feat" in out(r) and "rewrites pin_history" in out(r)
        assert self.remote_has(remote)

    def test_later_pin_commit_on_an_existing_remote_branch_pushes(self, tmp_path):
        work, remote = self.world(tmp_path)
        (work / "x.txt").write_text("x")
        git(work, "add", "x.txt")
        git(work, "commit", "-q", "--no-verify", "-m", "chore: unrelated change")
        assert self.push(work).returncode == 0
        self.registry_commit(work, SUBJECT)
        r = self.push(work)  # range remote_sha..local_sha
        assert r.returncode == 0, out(r)

    def test_force_push_after_amend_pushes(self, tmp_path):
        work, remote = self.world(tmp_path)
        self.registry_commit(work, SUBJECT)
        assert self.push(work).returncode == 0
        git(work, "commit", "--amend", "--no-verify", "-q", "-m", SUBJECT + " (amended)")
        assert self.push(work, "--force").returncode == 0

    def test_evil_merge_push_pushes(self, tmp_path):
        work, remote = self.world(tmp_path)
        git(work, "checkout", "-q", "-b", "side", "main")
        (work / "side.txt").write_text("s")
        git(work, "add", "side.txt")
        git(work, "commit", "-q", "--no-verify", "-m", "chore: side change")
        git(work, "checkout", "-q", "feat")
        (work / "f.txt").write_text("f")
        git(work, "add", "f.txt")
        git(work, "commit", "-q", "--no-verify", "-m", "chore: feat change")
        git(work, "merge", "--no-ff", "--no-commit", "side")
        edit_registry(work, change_pin)
        git(work, "commit", "-q", "--no-verify", "-m", "merge: side")
        r = self.push(work)
        assert r.returncode == 0, out(r)

    def test_unrelated_push_passes_and_deleting_a_branch_is_not_scanned(self, tmp_path):
        work, remote = self.world(tmp_path)
        (work / "x.txt").write_text("x")
        git(work, "add", "x.txt")
        git(work, "commit", "-q", "--no-verify", "-m", "chore: unrelated change")
        assert self.push(work).returncode == 0
        r = git(work, "push", "origin", ":feat", check=False)
        assert r.returncode == 0, out(r)
        assert not self.remote_has(remote)

    def test_unknown_remote_sha_falls_back_to_origin_main(self, tmp_path):
        """A force-push over a remote tip this clone never fetched: range is origin/main..local."""
        work, _ = self.world(tmp_path)
        self.registry_commit(work, "chore: rewrite history", rewrite_history)
        sha = git(work, "rev-parse", "HEAD").stdout.strip()
        r = self.run_hook(work, f"refs/heads/feat {sha} refs/heads/feat {'a' * 40}\n")
        assert r.returncode == 0 and "rewrites pin_history" in out(r), out(r)

    def test_new_remote_ref_audits_origin_main_to_local_sha(self, tmp_path):
        work, _ = self.world(tmp_path)
        self.registry_commit(work, "chore: rewrite history", rewrite_history)
        sha = git(work, "rev-parse", "HEAD").stdout.strip()
        r = self.run_hook(work, f"refs/heads/feat {sha} refs/heads/feat {ZERO_SHA}\n")
        assert r.returncode == 0 and "rewrites pin_history" in out(r), out(r)

    def test_missing_pyyaml_warns_but_does_not_fail(self, tmp_path):
        work, _ = self.world(tmp_path)
        self.registry_commit(work, SUBJECT)
        sha = git(work, "rev-parse", "HEAD").stdout.strip()
        shim = tmp_path / "shim"
        shim.mkdir()
        (shim / "yaml.py").write_text("raise ImportError('no yaml here')\n")
        r = self.run_hook(work, f"refs/heads/feat {sha} refs/heads/feat {ZERO_SHA}\n", PYTHONPATH=str(shim))
        assert r.returncode == 0, out(r)
        assert "PyYAML" in out(r) and "could not run" in out(r)

    def test_missing_scanner_script_warns_but_does_not_fail(self, tmp_path):
        work, _ = self.world(tmp_path)
        self.registry_commit(work, SUBJECT)
        (work / "scripts" / "check_pin_history.py").unlink()
        sha = git(work, "rev-parse", "HEAD").stdout.strip()
        r = self.run_hook(work, f"refs/heads/feat {sha} refs/heads/feat {ZERO_SHA}\n")
        assert r.returncode == 0 and "check_pin_history" in out(r), out(r)

    def test_skip_hooks_is_irrelevant_to_a_pin_change_push(self, tmp_path):
        """A pin change pushes with or without SKIP_HOOKS=1; nothing about it needs a bypass."""
        work, remote = self.world(tmp_path)
        self.registry_commit(work, SUBJECT)
        assert self.push(work).returncode == 0
        git(work, "push", "-q", "origin", ":feat")
        r = self.push(work, SKIP_HOOKS="1")
        assert r.returncode == 0, out(r)
        assert self.remote_has(remote)
        scan = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "check_pin_history.py"), "--strict"],
                              cwd=work, capture_output=True, text=True)
        assert scan.returncode == 0, out(scan)

    def test_hook_header_documents_the_advisory_audit(self):
        header = PRE_PUSH.read_text().split("set -euo pipefail")[0]
        assert "check_pin_history" in header and "advisory" in header.lower()
        assert TRAILER_NAME not in header and "never fails the push" in header


# ── pre-commit: registry-driven model checks (no version allowlist) ───────────

def make_full_registry_repo(tmp_path):
    """Scratch repo holding every file `models.py check` reads, in a synced state."""
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "T")
    for rel in ("config/models.yaml", "config/FRAMEWORK-MANIFEST.yaml", "src/AGENTS.md",
                ".githooks/LOCKED_MODELS.sh", ".agents_verification_sha", "docs/MODELS.md"):
        if not (REPO_ROOT / rel).exists():  # docs/MODELS.md lands with the generator
            continue
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / rel, dest)
    shutil.copytree(REPO_ROOT / "src" / "agents", tmp_path / "src" / "agents")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "chore: seed scratch repo for hooks")
    return tmp_path


def run_pre_commit(repo, **env):
    return subprocess.run([str(PRE_COMMIT)], cwd=repo, capture_output=True, text=True,
                          env={**os.environ, **env}, timeout=60)


def set_agent_model(repo, role, model):
    path = repo / "src" / "agents" / f"{role}-agent.md"
    # First line-anchored `model:` (frontmatter); a comment above it also contains "model:".
    path.write_text(re.sub(r"(?m)^model: .*$", f"model: {model}", path.read_text(), count=1))
    git(repo, "add", str(path.relative_to(repo)))


class TestPreCommitRegistryEnforcement:
    def test_synced_tree_has_no_model_violation(self, tmp_path):
        repo = make_full_registry_repo(tmp_path)
        git(repo, "add", "-A")
        (repo / "src" / "agents" / f"{ROLE}-agent.md").touch()
        r = run_pre_commit(repo)
        assert "model registry violation" not in out(r), out(r)

    def test_unknown_source_model_is_rejected(self, tmp_path):
        repo = make_full_registry_repo(tmp_path)
        set_agent_model(repo, ROLE, "claude-haiku-9.9")
        r = run_pre_commit(repo)
        assert r.returncode != 0, out(r)
        assert "Model not in the registry" in out(r)

    def test_hyphenated_render_form_is_rejected_as_source(self, tmp_path):
        repo = make_full_registry_repo(tmp_path)
        hyphenated = REGISTRY["models"][ROLE_PIN]["ids"]["claude"]
        if hyphenated == ROLE_PIN:
            pytest.skip("registry pin has no distinct hyphenated render form")
        set_agent_model(repo, ROLE, hyphenated)
        r = run_pre_commit(repo)
        assert r.returncode != 0, out(r)
        assert "Model not in the registry" in out(r)

    def test_newly_registered_model_needs_no_hook_change(self, tmp_path):
        """I6: adding a registry model (and pinning to it) is accepted without touching any hook."""
        repo = make_full_registry_repo(tmp_path)
        new_id = "claude-haiku-9.9"
        reg_path = repo / "config" / "models.yaml"
        reg = yaml.safe_load(reg_path.read_text())
        reg["models"][new_id] = {"family": "haiku", "status": "current", "verified": None, "source": None,
                                 "ids": {"claude": "claude-haiku-9-9", "copilot": new_id,
                                         "opencode": "claude-haiku-9-9"}}
        reg_path.write_text(yaml.safe_dump(reg, sort_keys=False))
        set_agent_model(repo, ROLE, new_id)
        git(repo, "add", "config/models.yaml")
        r = run_pre_commit(repo)
        assert "Model not in the registry" not in out(r), out(r)

    def test_stale_generated_target_is_rejected(self, tmp_path):
        """Re-pinning in the registry without `models.py sync` leaves generated files stale."""
        repo = make_full_registry_repo(tmp_path)
        edit_registry(repo, change_pin)
        r = run_pre_commit(repo)
        assert r.returncode != 0, out(r)
        assert "stale" in out(r) or "models.py check failed" in out(r)

    def test_registry_shape_error_is_rejected(self, tmp_path):
        repo = make_full_registry_repo(tmp_path)
        edit_registry(repo, lambda t: t.replace(f"  {ROLE}:\n    model: {ROLE_PIN}",
                                                f"  {ROLE}:\n    model: claude-nonexistent-1", 1))
        r = run_pre_commit(repo)
        assert r.returncode != 0, out(r)
        assert "models.py check failed" in out(r)

    # -- S3: filenames with spaces must not make the per-file check fail open --

    def test_staged_agent_file_with_space_in_name_is_still_checked(self, tmp_path):
        repo = make_full_registry_repo(tmp_path)
        src = (repo / "src" / "agents" / f"{ROLE}-agent.md").read_text()
        bad = re.sub(r"(?m)^model: .*$", "model: claude-haiku-9.9", src, count=1)
        odd = repo / "src" / "agents" / "my odd name-agent.md"
        odd.write_text(bad)
        git(repo, "add", "src/agents/my odd name-agent.md")
        r = run_pre_commit(repo)
        assert r.returncode != 0, out(r)
        assert "Model not in the registry" in out(r)
        assert "my odd name-agent.md" in out(r)

    # -- S4: checks run against the INDEX, not the working tree --

    def test_staged_registry_error_is_caught_even_if_worktree_is_fixed(self, tmp_path):
        repo = make_full_registry_repo(tmp_path)
        good = (repo / "config" / "models.yaml").read_text()
        edit_registry(repo, lambda t: t.replace(f"  {ROLE}:\n    model: {ROLE_PIN}",
                                                f"  {ROLE}:\n    model: claude-nonexistent-1", 1))
        (repo / "config" / "models.yaml").write_text(good)  # worktree "fixed", index still broken
        r = run_pre_commit(repo)
        assert r.returncode != 0, out(r)
        assert "models.py check failed" in out(r)

    def test_unstaged_worktree_breakage_does_not_fail_a_clean_index(self, tmp_path):
        repo = make_full_registry_repo(tmp_path)
        agent = repo / "src" / "agents" / f"{ROLE}-agent.md"
        agent.write_text(agent.read_text() + "\n")  # a real, staged, registry-related change ...
        git(repo, "add", str(agent.relative_to(repo)))
        # ... then break the registry in the working tree only, never staged.
        (repo / "config" / "models.yaml").write_text("schema_version: 1\nroles: [broken\n")
        r = run_pre_commit(repo)
        assert "model registry violation" not in out(r), out(r)


def _floored_role_and_low_model():
    """(role, model) where the role's family has a min_pin and `model` is below it."""
    for role, cfg in REGISTRY["roles"].items():
        fam = REGISTRY["models"][cfg["model"]]["family"]
        floor = REGISTRY["families"][fam].get("min_pin")
        if not floor:
            continue
        for mid, m in REGISTRY["models"].items():
            if m["family"] == fam and m["status"] != "retired" and models_cli._below_min_pin(REGISTRY, mid):
                return role, mid
    return None, None


class TestPreCommitFamilyFloor:
    def test_pin_below_family_floor_is_rejected(self, tmp_path):
        role, low = _floored_role_and_low_model()
        if role is None:
            pytest.skip("registry defines no family min_pin with a below-floor model")
        pin = REGISTRY["roles"][role]["model"]
        repo = make_full_registry_repo(tmp_path)
        edit_registry(repo, lambda t: t.replace(f"  {role}:\n    model: {pin}", f"  {role}:\n    model: {low}", 1))
        r = run_pre_commit(repo)
        assert r.returncode != 0, out(r)
        assert "min_pin" in out(r)
        assert "models.py check failed" in out(r)

    def test_floor_applies_to_pins_not_fallbacks(self):
        """A below-floor model is a legal fallback target: check reports no error for it."""
        errors, _ = models_cli.check(REPO_ROOT)
        assert not [e for e in errors if "fallback" in e and "min_pin" in e]

    def test_missing_pyyaml_fails_loudly(self, tmp_path):
        repo = make_full_registry_repo(tmp_path)
        edit_registry(repo, change_pin)
        block = tmp_path.parent / (tmp_path.name + "-noyaml")
        block.mkdir()
        (block / "yaml.py").write_text("raise ImportError('PyYAML blocked for test')\n")
        r = run_pre_commit(repo, PYTHONPATH=str(block))
        assert r.returncode != 0, out(r)
        assert "PyYAML" in out(r)

    def test_skip_hooks_bypasses_registry_check(self, tmp_path):
        repo = make_full_registry_repo(tmp_path)
        edit_registry(repo, change_pin)
        r = run_pre_commit(repo, SKIP_HOOKS="1")
        assert r.returncode == 0, out(r)


# ── relaxing the approval gate keeps every consistency check hard-failing ─────

class TestConsistencyStillEnforced:
    """With no approval trailer anywhere, the single reference table is still guarded by
    `scripts/models.py check` / `sync --check`: floating aliases, unknown ids and stale
    generated artifacts fail. (Wider coverage: tests/test_models_registry.py.)"""

    @staticmethod
    def tree(tmp_path):
        from tests.test_models_registry import make_tree
        return make_tree(tmp_path)

    @staticmethod
    def cli(root, *args):
        from tests.test_models_registry import cli
        return cli(*args, root=root)

    @staticmethod
    def set_pin(root, value):
        from tests.test_models_registry import edit_registry as edit_reg
        edit_reg(root, lambda r: r["roles"][ROLE].update(model=value))

    def test_unchanged_tree_passes_both(self, tmp_path):
        root = self.tree(tmp_path)
        assert self.cli(root, "check").returncode == 0
        assert self.cli(root, "sync", "--check").returncode == 0

    @pytest.mark.parametrize("bad", ["claude-sonnet-latest", "claude-sonnet", "latest",
                                     "claude-sonnet-99.9"])
    def test_floating_alias_or_unknown_id_is_rejected(self, tmp_path, bad):
        root = self.tree(tmp_path)
        self.set_pin(root, bad)
        r = self.cli(root, "check")
        assert r.returncode == 1, out(r)
        assert ROLE in out(r) or bad in out(r)

    def test_a_valid_pin_change_still_needs_history_and_sync_not_a_trailer(self, tmp_path):
        """A re-pin without its pin_history entry fails check (consistency), with no mention
        of any approval trailer; the trailer text is gone from the checker."""
        root = self.tree(tmp_path)
        self.set_pin(root, ALT_PIN)
        r = self.cli(root, "check")
        assert r.returncode == 1, out(r)
        assert "pin_history" in out(r) and TRAILER_NAME not in out(r)

    def test_stale_generated_artifact_fails_sync_check(self, tmp_path):
        root = self.tree(tmp_path)
        agent = root / "src" / "agents" / f"{ROLE}-agent.md"
        agent.write_text(re.sub(r"(?m)^model: .*$", f"model: {ALT_PIN}", agent.read_text(), count=1))
        r = self.cli(root, "sync", "--check")
        assert r.returncode == 1, out(r)
