"""
tests/test_model_pin_hooks.py - enforcement of the Model Pin Change process.

docs/SPEC.md (Model Pin Change): editing a role's pin in config/models.yaml needs a
`Model-Pin-Approved-By:` trailer on the commit (.githooks/commit-msg), and the
pre-commit hook validates staged agents and the registry through scripts/models.py
instead of a version allowlist (SPEC I6).

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
# the trailer rule, which only compares roles.<role>.model before and after).
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
    """Edit only ROLE's fallback list (never its pin): the trailer rule must not fire."""
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


SUBJECT = "chore: change a role pin for testing the trailer"


class TestCommitMsgModelPinTrailer:
    def test_pin_change_without_trailer_fails(self, tmp_path):
        repo = make_repo(tmp_path)
        edit_registry(repo, change_pin)
        r = run_commit_msg(repo, SUBJECT + "\n")
        assert r.returncode == 1, out(r)
        assert "Model-Pin-Approved-By" in out(r)
        assert f"{ROLE}: {ROLE_PIN} -> {ALT_PIN}" in out(r)

    def test_pin_change_with_trailer_passes(self, tmp_path):
        repo = make_repo(tmp_path)
        edit_registry(repo, change_pin)
        r = run_commit_msg(repo, SUBJECT + "\n\nModel-Pin-Approved-By: Jane Doe\n")
        assert r.returncode == 0, out(r)
        assert "Model Pin Change approved" in out(r)

    @pytest.mark.parametrize("trailer", ["Model-Pin-Approved-By:", "Model-Pin-Approved-By:    "])
    def test_empty_trailer_value_fails(self, tmp_path, trailer):
        repo = make_repo(tmp_path)
        edit_registry(repo, change_pin)
        r = run_commit_msg(repo, SUBJECT + "\n\n" + trailer + "\n")
        assert r.returncode == 1, out(r)

    def test_trailer_must_start_the_line(self, tmp_path):
        """A mention inside prose is not a trailer."""
        repo = make_repo(tmp_path)
        edit_registry(repo, change_pin)
        r = run_commit_msg(repo, SUBJECT + "\n\nsee Model-Pin-Approved-By: Jane\n")
        assert r.returncode == 1, out(r)

    def test_non_pin_registry_edit_needs_no_trailer(self, tmp_path):
        repo = make_repo(tmp_path)
        edit_registry(repo, change_effort_only)
        r = run_commit_msg(repo, "chore: comment-only registry edit\n")
        assert r.returncode == 0, out(r)
        assert "Model-Pin-Approved-By" not in out(r)

    def test_fallback_only_change_now_needs_the_trailer(self, tmp_path):
        """The approval gate covers the whole pin policy (roles.*.fallback included)."""
        repo = make_repo(tmp_path)
        edit_registry(repo, change_fallback_only)
        r = run_commit_msg(repo, "chore: change a fallback list only\n")
        assert r.returncode == 1, out(r)
        assert "Model-Pin-Approved-By" in out(r)

    def test_missing_pyyaml_fails_loudly(self, tmp_path):
        """With a registry change staged and no PyYAML the hook must not silently pass."""
        repo = make_repo(tmp_path)
        edit_registry(repo, change_pin)
        block = tmp_path.parent / (tmp_path.name + "-noyaml")
        block.mkdir()
        (block / "yaml.py").write_text("raise ImportError('PyYAML blocked for test')\n")
        r = run_commit_msg(repo, SUBJECT + "\n\nModel-Pin-Approved-By: Jane\n", PYTHONPATH=str(block))
        assert r.returncode == 1, out(r)
        assert "PyYAML" in out(r)

    def test_hook_copy_outside_repo_tree_still_finds_models_py(self, tmp_path):
        """CI copies hooks into .git/hooks/: there ../scripts does not exist."""
        repo = make_repo(tmp_path)
        edit_registry(repo, change_pin)
        copy = repo / ".git" / "hooks" / "commit-msg"
        shutil.copy(COMMIT_MSG, copy)
        shutil.copytree(REPO_ROOT / "scripts", repo / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        msg = repo / "MSG"
        msg.write_text(SUBJECT + "\n")
        r = subprocess.run([str(copy), str(msg)], cwd=repo, capture_output=True, text=True, timeout=30)
        assert r.returncode == 1 and "Model-Pin-Approved-By" in out(r), out(r)

    def test_commit_not_touching_registry_needs_no_trailer(self, tmp_path):
        repo = make_repo(tmp_path)
        (repo / "x.txt").write_text("x")
        git(repo, "add", "x.txt")
        r = run_commit_msg(repo, "chore: unrelated change here\n")
        assert r.returncode == 0, out(r)

    def test_registry_first_added_counts_as_pin_change(self, tmp_path):
        repo = make_repo(tmp_path, commit_registry=False)
        git(repo, "add", "config/models.yaml")
        r = run_commit_msg(repo, "chore: add the model registry file\n")
        assert r.returncode == 1, out(r)
        ok = run_commit_msg(repo, "chore: add the model registry file\n\nModel-Pin-Approved-By: Jane\n")
        assert ok.returncode == 0, out(ok)

    def test_skip_hooks_with_documented_reason_downgrades_to_warning(self, tmp_path):
        repo = make_repo(tmp_path)
        edit_registry(repo, change_pin)
        r = run_commit_msg(repo, SUBJECT + "\n\nSKIP_HOOKS: incident INC-1234 outage rollback\n",
                           SKIP_HOOKS="1")
        assert r.returncode == 0, out(r)
        assert "bypassed via documented SKIP_HOOKS=1" in out(r)

    def test_skip_hooks_without_reason_still_fails(self, tmp_path):
        repo = make_repo(tmp_path)
        edit_registry(repo, change_pin)
        r = run_commit_msg(repo, SUBJECT + "\n", SKIP_HOOKS="1")
        assert r.returncode == 1, out(r)

    def test_skip_commit_msg_hook_bypasses_everything(self, tmp_path):
        repo = make_repo(tmp_path)
        edit_registry(repo, change_pin)
        r = run_commit_msg(repo, SUBJECT + "\n", SKIP_COMMIT_MSG_HOOK="true")
        assert r.returncode == 0, out(r)

    def test_existing_rules_unchanged_for_registry_commits(self, tmp_path):
        """A trailer does not excuse a too-long subject."""
        repo = make_repo(tmp_path)
        edit_registry(repo, change_pin)
        r = run_commit_msg(repo, "chore: " + "x" * 80 + "\n\nModel-Pin-Approved-By: Jane\n")
        assert r.returncode == 1, out(r)
        assert "too long" in out(r)

    def test_real_repo_pin_change_flow_end_to_end(self, tmp_path):
        """The scratch registry is valid YAML and the pin really changed."""
        repo = make_repo(tmp_path)
        edit_registry(repo, change_pin)
        data = yaml.safe_load((repo / "config" / "models.yaml").read_text())
        assert data["roles"][ROLE]["model"] == ALT_PIN


class TestCommitMsgAmendPath:
    """S2: `git commit --amend` of a pin-changing commit has an EMPTY index diff
    against HEAD for the registry, so a naive hook sees no pin change and lets the
    approval trailer be dropped. The hook must compare against HEAD^ when amending.

    These run real `git commit --amend` so git itself invokes the hook."""

    PIN_MSG = SUBJECT + "\n\nModel-Pin-Approved-By: Jane Doe\n"

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

    def commit_pin(self, repo):
        edit_registry(repo, change_pin)
        git(repo, "commit", "-q", "-m", self.PIN_MSG)  # hooks still disabled here

    @staticmethod
    def amend(repo, hooks, message):
        git(repo, "config", "core.hooksPath", str(hooks))
        return git(repo, "commit", "--amend", "-q", "-m", message, check=False)

    def test_amend_of_pin_commit_dropping_trailer_is_rejected(self, tmp_path):
        repo, hooks = self.hooked_repo(tmp_path)
        self.commit_pin(repo)
        r = self.amend(repo, hooks, SUBJECT)
        assert r.returncode != 0, out(r)
        assert "Model-Pin-Approved-By" in out(r)
        assert f"{ROLE}: {ROLE_PIN} -> {ALT_PIN}" in out(r)
        # The commit was not rewritten.
        assert "Model-Pin-Approved-By: Jane Doe" in git(repo, "log", "-1", "--format=%B").stdout

    def test_amend_of_pin_commit_keeping_trailer_is_accepted(self, tmp_path):
        repo, hooks = self.hooked_repo(tmp_path)
        self.commit_pin(repo)
        r = self.amend(repo, hooks, SUBJECT + " (reworded)\n\nModel-Pin-Approved-By: Jane Doe")
        assert r.returncode == 0, out(r)
        assert "reworded" in git(repo, "log", "-1", "--format=%s").stdout

    def test_amend_of_non_pin_commit_is_unaffected(self, tmp_path):
        repo, hooks = self.hooked_repo(tmp_path)
        self.commit_pin(repo)
        (repo / "x.txt").write_text("x")
        git(repo, "add", "x.txt")
        git(repo, "commit", "-q", "-m", "chore: unrelated change here")
        r = self.amend(repo, hooks, "chore: unrelated change reworded")
        assert r.returncode == 0, out(r)

    def test_new_unrelated_commit_after_pin_commit_needs_no_trailer(self, tmp_path):
        """Guard against over-correcting: only an AMEND compares against HEAD^."""
        repo, hooks = self.hooked_repo(tmp_path)
        self.commit_pin(repo)
        (repo / "x.txt").write_text("x")
        git(repo, "add", "x.txt")
        git(repo, "config", "core.hooksPath", str(hooks))
        r = git(repo, "commit", "-q", "-m", "chore: unrelated follow-up", check=False)
        assert r.returncode == 0, out(r)

    def test_amend_that_adds_a_pin_change_to_a_plain_commit_needs_trailer(self, tmp_path):
        repo, hooks = self.hooked_repo(tmp_path)
        (repo / "x.txt").write_text("x")
        git(repo, "add", "x.txt")
        git(repo, "commit", "-q", "-m", "chore: unrelated change here")
        edit_registry(repo, change_pin)  # staged, then folded in by the amend
        r = self.amend(repo, hooks, "chore: unrelated change here")
        assert r.returncode != 0 and "Model-Pin-Approved-By" in out(r), out(r)

    def test_amend_of_registry_introducing_root_commit_needs_trailer(self, tmp_path):
        repo, hooks = self.hooked_repo(tmp_path, commit_registry=False)
        git(repo, "add", "config/models.yaml")
        git(repo, "commit", "-q", "-m", "chore: add the model registry file\n\nModel-Pin-Approved-By: Jane")
        r = self.amend(repo, hooks, "chore: add the model registry file")
        assert r.returncode != 0 and "Model-Pin-Approved-By" in out(r), out(r)


class TestCommitMsgRebaseAndCherryPick:
    """git rebase reword/squash/fixup and cherry-pick create commits that replace HEAD (rebase)
    or sit on HEAD (cherry-pick). A reworded pin commit has an EMPTY registry diff against
    HEAD, so the hook must compare against HEAD^ for the amend-like rebase actions (detected
    from GIT_REFLOG_ACTION, independent of the parent-process heuristic).

    Limit (documented in the hook header): git 2.43 does not run commit-msg at all for the
    final squash/fixup commit, and `--no-verify`/`-n` skips it everywhere, so the pre-push
    hook and the CI scanner are the authoritative backstop."""

    PIN_MSG = SUBJECT + "\n\nModel-Pin-Approved-By: Jane Doe\n"
    hooked_repo = staticmethod(TestCommitMsgAmendPath.hooked_repo)

    @staticmethod
    def editor(tmp_path, message):
        """A GIT_EDITOR that replaces the whole message with *message*."""
        (tmp_path / "newmsg").write_text(message)
        script = tmp_path / "editor.sh"
        script.write_text(f'#!/bin/sh\ncat "{tmp_path / "newmsg"}" > "$1"\n')
        script.chmod(0o755)
        return str(script)

    def pin_then_plain(self, tmp_path):
        repo, hooks = self.hooked_repo(tmp_path)
        edit_registry(repo, change_pin)
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

    def test_rebase_reword_of_pin_commit_dropping_trailer_is_rejected(self, tmp_path):
        repo = self.pin_then_plain(tmp_path)
        r = self.rebase(repo, tmp_path, "sed -i '1s/^pick/reword/'", SUBJECT + "\n")
        assert r.returncode != 0, out(r)
        assert "Model-Pin-Approved-By" in out(r) and f"{ROLE}: {ROLE_PIN} -> {ALT_PIN}" in out(r)
        git(repo, "rebase", "--abort", check=False)
        assert "Model-Pin-Approved-By: Jane Doe" in git(repo, "log", "-2", "--format=%B").stdout

    def test_rebase_reword_of_pin_commit_keeping_trailer_is_accepted(self, tmp_path):
        repo = self.pin_then_plain(tmp_path)
        r = self.rebase(repo, tmp_path, "sed -i '1s/^pick/reword/'", SUBJECT + " (reworded)\n\nModel-Pin-Approved-By: Jane Doe\n")
        assert r.returncode == 0, out(r)
        assert "reworded" in git(repo, "log", "-2", "--format=%s").stdout

    def test_rebase_reword_of_plain_commit_above_a_pin_commit_is_unaffected(self, tmp_path):
        repo = self.pin_then_plain(tmp_path)
        r = self.rebase(repo, tmp_path, "sed -i '2s/^pick/reword/'", "chore: unrelated change reworded\n")
        assert r.returncode == 0, out(r)

    @pytest.mark.parametrize("action", ["rebase (reword)", "rebase -i (reword)", "rebase (squash)",
                                        "rebase (fixup)", "rebase -i (fixup)", "rebase (fixup -C)"])
    def test_amend_like_rebase_actions_compare_against_head_parent(self, tmp_path, action):
        """Env-only (no --amend in the parent process): GIT_REFLOG_ACTION alone must select HEAD^."""
        repo = self.pin_then_plain(tmp_path)
        git(repo, "reset", "-q", "--hard", "HEAD~1")  # HEAD is the pin commit, index == HEAD
        r = run_commit_msg(repo, SUBJECT + "\n", GIT_REFLOG_ACTION=action)
        assert r.returncode == 1 and "Model-Pin-Approved-By" in out(r), out(r)
        ok = run_commit_msg(repo, self.PIN_MSG, GIT_REFLOG_ACTION=action)
        assert ok.returncode == 0, out(ok)

    @pytest.mark.parametrize("action", ["rebase (continue)", "rebase (pick)", "cherry-pick", "rebase (start)"])
    def test_non_amend_actions_still_compare_against_head(self, tmp_path, action):
        """A new commit ON TOP of a pin commit has no pin change of its own."""
        repo = self.pin_then_plain(tmp_path)
        git(repo, "reset", "-q", "--hard", "HEAD~1")
        (repo / "y.txt").write_text("y")
        git(repo, "add", "y.txt")
        r = run_commit_msg(repo, "chore: another unrelated change\n", GIT_REFLOG_ACTION=action)
        assert r.returncode == 0, out(r)

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

    def test_cherry_pick_reworded_without_trailer_is_rejected_locally_or_caught_by_the_scanner(self, tmp_path):
        """git does not run commit-msg for `cherry-pick -e`: the dropped trailer must then be
        caught by the scanner (pre-push / CI), which is why it is the authoritative backstop."""
        repo, sha = self.cherry_source(tmp_path, self.PIN_MSG)
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        env = {"GIT_EDITOR": self.editor(tmp_path, SUBJECT + "\n")}
        r = git(repo, "cherry-pick", "-e", sha, check=False, env=env)
        if r.returncode == 0:
            scan = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "check_pin_trailers.py")],
                                  cwd=repo, capture_output=True, text=True)
            assert scan.returncode == 1, out(scan)
        else:
            assert "Model-Pin-Approved-By" in out(r), out(r)

    def test_cherry_pick_reworded_keeping_trailer_is_accepted(self, tmp_path):
        repo, sha = self.cherry_source(tmp_path, self.PIN_MSG)
        env = {"GIT_EDITOR": self.editor(tmp_path, SUBJECT + " (picked)\n\nModel-Pin-Approved-By: Jane Doe\n")}
        r = git(repo, "cherry-pick", "-e", sha, check=False, env=env)
        assert r.returncode == 0, out(r)

    def test_cherry_pick_continue_after_conflict_needs_the_trailer(self, tmp_path):
        """`cherry-pick --continue` makes a real `git commit` (hook runs, parent is HEAD)."""
        repo, sha = self.cherry_source(tmp_path, self.PIN_MSG)
        ALT2 = next(m for m, v in REGISTRY["models"].items() if m not in (ROLE_PIN, ALT_PIN) and v["status"] != "retired")
        main_hooks = git(repo, "config", "core.hooksPath").stdout.strip()
        git(repo, "config", "core.hooksPath", "/nonexistent")
        edit_registry(repo, lambda t: t.replace(f"\n  {ROLE}:\n    model: {ROLE_PIN}\n", f"\n  {ROLE}:\n    model: {ALT2}\n", 1))
        git(repo, "commit", "-q", "-m", "chore: other pin\n\nModel-Pin-Approved-By: Jane Doe")
        git(repo, "config", "core.hooksPath", main_hooks)
        assert git(repo, "cherry-pick", sha, check=False).returncode != 0, "expected a conflict"
        reg = repo / "config" / "models.yaml"
        reg.write_text(re.sub(r"<<<<<<<[^\n]*\n.*?=======\n(.*?)>>>>>>>[^\n]*\n", r"\1", reg.read_text(), flags=re.S))
        git(repo, "add", "config/models.yaml")
        (repo / ".git" / "MERGE_MSG").write_text(SUBJECT + "\n")  # the trailer is dropped here
        r = git(repo, "cherry-pick", "--continue", check=False)
        assert r.returncode != 0 and "Model-Pin-Approved-By" in out(r), out(r)
        assert f"{ROLE}:" in out(r)

    def test_squash_dropping_the_trailer_is_rejected_locally_or_caught_by_the_scanner(self, tmp_path):
        """Whether or not this git runs commit-msg for the squash commit, a dropped trailer
        never gets through unnoticed: the hook rejects it, or the scanner flags the result."""
        repo = self.pin_then_plain(tmp_path)
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD~2")
        r = self.rebase(repo, tmp_path, "sed -i '2s/^pick/squash/'", SUBJECT + "\n")
        if r.returncode == 0:
            scan = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "check_pin_trailers.py")],
                                  cwd=repo, capture_output=True, text=True)
            assert scan.returncode == 1, out(scan)
        else:
            assert "Model-Pin-Approved-By" in out(r), out(r)

    def test_header_documents_that_pre_push_and_ci_are_the_authoritative_backstop(self):
        header = COMMIT_MSG.read_text().split("set -uo pipefail")[0]
        assert "authoritative" in header and "pre-push" in header and "CI" in header
        assert "squash" in header and "--no-verify" in header


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


