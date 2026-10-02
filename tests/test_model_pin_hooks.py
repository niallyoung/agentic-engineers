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
