"""
tests/test_pin_policy_fingerprint.py - the Model Pin Change approval gate covers the whole
pin POLICY, and pin_history is append-only.

Gated fingerprint (scanner and commit-msg hook): roles.*.model, roles.*.fallback,
roles.*.effort, families.*.min_pin, fallback_policy. Comments and other registry content are
not gated. pin_history: the parent's list must be a prefix of the child's; a trailer does not
waive a rewrite. Real scratch git repos throughout.
"""

import re

import pytest

from tests.test_check_pin_trailers import (  # noqa: F401
    TRAILER, commit, git, run_scan, scan_repo, touch_commit,
)
from tests.test_model_pin_hooks import (  # noqa: F401
    REGISTRY, ROLE, change_effort_only, change_fallback_only, edit_registry, make_repo,
    out, run_commit_msg,
)

FLOORED = next(f for f, c in REGISTRY["families"].items() if (c or {}).get("min_pin"))


def drop_min_pin(text):
    new, n = re.subn(r"\n    min_pin: \S+", "", text, count=1)
    assert n == 1
    return new


def widen_adjacent(text):
    new = text.replace("    fable: [opus]", "    fable: [opus, haiku]", 1)
    assert new != text
    return new


def change_effort(text):
    cfg = REGISTRY["roles"][ROLE]
    new = text.replace(f"    effort: {cfg['effort']}\n    fallback: [{', '.join(cfg['fallback'])}]",
                       f"    effort: {'low' if cfg['effort'] != 'low' else 'max'}\n"
                       f"    fallback: [{', '.join(cfg['fallback'])}]", 1)
    assert new != text
    return new


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


GATED = [("drop_min_pin", drop_min_pin), ("widen_adjacent", widen_adjacent),
         ("fallback_list", change_fallback_only), ("effort", change_effort)]


class TestScannerPolicyFingerprint:
    @pytest.mark.parametrize("name,mutate", GATED, ids=[g[0] for g in GATED])
    def test_policy_change_without_trailer_fails(self, tmp_path, name, mutate):
        repo = scan_repo(tmp_path)
        edit_registry(repo, mutate)
        commit(repo, "chore: tweak registry")
        r = run_scan(repo)
        assert r.returncode == 1, r.stdout + r.stderr

    @pytest.mark.parametrize("name,mutate", GATED, ids=[g[0] for g in GATED])
    def test_policy_change_with_trailer_passes(self, tmp_path, name, mutate):
        repo = scan_repo(tmp_path)
        edit_registry(repo, mutate)
        commit(repo, "chore: tweak registry\n\n" + TRAILER)
        r = run_scan(repo)
        assert r.returncode == 0, r.stdout + r.stderr

    def test_comment_only_registry_edit_still_needs_no_trailer(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, change_effort_only)
        commit(repo, "chore: comment-only")
        assert run_scan(repo).returncode == 0

    def test_output_names_item_paths_not_values(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, drop_min_pin)
        commit(repo, "chore: tweak registry")
        r = run_scan(repo)
        assert "families.%s.min_pin" % FLOORED in r.stdout
        assert str(REGISTRY["families"][FLOORED]["min_pin"]) not in r.stdout


class TestScannerHistoryAppendOnly:
    @pytest.mark.parametrize("mutate", [edit_old_history, delete_history_entry, reorder_history])
    def test_rewrite_fails_even_with_trailer(self, tmp_path, mutate):
        repo = scan_repo(tmp_path)
        edit_registry(repo, mutate)
        commit(repo, "chore: history\n\n" + TRAILER)
        r = run_scan(repo)
        assert r.returncode == 1, r.stdout + r.stderr
        assert "pin_history" in r.stdout

    def test_append_passes_without_trailer_when_no_policy_changes(self, tmp_path):
        repo = scan_repo(tmp_path)
        edit_registry(repo, append_history)
        commit(repo, "chore: record history")
        r = run_scan(repo)
        assert r.returncode == 0, r.stdout + r.stderr

    def test_rewrite_in_a_merge_is_caught(self, tmp_path):
        repo = scan_repo(tmp_path)
        base = git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        git(repo, "checkout", "-q", "-b", "side")
        touch_commit(repo)
        git(repo, "checkout", "-q", base)
        touch_commit(repo, "y.txt")
        git(repo, "merge", "--no-ff", "--no-commit", "-q", "side")
        edit_registry(repo, edit_old_history)
        commit(repo, "Merge side\n\n" + TRAILER)
        assert run_scan(repo).returncode == 1


class TestCommitMsgHookPolicyFingerprint:
    @pytest.mark.parametrize("name,mutate", GATED, ids=[g[0] for g in GATED])
    def test_policy_change_without_trailer_fails(self, tmp_path, name, mutate):
        repo = make_repo(tmp_path)
        edit_registry(repo, mutate)
        r = run_commit_msg(repo, "chore: tweak registry\n")
        assert r.returncode == 1, out(r)
        assert "Model-Pin-Approved-By" in out(r)

    @pytest.mark.parametrize("name,mutate", GATED, ids=[g[0] for g in GATED])
    def test_policy_change_with_trailer_passes(self, tmp_path, name, mutate):
        repo = make_repo(tmp_path)
        edit_registry(repo, mutate)
        r = run_commit_msg(repo, "chore: tweak registry\n\n" + TRAILER + "\n")
        assert r.returncode == 0, out(r)

    def test_comment_only_edit_needs_no_trailer(self, tmp_path):
        repo = make_repo(tmp_path)
        edit_registry(repo, change_effort_only)
        r = run_commit_msg(repo, "chore: comment\n")
        assert r.returncode == 0, out(r)

    @pytest.mark.parametrize("mutate", [edit_old_history, delete_history_entry, reorder_history])
    def test_history_rewrite_fails_even_with_trailer(self, tmp_path, mutate):
        repo = make_repo(tmp_path)
        edit_registry(repo, mutate)
        r = run_commit_msg(repo, "chore: history\n\n" + TRAILER + "\n")
        assert r.returncode == 1, out(r)
        assert "pin_history" in out(r)

    def test_history_append_passes(self, tmp_path):
        repo = make_repo(tmp_path)
        edit_registry(repo, append_history)
        r = run_commit_msg(repo, "chore: record history\n")
        assert r.returncode == 0, out(r)