# ── CI: pin-approval scan over origin/main..HEAD + workflow permissions ───────

CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _ci():
    return yaml.safe_load(CI_YML.read_text())


def _scan_step_run():
    steps = _ci()["jobs"]["quality-gate"]["steps"]
    named = [s for s in steps if s.get("name") == "Model Pin Approval Scan"]
    assert len(named) == 1, "CI must have exactly one 'Model Pin Approval Scan' step"
    return named[0]["run"]


class TestCiPinApprovalScan:
    """The scan logic lives in scripts/check_pin_trailers.py (tests/test_check_pin_trailers.py);
    the workflow step must only invoke it."""

    def test_step_just_invokes_the_script(self):
        run = _scan_step_run()
        assert "scripts/check_pin_trailers.py" in run
        assert "python3 -" not in run and "<<" not in run, "no inline python in the workflow step"
        assert len([ln for ln in run.splitlines() if ln.strip()]) <= 2

    def test_untrusted_text_never_reaches_workflow_expressions(self):
        assert "${{" not in _scan_step_run()

    def test_scanner_script_exists_and_is_executable_python(self):
        script = REPO_ROOT / "scripts" / "check_pin_trailers.py"
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

    def test_quality_gate_checks_out_full_history_for_the_scan(self):
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


class TestPrePushPinScan:
    """pre-push runs scripts/check_pin_trailers.py over the commits being pushed (ref lines
    on stdin, githooks(5)): the local backstop for `--no-verify` commits and rebases. Real
    bare remote; git itself invokes the hook for the push tests."""

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
        for name in ("check_pin_trailers.py", "models.py"):
            shutil.copy(REPO_ROOT / "scripts" / name, work / "scripts" / name)
        hooks = tmp_path / "hooks"
        hooks.mkdir()
        shutil.copy(PRE_PUSH, hooks / "pre-push")
        git(work, "config", "core.hooksPath", str(hooks))
        git(work, "checkout", "-q", "-b", "feat")
        return work, remote

    @staticmethod
    def pin_commit(work, message):
        edit_registry(work, change_pin)
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

    def test_unapproved_pin_commit_push_is_rejected(self, tmp_path):
        work, remote = self.world(tmp_path)
        self.pin_commit(work, SUBJECT)
        r = self.push(work)
        assert r.returncode != 0, out(r)
        assert "Model-Pin-Approved-By" in out(r) and ROLE in out(r)
        assert not self.remote_has(remote), "the rejected push must not reach the remote"

    def test_approved_pin_commit_push_passes(self, tmp_path):
        work, remote = self.world(tmp_path)
        self.pin_commit(work, SUBJECT + "\n\nModel-Pin-Approved-By: Jane Doe")
        r = self.push(work)
        assert r.returncode == 0, out(r)
        assert self.remote_has(remote)

    def test_later_unapproved_commit_on_an_existing_remote_branch_is_rejected(self, tmp_path):
        work, remote = self.world(tmp_path)
        (work / "x.txt").write_text("x")
        git(work, "add", "x.txt")
        git(work, "commit", "-q", "--no-verify", "-m", "chore: unrelated change")
        assert self.push(work).returncode == 0
        self.pin_commit(work, SUBJECT)
        r = self.push(work)  # range remote_sha..local_sha
        assert r.returncode != 0, out(r)

    def test_force_push_of_a_rewritten_commit_without_the_trailer_is_rejected(self, tmp_path):
        work, remote = self.world(tmp_path)
        self.pin_commit(work, SUBJECT + "\n\nModel-Pin-Approved-By: Jane Doe")
        assert self.push(work).returncode == 0
        git(work, "commit", "--amend", "--no-verify", "-q", "-m", SUBJECT)  # rebase/amend dropped it
        r = self.push(work, "--force")
        assert r.returncode != 0, out(r)

    def test_evil_merge_push_is_rejected(self, tmp_path):
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
        assert r.returncode != 0 and ROLE in out(r), out(r)

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
        self.pin_commit(work, SUBJECT)
        sha = git(work, "rev-parse", "HEAD").stdout.strip()
        r = self.run_hook(work, f"refs/heads/feat {sha} refs/heads/feat {'a' * 40}\n")
        assert r.returncode == 1 and ROLE in out(r), out(r)

    def test_new_remote_ref_scans_origin_main_to_local_sha(self, tmp_path):
        work, _ = self.world(tmp_path)
        self.pin_commit(work, SUBJECT)
        sha = git(work, "rev-parse", "HEAD").stdout.strip()
        r = self.run_hook(work, f"refs/heads/feat {sha} refs/heads/feat {ZERO_SHA}\n")
        assert r.returncode == 1 and "Model-Pin-Approved-By" in out(r), out(r)

    def test_missing_pyyaml_fails_loudly(self, tmp_path):
        work, _ = self.world(tmp_path)
        self.pin_commit(work, SUBJECT + "\n\nModel-Pin-Approved-By: Jane Doe")
        sha = git(work, "rev-parse", "HEAD").stdout.strip()
        shim = tmp_path / "shim"
        shim.mkdir()
        (shim / "yaml.py").write_text("raise ImportError('no yaml here')\n")
        r = self.run_hook(work, f"refs/heads/feat {sha} refs/heads/feat {ZERO_SHA}\n", PYTHONPATH=str(shim))
        assert r.returncode == 1, out(r)
        assert "PyYAML" in out(r)

    def test_missing_scanner_script_fails_loudly(self, tmp_path):
        work, _ = self.world(tmp_path)
        self.pin_commit(work, SUBJECT)
        (work / "scripts" / "check_pin_trailers.py").unlink()
        sha = git(work, "rev-parse", "HEAD").stdout.strip()
        r = self.run_hook(work, f"refs/heads/feat {sha} refs/heads/feat {ZERO_SHA}\n")
        assert r.returncode == 1 and "check_pin_trailers" in out(r), out(r)

    def test_skip_hooks_bypasses_like_the_other_hooks_and_ci_still_catches_it(self, tmp_path):
        """SKIP_HOOKS=1 / GIT_SKIP_HOOKS=1 skip pre-push entirely (documented emergency bypass);
        the CI scan is the authoritative backstop for such a push."""
        work, remote = self.world(tmp_path)
        self.pin_commit(work, SUBJECT)
        r = self.push(work, SKIP_HOOKS="1")
        assert r.returncode == 0, out(r)
        assert self.remote_has(remote)
        scan = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "check_pin_trailers.py")], cwd=work,
                              capture_output=True, text=True)
        assert scan.returncode == 1
        text = PRE_PUSH.read_text()
        assert "SKIP_HOOKS=1" in text.split("set -euo pipefail")[0]
        assert "CI" in text.split("set -euo pipefail")[0]

    def test_hook_header_documents_the_pin_scan(self):
        header = PRE_PUSH.read_text().split("set -euo pipefail")[0]
        assert "check_pin_trailers" in header and "Model-Pin-Approved-By" in header


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
