"""
tests/test_check_pin_history.py - the advisory pin_history audit scanner.

scripts/check_pin_history.py is used by CI (the "Model Pin History Audit (advisory)" step)
and by .githooks/pre-push. Changing a role's pin (or any other policy item) in
config/models.yaml needs no trailer or approval. The only thing audited is that
pin_history stays append-only: a commit whose parent's pin_history is not an unchanged
prefix of its own prints a warning. The scanner exits 0 regardless (1 only with --strict).

All scenarios use real scratch git repos; no model ID is hard-coded.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_model_pin_hooks import (  # noqa: F401  (shared scratch-repo helpers)
    ALT_PIN, REGISTRY, ROLE, ROLE_PIN, SUBJECT, edit_registry, change_effort_only,
    change_pin, git, make_repo, out,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_pin_history.py"
# A third distinct non-retired model, for conflicting pin edits.
ALT2_PIN = next(mid for mid, m in REGISTRY["models"].items()
                if mid not in (ROLE_PIN, ALT_PIN) and m["status"] != "retired")


def pin_to(value):
    """Mutator: set ROLE's pin to *value* whatever it currently is."""
    def mutate(text):
        new, n = re.subn(rf"(\n  {re.escape(ROLE)}:\n    model: )\S+", lambda m: m.group(1) + value, text, count=1)
        assert n == 1, "role block not found"
        return new
    return mutate


def edit_old_history(text):
    new = text.replace("baseline: seeded from tree", "baseline: forged tree", 1)
    assert new != text
    return new


def delete_history_entry(text):
    lines = text.rstrip("\n").split("\n")
    idx = max(i for i, ln in enumerate(lines) if ln.lstrip().startswith("- {date:"))
    del lines[idx]
    return "\n".join(lines) + "\n"


def reorder_history(text):
    lines = text.rstrip("\n").split("\n")
    idx = [i for i, ln in enumerate(lines) if ln.lstrip().startswith("- {date:")]
    lines[idx[0]], lines[idx[1]] = lines[idx[1]], lines[idx[0]]
    return "\n".join(lines) + "\n"


def append_history(text):
    return text.rstrip("\n") + (
        "\n  - {date: 2026-10-03, role: engineer, from: x, to: y, approval: \"test append\"}\n")


REWRITES = [edit_old_history, delete_history_entry, reorder_history]


def scan_repo(tmp_path):
    """Scratch repo: registry seed commit also marked as the fake origin/main."""
    repo = make_repo(tmp_path)
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repo


def run_scan(repo, *args, **env):
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=repo, capture_output=True,
                          text=True, timeout=60, env={**os.environ, **env})


def commit(repo, message):
    git(repo, "commit", "-q", "-m", message)


def pin_commit(repo, value, message):
    edit_registry(repo, pin_to(value))
    commit(repo, message)


def touch_commit(repo, name="x.txt", message="chore: unrelated change"):
    (repo / name).write_text(name)
    git(repo, "add", name)
    commit(repo, message)


def branch(repo):
    return git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def is_clean(result):
    """No warning of any kind and a zero exit."""
    return result.returncode == 0 and "warning" not in out(result).lower()


