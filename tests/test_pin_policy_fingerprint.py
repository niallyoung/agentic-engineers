"""
tests/test_pin_policy_fingerprint.py - no part of the pin policy is approval-gated any more.

roles.*.model, roles.*.fallback, roles.*.effort, families.*.min_pin and fallback_policy used
to need an approval trailer. They can now change freely in the commit-msg hook and
in the advisory history scanner. pin_history is still an append-only audit record: a rewrite
warns (never fails). Strict consistency lives in `scripts/models.py check`. Real scratch repos.
"""

import re
import subprocess
import sys

import pytest

from tests.test_check_pin_history import (  # noqa: F401
    append_history, commit, delete_history_entry, edit_old_history, is_clean, reorder_history,
    run_scan, scan_repo,
)
from tests.test_model_pin_hooks import (  # noqa: F401
    REPO_ROOT, REGISTRY, ROLE, change_effort_only, change_fallback_only, change_pin, edit_registry,
    make_repo, out, run_commit_msg,
)


def drop_min_pin(text):
    new, n = re.subn(r"\n    min_pin: \S+", "", text, count=1)
    assert n == 1
    return new


def widen_adjacent(text):
    new = text.replace("    fable: [opus]", "    fable: [opus, haiku]", 1)
    assert new != text
    return new


def narrow_adjacent(text):
    """A fallback_policy edit that does NOT touch I7: haiku may no longer fall to sonnet."""
    new = text.replace("    haiku: [sonnet]", "    haiku: []", 1)
    assert new != text
    return new


def change_effort(text):
    cfg = REGISTRY["roles"][ROLE]
    new = text.replace(f"    effort: {cfg['effort']}\n    fallback: [{', '.join(cfg['fallback'])}]",
                       f"    effort: {'low' if cfg['effort'] != 'low' else 'max'}\n"
                       f"    fallback: [{', '.join(cfg['fallback'])}]", 1)
    assert new != text
    return new


# model, fallback, effort, min_pin: the former fingerprint. Free to change without a trailer.
# fallback_policy is no longer wholly free: widening fable's adjacency to haiku violates the
# fixed I7 floor (see test_widening_fable_adjacency_to_haiku_fails_the_registry_check).
POLICY_CHANGES = [("model", change_pin), ("fallback_list", change_fallback_only),
                  ("effort", change_effort), ("min_pin", drop_min_pin),
                  ("fallback_policy_other", narrow_adjacent)]
IDS = [p[0] for p in POLICY_CHANGES]


@pytest.mark.parametrize("name,mutate", POLICY_CHANGES + [("fallback_policy_widen", widen_adjacent)], ids=IDS + ["fallback_policy_widen"])
def test_policy_change_without_trailer_passes_the_commit_msg_hook(tmp_path, name, mutate):
    """The hook never fails on a policy edit (even I7-violating ones: models.py check is the gate)."""
    repo = make_repo(tmp_path)
    edit_registry(repo, mutate)
    r = run_commit_msg(repo, "chore: tweak registry\n")
    assert r.returncode == 0, out(r)
    assert "Approved-By" not in out(r) and "pin_history" not in out(r)
    assert "Registry policy changed" in out(r), out(r)  # informational note, never a failure


NOTE_EXPECTS = {
    "model": "roles.engineer.model", "fallback_list": "roles.engineer.fallback",
    "effort": "roles.engineer.effort", "min_pin": "families.", "fallback_policy_other": "fallback_policy",
}


@pytest.mark.parametrize("name", list(NOTE_EXPECTS))
def test_commit_msg_note_names_what_changed(tmp_path, name):
    repo = make_repo(tmp_path)
    edit_registry(repo, dict(POLICY_CHANGES)[name])
    r = run_commit_msg(repo, "chore: tweak registry\n")
    assert r.returncode == 0, out(r)
    assert NOTE_EXPECTS[name] in out(r), out(r)
    assert "Approved-By" not in out(r) and "approval" not in out(r).lower()


def test_commit_msg_is_silent_about_policy_when_nothing_changed(tmp_path):
    repo = make_repo(tmp_path)
    edit_registry(repo, change_effort_only)
    r = run_commit_msg(repo, "chore: comment\n")
    assert r.returncode == 0 and "Registry policy changed" not in out(r), out(r)


def _check(repo):
    return subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "models.py"), "--root", str(repo), "check"],
                          capture_output=True, text=True)


def test_widening_fable_adjacency_to_haiku_fails_the_registry_check(tmp_path):
    """I7 is a fixed floor: the mutable policy cannot widen it (tests/test_models_registry.py has the rest)."""
    repo = make_repo(tmp_path)
    edit_registry(repo, widen_adjacent)
    r = _check(repo)
    assert r.returncode == 1 and "I7" in out(r), out(r)


@pytest.mark.parametrize("name,mutate", POLICY_CHANGES, ids=IDS)
def test_policy_change_without_trailer_is_clean_for_the_scanner(tmp_path, name, mutate):
    repo = scan_repo(tmp_path)
    edit_registry(repo, mutate)
    commit(repo, "chore: tweak registry")
    r = run_scan(repo, "--strict")
    assert is_clean(r), out(r)


@pytest.mark.parametrize("mutate", [edit_old_history, delete_history_entry, reorder_history],
                         ids=lambda f: f.__name__)
def test_history_rewrite_warns_in_hook_and_scanner_but_never_fails(tmp_path, mutate):
    (tmp_path / "hook").mkdir()
    repo = make_repo(tmp_path / "hook")
    edit_registry(repo, mutate)
    h = run_commit_msg(repo, "chore: history\n")
    assert h.returncode == 0, out(h)
    assert "pin_history" in out(h) and "append-only" in out(h)

    (tmp_path / "scan").mkdir()
    srepo = scan_repo(tmp_path / "scan")
    edit_registry(srepo, mutate)
    commit(srepo, "chore: history")
    s = run_scan(srepo)
    assert s.returncode == 0 and "pin_history" in s.stdout


def test_history_append_is_silent_in_hook(tmp_path):
    repo = make_repo(tmp_path)
    edit_registry(repo, append_history)
    r = run_commit_msg(repo, "chore: record history\n")
    assert r.returncode == 0 and "pin_history" not in out(r), out(r)


def test_comment_only_edit_is_silent(tmp_path):
    repo = make_repo(tmp_path)
    edit_registry(repo, change_effort_only)
    r = run_commit_msg(repo, "chore: comment\n")
    assert r.returncode == 0 and "pin_history" not in out(r), out(r)
