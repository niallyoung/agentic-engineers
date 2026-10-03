"""
tests/test_check_pin_trailers.py - the one model-pin approval scanner.

scripts/check_pin_trailers.py is used by CI (the "Model Pin Approval Scan" step) and by
.githooks/pre-push. Every commit in <base>..<head> that changes a roles.<role>.model pin in
config/models.yaml must carry a non-empty `Model-Pin-Approved-By:` trailer at the START of a
line (docs/SPEC.md, Model Pin Change). Merge commits are scanned too: a pin change that
exists only in a merge's first-parent diff (conflict resolution / evil merge) needs the
trailer on the merge, or must be exactly a side's already-scanned value.

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
SCRIPT = REPO_ROOT / "scripts" / "check_pin_trailers.py"
TRAILER = "Model-Pin-Approved-By: Jane Doe"
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


# ── behaviour carried over from the former inline CI step ─────────────────────

class TestLinearHistory:
    def test_pin_commit_without_trailer_fails_the_scan(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        commit(repo, SUBJECT)
        r = run_scan(repo)
        assert r.returncode == 1, out(r)
        assert ROLE in out(r) and "Model-Pin-Approved-By" in out(r)

    def test_pin_commit_with_trailer_passes(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        commit(repo, SUBJECT + "\n\n" + TRAILER)
        assert run_scan(repo).returncode == 0

    def test_empty_trailer_fails_the_scan(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        commit(repo, SUBJECT + "\n\nModel-Pin-Approved-By:   ")
        assert run_scan(repo).returncode == 1

    def test_amended_away_trailer_is_caught_even_though_the_hook_was_skipped(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        commit(repo, SUBJECT + "\n\n" + TRAILER)
        git(repo, "commit", "--amend", "-q", "-m", SUBJECT)  # hooks disabled == --no-verify
        assert run_scan(repo).returncode == 1

    def test_non_pin_registry_commit_and_unrelated_commit_pass(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_effort_only)
        commit(repo, "chore: comment-only registry edit")
        touch_commit(repo)
        assert run_scan(repo).returncode == 0

    def test_introducing_the_registry_is_not_a_pin_change(self, tmp_path):
        """Seeding config/models.yaml from nothing must not demand a trailer, but the NEXT
        pin change without one must still be caught."""
        repo = make_repo(tmp_path, commit_registry=False)
        (repo / "README.md").write_text("x")
        git(repo, "add", "README.md")
        commit(repo, "chore: base without a registry")
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(repo, "add", "config/models.yaml")
        commit(repo, "feat: introduce the model registry")
        assert run_scan(repo).returncode == 0
        edit_registry(repo, change_pin)
        commit(repo, SUBJECT)
        r = run_scan(repo)
        assert r.returncode == 1, out(r)
        assert ROLE in out(r)

    def test_only_commits_after_base_are_scanned(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        commit(repo, SUBJECT)  # unapproved pin change ...
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")  # ... already on main
        assert run_scan(repo).returncode == 0

    def test_missing_base_ref_skips_with_notice(self, tmp_path):
        repo = scan_repo(tmp_path)
        r = run_scan(repo, "--base", "origin/does-not-exist")
        assert r.returncode == 0 and "skipping" in out(r)

    def test_default_base_is_origin_main_and_head_is_selectable(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        commit(repo, SUBJECT)
        bad = git(repo, "rev-parse", "HEAD").stdout.strip()
        touch_commit(repo)
        assert run_scan(repo, "--head", bad).returncode == 1
        assert run_scan(repo, "--head", "origin/main").returncode == 0
        assert run_scan(repo, "--base", bad).returncode == 0

    def test_output_names_short_sha_and_role_but_neither_models_nor_message_text(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        commit(repo, "chore: INJECTED_MARKER ::error::forged annotation\n\nbody text BODY_MARKER")
        sha = git(repo, "rev-parse", "HEAD").stdout.strip()
        r = run_scan(repo)
        assert r.returncode == 1
        text = out(r)
        assert sha[:12] in text and ROLE in text
        assert "INJECTED_MARKER" not in text and "BODY_MARKER" not in text and "forged" not in text
        assert ROLE_PIN not in text and ALT_PIN not in text

    def test_github_annotations_only_under_actions(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        commit(repo, SUBJECT)
        assert "::error::" in out(run_scan(repo, GITHUB_ACTIONS="true"))
        assert "::error::" not in out(run_scan(repo, GITHUB_ACTIONS=""))

    def test_missing_pyyaml_fails_loudly(self, tmp_path):
        repo = scan_repo(tmp_path)
        shim = tmp_path / "shim"
        shim.mkdir()
        (shim / "yaml.py").write_text("raise ImportError('no yaml here')\n")
        r = run_scan(repo, PYTHONPATH=str(shim))
        assert r.returncode == 2, out(r)
        assert "PyYAML" in out(r)


# ── trailer shape (c) ─────────────────────────────────────────────────────────

class TestTrailerShape:
    @pytest.mark.parametrize("message", [
        SUBJECT + "\n\nSee Model-Pin-Approved-By: Jane Doe in the PR thread",
        SUBJECT + "\n\n  Model-Pin-Approved-By: Jane Doe",
        SUBJECT + " Model-Pin-Approved-By: Jane Doe",
        SUBJECT + "\n\nmodel-pin-approved-by: Jane Doe",
        SUBJECT + "\n\nModel-Pin-Approved-By:\nJane Doe",
    ])
    def test_trailer_not_at_start_of_a_line_or_empty_is_flagged(self, tmp_path, message):
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        commit(repo, message)
        r = run_scan(repo)
        assert r.returncode == 1, out(r)

    def test_trailer_in_the_body_not_only_the_last_paragraph_is_accepted(self, tmp_path):
        """Matches .githooks/commit-msg, which accepts any line-start trailer."""
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        commit(repo, SUBJECT + "\n\n" + TRAILER + "\n\nMore prose after the trailer.")
        assert run_scan(repo).returncode == 0


# ── squash / rebase (b) ───────────────────────────────────────────────────────

class TestSquashAndRebase:
    def test_squash_merge_without_trailer_is_flagged(self, tmp_path):
        repo = scan_repo(tmp_path)
        main = branch(repo)
        git(repo, "checkout", "-q", "-b", "side")
        pin_commit(repo, ALT_PIN, SUBJECT + "\n\n" + TRAILER)
        git(repo, "checkout", "-q", main)
        git(repo, "merge", "--squash", "side")
        commit(repo, "feat: squashed side branch")  # squash dropped the trailer
        r = run_scan(repo)
        assert r.returncode == 1, out(r)

    def test_squash_merge_with_trailer_passes(self, tmp_path):
        repo = scan_repo(tmp_path)
        main = branch(repo)
        git(repo, "checkout", "-q", "-b", "side")
        pin_commit(repo, ALT_PIN, SUBJECT + "\n\n" + TRAILER)
        git(repo, "checkout", "-q", main)
        git(repo, "merge", "--squash", "side")
        commit(repo, "feat: squashed side branch\n\n" + TRAILER)
        assert run_scan(repo).returncode == 0

    def test_rebase_that_rewords_away_the_trailer_is_flagged(self, tmp_path):
        repo = scan_repo(tmp_path)
        main = branch(repo)
        git(repo, "checkout", "-q", "-b", "side")
        pin_commit(repo, ALT_PIN, SUBJECT + "\n\n" + TRAILER)
        git(repo, "checkout", "-q", main)
        touch_commit(repo, "main.txt")
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(repo, "checkout", "-q", "side")
        # Rebase onto the new main, rewriting the message without the trailer (hooks off).
        git(repo, "rebase", "-q", main)
        assert run_scan(repo).returncode == 0  # a plain rebase keeps the message
        git(repo, "commit", "--amend", "-q", "-m", SUBJECT)
        assert run_scan(repo).returncode == 1

    def test_cherry_picked_pin_commit_keeps_or_loses_the_trailer(self, tmp_path):
        repo = scan_repo(tmp_path)
        main = branch(repo)
        git(repo, "checkout", "-q", "-b", "side")
        pin_commit(repo, ALT_PIN, SUBJECT)  # unapproved
        sha = git(repo, "rev-parse", "HEAD").stdout.strip()
        git(repo, "checkout", "-q", main)
        git(repo, "cherry-pick", sha)
        assert run_scan(repo).returncode == 1
        git(repo, "commit", "--amend", "-q", "-m", SUBJECT + "\n\n" + TRAILER)
        assert run_scan(repo).returncode == 0


# ── merge commits (a) ─────────────────────────────────────────────────────────

class TestMergeCommits:
    def diverge(self, repo):
        """main gets an unrelated commit and `side` starts from the seed, so a merge is real."""
        main = branch(repo)
        git(repo, "checkout", "-q", "-b", "side")
        git(repo, "checkout", "-q", main)
        touch_commit(repo, "main.txt")
        return main

    def test_noff_merge_of_branch_with_unapproved_pin_commit_is_flagged(self, tmp_path):
        repo = scan_repo(tmp_path)
        main = self.diverge(repo)
        git(repo, "checkout", "-q", "side")
        pin_commit(repo, ALT_PIN, SUBJECT)  # no trailer
        git(repo, "checkout", "-q", main)
        git(repo, "merge", "--no-ff", "-q", "-m", "merge: bring in side", "side")
        r = run_scan(repo)
        assert r.returncode == 1, out(r)
        assert ROLE in out(r)

    def test_noff_merge_of_branch_with_approved_pin_commit_passes(self, tmp_path):
        repo = scan_repo(tmp_path)
        main = self.diverge(repo)
        git(repo, "checkout", "-q", "side")
        pin_commit(repo, ALT_PIN, SUBJECT + "\n\n" + TRAILER)
        git(repo, "checkout", "-q", main)
        git(repo, "merge", "--no-ff", "-q", "-m", "merge: bring in side", "side")
        r = run_scan(repo)
        assert r.returncode == 0, out(r)

    def test_evil_merge_changing_the_pin_without_trailer_is_flagged(self, tmp_path):
        """The merge commit itself carries the pin edit: nothing on either side introduced it."""
        repo = scan_repo(tmp_path)
        main = self.diverge(repo)
        git(repo, "checkout", "-q", "side")
        touch_commit(repo, "side.txt")
        git(repo, "checkout", "-q", main)
        git(repo, "merge", "--no-ff", "--no-commit", "side")
        edit_registry(repo, pin_to(ALT_PIN))
        commit(repo, "merge: bring in side")
        r = run_scan(repo)
        assert r.returncode == 1, out(r)
        assert ROLE in out(r)
        assert "merge" in out(r).lower()

    def test_evil_merge_with_trailer_on_the_merge_passes(self, tmp_path):
        repo = scan_repo(tmp_path)
        main = self.diverge(repo)
        git(repo, "checkout", "-q", "side")
        touch_commit(repo, "side.txt")
        git(repo, "checkout", "-q", main)
        git(repo, "merge", "--no-ff", "--no-commit", "side")
        edit_registry(repo, pin_to(ALT_PIN))
        commit(repo, "merge: bring in side\n\n" + TRAILER)
        assert run_scan(repo).returncode == 0

    def conflicting_pin_branches(self, repo):
        """Both sides re-pin ROLE (each with a trailer); merging conflicts."""
        main = branch(repo)
        git(repo, "checkout", "-q", "-b", "side")
        pin_commit(repo, ALT2_PIN, SUBJECT + "\n\n" + TRAILER)
        git(repo, "checkout", "-q", main)
        pin_commit(repo, ALT_PIN, SUBJECT + "\n\n" + TRAILER)
        merged = git(repo, "merge", "--no-ff", "-q", "-m", "merge: side", "side", check=False)
        assert merged.returncode != 0, "expected a registry conflict"

    def test_conflict_resolved_to_a_third_pin_without_trailer_is_flagged(self, tmp_path):
        repo = scan_repo(tmp_path)
        self.conflicting_pin_branches(repo)
        # Resolve to the ORIGINAL pin: matches neither parent, so no approved commit made it.
        text = subprocess.run(["git", "show", "HEAD~0:config/models.yaml"], cwd=repo,
                              capture_output=True, text=True).stdout
        (repo / "config" / "models.yaml").write_text(pin_to(ROLE_PIN)(text))
        git(repo, "add", "config/models.yaml")
        commit(repo, "merge: side, resolved the pin conflict")
        r = run_scan(repo)
        assert r.returncode == 1, out(r)
        assert ROLE in out(r)

    def test_conflict_resolved_to_a_third_pin_with_trailer_on_merge_passes(self, tmp_path):
        repo = scan_repo(tmp_path)
        self.conflicting_pin_branches(repo)
        text = subprocess.run(["git", "show", "HEAD:config/models.yaml"], cwd=repo,
                              capture_output=True, text=True).stdout
        (repo / "config" / "models.yaml").write_text(pin_to(ROLE_PIN)(text))
        git(repo, "add", "config/models.yaml")
        commit(repo, "merge: side, resolved the pin conflict\n\n" + TRAILER)
        assert run_scan(repo).returncode == 0

    def test_conflict_resolved_to_the_sides_approved_pin_passes(self, tmp_path):
        repo = scan_repo(tmp_path)
        self.conflicting_pin_branches(repo)
        text = subprocess.run(["git", "show", "HEAD:config/models.yaml"], cwd=repo,
                              capture_output=True, text=True).stdout
        (repo / "config" / "models.yaml").write_text(pin_to(ALT2_PIN)(text))
        git(repo, "add", "config/models.yaml")
        commit(repo, "merge: side, took the side's pin")
        r = run_scan(repo)
        assert r.returncode == 0, out(r)

    def test_merging_main_into_a_branch_does_not_flag_pins_already_on_main(self, tmp_path):
        repo = scan_repo(tmp_path)
        main = branch(repo)
        git(repo, "checkout", "-q", "-b", "feature")
        touch_commit(repo, "feature.txt")
        git(repo, "checkout", "-q", main)
        pin_commit(repo, ALT_PIN, SUBJECT)  # lands on main (not scanned: it is in base)
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(repo, "checkout", "-q", "feature")
        git(repo, "merge", "--no-ff", "-q", "-m", "merge: main into feature", "origin/main")
        r = run_scan(repo)
        assert r.returncode == 0, out(r)

    def test_merge_that_does_not_touch_the_pin_is_ignored(self, tmp_path):
        repo = scan_repo(tmp_path)
        main = self.diverge(repo)
        git(repo, "checkout", "-q", "side")
        touch_commit(repo, "side.txt")
        git(repo, "checkout", "-q", main)
        git(repo, "merge", "--no-ff", "-q", "-m", "merge: bring in side", "side")
        assert run_scan(repo).returncode == 0

    def test_octopus_merge_evil_pin_change_is_flagged(self, tmp_path):
        repo = scan_repo(tmp_path)
        main = self.diverge(repo)
        for name in ("a", "b"):
            git(repo, "checkout", "-q", "-b", name, "side")
            touch_commit(repo, name + ".txt")
        git(repo, "checkout", "-q", main)
        git(repo, "merge", "--no-ff", "--no-commit", "a", "b")
        edit_registry(repo, pin_to(ALT_PIN))
        commit(repo, "merge: octopus")
        assert len(git(repo, "rev-list", "--parents", "-1", "HEAD").stdout.split()) == 4
        assert run_scan(repo).returncode == 1


# ── reverts (d) ───────────────────────────────────────────────────────────────

class TestReverts:
    def test_revert_restoring_the_previous_pin_is_not_exempt_and_says_so(self, tmp_path):
        repo = scan_repo(tmp_path)
        pin_commit(repo, ALT_PIN, SUBJECT + "\n\n" + TRAILER)
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(repo, "revert", "--no-edit", "HEAD")  # message carries no trailer
        r = run_scan(repo)
        assert r.returncode == 1, out(r)
        assert "revert" in out(r).lower()
        assert ROLE in out(r)

    def test_revert_with_a_trailer_passes(self, tmp_path):
        repo = scan_repo(tmp_path)
        pin_commit(repo, ALT_PIN, SUBJECT + "\n\n" + TRAILER)
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(repo, "revert", "--no-edit", "HEAD")
        git(repo, "commit", "--amend", "-q", "-m", "Revert pin change\n\n" + TRAILER)
        assert run_scan(repo).returncode == 0

    def test_ordinary_unapproved_commit_is_not_called_a_revert(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        commit(repo, SUBJECT)
        assert "revert" not in out(run_scan(repo)).lower()