class TestPinChangesNeedNoApproval:
    def test_pin_commit_without_trailer_is_clean(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        commit(repo, SUBJECT)
        r = run_scan(repo)
        assert is_clean(r), out(r)
        assert "1 commit(s) checked" in r.stdout

    def test_pin_change_with_appended_history_entry_is_clean(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, lambda t: append_history(change_pin(t)))
        commit(repo, SUBJECT)
        assert is_clean(run_scan(repo)), out(run_scan(repo))

    def test_non_pin_registry_commit_and_unrelated_commit_are_clean(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_effort_only)
        commit(repo, "chore: comment-only registry edit")
        touch_commit(repo)
        assert is_clean(run_scan(repo))

    def test_append_only_change_is_clean(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, append_history)
        commit(repo, "chore: record history")
        assert is_clean(run_scan(repo))

    def test_no_trailer_text_is_ever_demanded(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        commit(repo, SUBJECT)
        assert "trailer" not in out(run_scan(repo)).lower()
        assert "Approved-By" not in out(run_scan(repo, "--strict"))

    def test_revert_restoring_the_previous_pin_is_clean(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        commit(repo, SUBJECT)
        git(repo, "revert", "--no-edit", "HEAD")
        assert is_clean(run_scan(repo))


class TestHistoryRewriteIsAdvisory:
    @pytest.mark.parametrize("mutate", REWRITES, ids=lambda f: f.__name__)
    def test_rewrite_warns_and_exits_zero(self, tmp_path, mutate):
        repo = scan_repo(tmp_path)
        edit_registry(repo, mutate)
        commit(repo, "chore: history")
        r = run_scan(repo)
        assert r.returncode == 0, out(r)
        assert "warning: commit" in r.stdout and "pin_history" in r.stdout

    @pytest.mark.parametrize("mutate", REWRITES, ids=lambda f: f.__name__)
    def test_strict_exits_one_on_rewrite(self, tmp_path, mutate):
        repo = scan_repo(tmp_path)
        edit_registry(repo, mutate)
        commit(repo, "chore: history")
        assert run_scan(repo, "--strict").returncode == 1

    def test_strict_is_clean_without_a_rewrite(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        commit(repo, SUBJECT)
        assert run_scan(repo, "--strict").returncode == 0

    def test_rewrite_in_a_merge_is_caught(self, tmp_path):
        repo = scan_repo(tmp_path)
        base = branch(repo)
        git(repo, "checkout", "-q", "-b", "side")
        touch_commit(repo)
        git(repo, "checkout", "-q", base)
        touch_commit(repo, "y.txt")
        git(repo, "merge", "--no-ff", "--no-commit", "-q", "side")
        edit_registry(repo, edit_old_history)
        commit(repo, "Merge side")
        r = run_scan(repo)
        assert r.returncode == 0 and "warning: commit" in r.stdout
        assert run_scan(repo, "--strict").returncode == 1

    def test_merge_dropping_history_carried_by_the_second_parent_is_caught(self, tmp_path):
        """The side branch appended a pin_history entry; the merge resolves to main's registry
        (identical to parent 1), silently discarding it. Only parent 2 reveals the loss."""
        repo = scan_repo(tmp_path)
        base = branch(repo)
        git(repo, "checkout", "-q", "-b", "side")
        edit_registry(repo, append_history)
        commit(repo, "feat: side history entry")
        git(repo, "checkout", "-q", base)
        touch_commit(repo, "y.txt")
        git(repo, "merge", "--no-ff", "--no-commit", "-q", "side")
        git(repo, "checkout", "HEAD", "--", "config/models.yaml")
        commit(repo, "Merge side")
        r = run_scan(repo)
        assert r.returncode == 0 and "warning: commit" in r.stdout
        assert run_scan(repo, "--strict").returncode == 1

    def test_clean_merge_keeping_both_sides_history_is_clean(self, tmp_path):
        repo = scan_repo(tmp_path)
        base = branch(repo)
        git(repo, "checkout", "-q", "-b", "side")
        edit_registry(repo, append_history)
        commit(repo, "feat: side history entry")
        git(repo, "checkout", "-q", base)
        touch_commit(repo, "y.txt")
        git(repo, "merge", "--no-ff", "-q", "-m", "Merge side", "side")
        assert is_clean(run_scan(repo, "--strict"))

    def test_merge_that_does_not_touch_the_registry_is_clean(self, tmp_path):
        repo = scan_repo(tmp_path)
        base = branch(repo)
        git(repo, "checkout", "-q", "-b", "side")
        touch_commit(repo)
        git(repo, "checkout", "-q", base)
        touch_commit(repo, "y.txt")
        git(repo, "merge", "--no-ff", "-q", "-m", "Merge side", "side")
        assert is_clean(run_scan(repo, "--strict"))

    def test_github_annotations_only_under_actions(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, edit_old_history)
        commit(repo, SUBJECT)
        assert "::warning::" in out(run_scan(repo, GITHUB_ACTIONS="true"))
        assert "::warning::" not in out(run_scan(repo, GITHUB_ACTIONS=""))
        assert "::error::" not in out(run_scan(repo, GITHUB_ACTIONS="true"))

    def test_output_names_short_sha_but_neither_models_nor_message_text(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, lambda t: edit_old_history(change_pin(t)))
        commit(repo, "chore: INJECTED_MARKER ::error::forged annotation\n\nbody text BODY_MARKER")
        sha = git(repo, "rev-parse", "HEAD").stdout.strip()
        text = out(run_scan(repo))
        assert sha[:12] in text
        assert "INJECTED_MARKER" not in text and "BODY_MARKER" not in text and "forged" not in text
        assert ROLE_PIN not in text and ALT_PIN not in text


class TestRangeAndEnvironment:
    def test_introducing_the_registry_is_not_flagged(self, tmp_path):
        repo = make_repo(tmp_path, commit_registry=False)
        (repo / "README.md").write_text("x")
        git(repo, "add", "README.md")
        commit(repo, "chore: base without a registry")
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(repo, "add", "config/models.yaml")
        commit(repo, "feat: introduce the model registry")
        assert is_clean(run_scan(repo, "--strict"))

    def test_root_commit_in_range_is_not_flagged(self, tmp_path):
        """base is an unrelated orphan commit, so the seed (root) commit is inside base..head."""
        repo = make_repo(tmp_path)
        main = branch(repo)
        git(repo, "checkout", "-q", "--orphan", "other")
        git(repo, "rm", "-rqf", "--cached", ".")
        git(repo, "commit", "-q", "--allow-empty", "-m", "chore: unrelated orphan base")
        orphan = git(repo, "rev-parse", "HEAD").stdout.strip()
        git(repo, "checkout", "-qf", main)
        r = run_scan(repo, "--base", orphan, "--strict")
        assert is_clean(r), out(r)
        assert "1 commit(s) checked" in r.stdout

    def test_only_commits_after_base_are_scanned(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, edit_old_history)
        commit(repo, SUBJECT)  # rewrite ... already on main
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        assert is_clean(run_scan(repo, "--strict"))

    def test_missing_base_ref_skips_with_notice(self, tmp_path):
        repo = scan_repo(tmp_path)
        r = run_scan(repo, "--base", "origin/does-not-exist", "--strict")
        assert r.returncode == 0 and "skipping" in out(r) and "notice" in out(r)

    def test_default_base_is_origin_main_and_head_is_selectable(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, edit_old_history)
        commit(repo, SUBJECT)
        bad = git(repo, "rev-parse", "HEAD").stdout.strip()
        touch_commit(repo)
        assert run_scan(repo, "--head", bad, "--strict").returncode == 1
        assert run_scan(repo, "--head", "origin/main", "--strict").returncode == 0
        assert run_scan(repo, "--base", bad, "--strict").returncode == 0

    def test_bad_head_is_an_environment_error(self, tmp_path):
        repo = scan_repo(tmp_path)
        assert run_scan(repo, "--head", "no-such-ref").returncode == 2

    @pytest.mark.parametrize("opt", ["--base", "--head"])
    def test_option_like_ref_values_are_rejected(self, tmp_path, opt):
        repo = scan_repo(tmp_path)
        r = run_scan(repo, opt + "=--output=/tmp/x")
        assert r.returncode == 2 and "must not start with '-'" in r.stderr

    def test_not_a_git_repo_is_an_environment_error(self, tmp_path):
        assert run_scan(tmp_path, GIT_CEILING_DIRECTORIES=str(tmp_path.parent)).returncode == 2

    def test_missing_pyyaml_fails_loudly(self, tmp_path):
        repo = scan_repo(tmp_path)
        shim = tmp_path / "shim"
        shim.mkdir()
        (shim / "yaml.py").write_text("raise ImportError('no yaml here')\n")
        r = run_scan(repo, PYTHONPATH=str(shim))
        assert r.returncode == 2, out(r)
        assert "PyYAML" in out(r)


class TestSquashRebaseAndCherryPick:
    def test_squash_merge_of_a_pin_change_is_clean(self, tmp_path):
        repo = scan_repo(tmp_path)
        main = branch(repo)
        git(repo, "checkout", "-q", "-b", "side")
        pin_commit(repo, ALT_PIN, SUBJECT)
        git(repo, "checkout", "-q", main)
        git(repo, "merge", "--squash", "side")
        commit(repo, "feat: squashed side branch")
        assert is_clean(run_scan(repo, "--strict"))

    def test_rebased_and_cherry_picked_pin_commits_are_clean(self, tmp_path):
        repo = scan_repo(tmp_path)
        main = branch(repo)
        git(repo, "checkout", "-q", "-b", "side")
        pin_commit(repo, ALT_PIN, SUBJECT)
        sha = git(repo, "rev-parse", "HEAD").stdout.strip()
        git(repo, "checkout", "-q", main)
        touch_commit(repo, "main.txt")
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(repo, "checkout", "-q", "side")
        git(repo, "rebase", "-q", main)
        assert is_clean(run_scan(repo, "--strict"))
        git(repo, "checkout", "-q", main)
        git(repo, "cherry-pick", sha)
        assert is_clean(run_scan(repo, "--strict"))


class TestMergeCommitsWithPinChanges:
    def diverge(self, repo):
        main = branch(repo)
        git(repo, "checkout", "-q", "-b", "side")
        git(repo, "checkout", "-q", main)
        touch_commit(repo, "main.txt")
        return main

    def test_noff_merge_of_a_pin_change_branch_is_clean(self, tmp_path):
        repo = scan_repo(tmp_path)
        main = self.diverge(repo)
        git(repo, "checkout", "-q", "side")
        pin_commit(repo, ALT_PIN, SUBJECT)
        git(repo, "checkout", "-q", main)
        git(repo, "merge", "--no-ff", "-q", "-m", "merge: bring in side", "side")
        assert is_clean(run_scan(repo, "--strict"))

    def test_evil_merge_changing_the_pin_is_clean_without_history_rewrite(self, tmp_path):
        repo = scan_repo(tmp_path)
        main = self.diverge(repo)
        git(repo, "checkout", "-q", "side")
        touch_commit(repo, "side.txt")
        git(repo, "checkout", "-q", main)
        git(repo, "merge", "--no-ff", "--no-commit", "side")
        edit_registry(repo, pin_to(ALT_PIN))
        commit(repo, "merge: bring in side")
        assert is_clean(run_scan(repo, "--strict"))

    def test_conflicting_pin_edits_resolved_to_a_third_pin_are_clean(self, tmp_path):
        repo = scan_repo(tmp_path)
        main = branch(repo)
        git(repo, "checkout", "-q", "-b", "side")
        pin_commit(repo, ALT_PIN, "feat: side pin")
        git(repo, "checkout", "-q", main)
        pin_commit(repo, ALT2_PIN, "feat: main pin")
        assert git(repo, "merge", "--no-ff", "--no-commit", "side", check=False).returncode != 0
        edit_registry(repo, lambda t: pin_to(ROLE_PIN)(re.sub(r"<<<<<<<[^\n]*\n(.*?)=======\n.*?>>>>>>>[^\n]*\n", r"\1", t, flags=re.S)))
        commit(repo, "Merge side")
        assert is_clean(run_scan(repo, "--strict"))
