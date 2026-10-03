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

    def test_fallback_only_change_needs_no_trailer(self, tmp_path):
        repo = make_repo(tmp_path)
        edit_registry(repo, change_fallback_only)
        r = run_commit_msg(repo, "chore: change a fallback list only\n")
        assert r.returncode == 0, out(r)
        assert "Model-Pin-Approved-By" not in out(r)

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
    @staticmethod
    def scan_repo(tmp_path):
        """Scratch repo: seed commit on a fake origin/main, scripts/ alongside."""
        repo = make_repo(tmp_path)
        (repo / "scripts").symlink_to(REPO_ROOT / "scripts")
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        return repo

    @staticmethod
    def run_scan(repo, **env):
        return subprocess.run(["bash", "-e", "-c", _scan_step_run()], cwd=repo, capture_output=True,
                              text=True, timeout=60, env={**os.environ, **env})

    def commit(self, repo, message):
        git(repo, "commit", "-q", "-m", message)

    def test_pin_commit_without_trailer_fails_the_scan(self, tmp_path):
        repo = self.scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        self.commit(repo, SUBJECT)
        r = self.run_scan(repo)
        assert r.returncode == 1, out(r)
        assert ROLE in out(r) and "Model-Pin-Approved-By" in out(r)

    def test_pin_commit_with_trailer_passes(self, tmp_path):
        repo = self.scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        self.commit(repo, SUBJECT + "\n\nModel-Pin-Approved-By: Jane Doe")
        assert self.run_scan(repo).returncode == 0

    def test_empty_trailer_fails_the_scan(self, tmp_path):
        repo = self.scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        self.commit(repo, SUBJECT + "\n\nModel-Pin-Approved-By:   ")
        assert self.run_scan(repo).returncode == 1

    def test_amended_away_trailer_is_caught_even_though_the_hook_was_skipped(self, tmp_path):
        repo = self.scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        self.commit(repo, SUBJECT + "\n\nModel-Pin-Approved-By: Jane Doe")
        git(repo, "commit", "--amend", "-q", "-m", SUBJECT)  # hooks disabled == --no-verify
        assert self.run_scan(repo).returncode == 1

    def test_non_pin_registry_commit_and_unrelated_commit_pass(self, tmp_path):
        repo = self.scan_repo(tmp_path)
        edit_registry(repo, change_effort_only)
        self.commit(repo, "chore: comment-only registry edit")
        (repo / "x.txt").write_text("x")
        git(repo, "add", "x.txt")
        self.commit(repo, "chore: unrelated")
        assert self.run_scan(repo).returncode == 0

    def test_introducing_the_registry_is_not_a_pin_change(self, tmp_path):
        """Seeding config/models.yaml from nothing must not demand a trailer (a PR that
        adds the registry would otherwise fail on its own first commit), but the NEXT
        pin change without one must still be caught."""
        repo = make_repo(tmp_path, commit_registry=False)
        (repo / "README.md").write_text("x")
        git(repo, "add", "README.md")
        self.commit(repo, "chore: base without a registry")
        (repo / "scripts").symlink_to(REPO_ROOT / "scripts")
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(repo, "add", "config/models.yaml")
        self.commit(repo, "feat: introduce the model registry")  # no trailer, parent has no registry
        assert self.run_scan(repo).returncode == 0
        edit_registry(repo, change_pin)
        self.commit(repo, SUBJECT)
        r = self.run_scan(repo)
        assert r.returncode == 1, out(r)
        assert ROLE in out(r)

    def test_only_commits_after_base_are_scanned(self, tmp_path):
        repo = self.scan_repo(tmp_path)
        edit_registry(repo, change_pin)
        self.commit(repo, SUBJECT)  # unapproved pin change ...
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")  # ... already on main
        assert self.run_scan(repo).returncode == 0

    def test_missing_base_ref_skips_with_notice(self, tmp_path):
        repo = self.scan_repo(tmp_path)
        r = self.run_scan(repo, MODEL_PIN_SCAN_BASE="origin/does-not-exist")
        assert r.returncode == 0 and "skipping" in out(r)

    def test_untrusted_text_never_reaches_workflow_expressions(self):
        run = _scan_step_run()
        assert "${{" not in run


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
