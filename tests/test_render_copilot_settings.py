#!/usr/bin/env python3
"""Copilot settings.json "model" ownership (invariant I4, Principal finding C2).

render-copilot.sh must give Copilot the SAME ownership semantics as
render-claude.sh (see TestMarkerSemantics / TestNonStrictJsonSettings in
test_render_model_pins.py): the installer never overwrites a model the user
chose, never drops other keys, never clobbers a file that is not strict JSON,
and uninstall removes only what the installer wrote.

Ownership is recorded in $COPILOT/.agentic-engine-copilot-model.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS = REPO_ROOT / "scripts" / "models.py"
MARKER = ".agentic-engine-copilot-model"


def registry_id(role: str, harness: str) -> str:
    out = subprocess.run(
        ["python3", str(MODELS), "get", role, "--harness", harness],
        capture_output=True, text=True, check=True, cwd=REPO_ROOT,
    )
    return out.stdout.strip()


@pytest.fixture(scope="module")
def repo(tmp_path_factory):
    dst = tmp_path_factory.mktemp("copilot-settings") / "repo"
    shutil.copytree(
        REPO_ROOT, dst,
        ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", ".pytest_cache", "*.pyc", "node_modules"),
    )
    subprocess.run(["git", "init", "-q", str(dst)], check=True)
    return dst


def run(repo, target, *extra, env=None):
    e = {**os.environ, "NO_COLOR": "1", **(env or {})}
    return subprocess.run(
        ["bash", str(repo / "renderer" / "scripts" / "render-copilot.sh"), str(repo), str(target), *extra],
        capture_output=True, text=True, env=e,
    )


def seed(p: Path, model, marker, extra=None):
    p.mkdir(parents=True, exist_ok=True)
    data = dict(extra or {})
    if model is not None:
        data["model"] = model
    (p / "settings.json").write_text(json.dumps(data))
    if marker is not None:
        (p / MARKER).write_text(marker + "\n")


def load(p: Path):
    return json.loads((p / "settings.json").read_text())


PIN = registry_id("orchestrator", "copilot")


class TestInstall:
    def test_fresh_install_sets_pin_and_records_marker(self, repo, tmp_path):
        p = tmp_path / "p"
        r = run(repo, p)
        assert r.returncode == 0, r.stderr
        assert load(p)["model"] == PIN
        assert (p / MARKER).read_text().strip() == PIN

    @pytest.mark.parametrize("old", ["sonnet", "gpt-old", "claude-sonnet-4.5"])
    def test_managed_value_refreshes_to_pin(self, repo, tmp_path, old):
        p = tmp_path / "p"
        seed(p, old, old)
        r = run(repo, p)
        assert r.returncode == 0, r.stderr
        assert load(p)["model"] == PIN
        assert (p / MARKER).read_text().strip() == PIN

    def test_user_chosen_value_is_kept_and_reported(self, repo, tmp_path):
        p = tmp_path / "p"
        seed(p, "my-own-model", "something-else")
        r = run(repo, p)
        assert load(p)["model"] == "my-own-model"
        assert "Keeping your existing session model (my-own-model)" in r.stdout
        assert (p / MARKER).read_text().strip() == "something-else"

    def test_value_without_marker_is_user_chosen(self, repo, tmp_path):
        p = tmp_path / "p"
        seed(p, "sonnet", None)
        run(repo, p)
        assert load(p)["model"] == "sonnet"
        assert not (p / MARKER).exists()

    def test_absent_key_stays_absent(self, repo, tmp_path):
        p = tmp_path / "p"
        seed(p, None, None, {"theme": "dark"})
        r = run(repo, p)
        assert "model" not in load(p)
        assert "Leaving your session model unset" in r.stdout
        assert not (p / MARKER).exists()

    def test_foreign_keys_preserved_on_refresh(self, repo, tmp_path):
        p = tmp_path / "p"
        extra = {"theme": "dark", "trusted_folders": ["/a", "/b"], "nested": {"k": [1, 2]}}
        seed(p, "old", "old", extra)
        run(repo, p)
        data = load(p)
        assert data["model"] == PIN
        for k, v in extra.items():
            assert data[k] == v

    def test_foreign_keys_preserved_when_model_user_chosen(self, repo, tmp_path):
        p = tmp_path / "p"
        extra = {"theme": "dark", "trusted_folders": ["/a"]}
        seed(p, "mine", None, extra)
        run(repo, p)
        assert load(p) == {**extra, "model": "mine"}

    def test_install_is_idempotent(self, repo, tmp_path):
        p = tmp_path / "p"
        run(repo, p)
        first = (p / "settings.json").read_bytes()
        run(repo, p)
        assert (p / "settings.json").read_bytes() == first


class TestNonStrictJson:
    JSONC = '// mine\n{\n  "theme": "dark",\n  "model": "opus", // my choice\n}\n'

    @pytest.mark.parametrize("content", [
        JSONC, '{"theme": "dark", "model": "x",}', '{"theme": "dark"', '[1, 2]',
    ], ids=["jsonc", "trailing-comma", "truncated", "non-object"])
    def test_install_leaves_invalid_json_byte_identical_and_warns(self, repo, tmp_path, content):
        p = tmp_path / "p"
        p.mkdir()
        raw = content.encode()
        (p / "settings.json").write_bytes(raw)
        r = run(repo, p)
        assert r.returncode == 0, r.stderr
        assert (p / "settings.json").read_bytes() == raw
        out = r.stdout + r.stderr
        assert "not valid JSON" in out and "left untouched" in out
        assert not (p / MARKER).exists()
        assert (p / "agents").is_dir()  # rest of the install still happened

    def test_uninstall_leaves_invalid_json_byte_identical(self, repo, tmp_path):
        p = tmp_path / "p"
        p.mkdir()
        raw = self.JSONC.encode()
        (p / "settings.json").write_bytes(raw)
        (p / MARKER).write_text("opus\n")
        r = run(repo, p, "--uninstall")
        assert r.returncode == 0, r.stderr
        assert (p / "settings.json").read_bytes() == raw

    @pytest.mark.parametrize("content", ["", "  \n"], ids=["empty", "whitespace"])
    def test_empty_file_is_not_a_crash_and_gets_no_model(self, repo, tmp_path, content):
        """Mirrors Claude: an existing (even empty) settings.json is the user's, so no model is added."""
        p = tmp_path / "p"
        p.mkdir()
        (p / "settings.json").write_text(content)
        r = run(repo, p)
        assert r.returncode == 0, r.stderr
        assert (p / "settings.json").read_text() == content
        assert not (p / MARKER).exists()


class TestUninstall:
    def test_removes_managed_model_marker_and_empty_file(self, repo, tmp_path):
        p = tmp_path / "p"
        run(repo, p)
        r = run(repo, p, "--uninstall")
        assert r.returncode == 0, r.stderr
        assert not (p / MARKER).exists()
        assert not (p / "settings.json").exists()

    def test_keeps_foreign_keys_and_file(self, repo, tmp_path):
        p = tmp_path / "p"
        run(repo, p)
        data = load(p)
        data["theme"] = "dark"
        (p / "settings.json").write_text(json.dumps(data))
        run(repo, p, "--uninstall")
        after = load(p)
        assert "model" not in after
        assert after["theme"] == "dark"
        assert not (p / MARKER).exists()

    def test_user_chosen_model_kept_and_reported(self, repo, tmp_path):
        p = tmp_path / "p"
        seed(p, "mine", "other")
        r = run(repo, p, "--uninstall")
        assert load(p)["model"] == "mine"
        assert "keeping session model (mine)" in r.stdout
        assert not (p / MARKER).exists()

    def test_value_without_marker_kept(self, repo, tmp_path):
        p = tmp_path / "p"
        seed(p, "sonnet", None)
        run(repo, p, "--uninstall")
        assert load(p)["model"] == "sonnet"

    def test_file_with_other_content_not_removed(self, repo, tmp_path):
        p = tmp_path / "p"
        seed(p, "x", "x", {"theme": "dark"})
        run(repo, p, "--uninstall")
        assert load(p) == {"theme": "dark"}

    def test_keep_model_env_leaves_model_and_marker(self, repo, tmp_path):
        p = tmp_path / "p"
        run(repo, p)
        r = run(repo, p, "--uninstall", env={"AGENTIC_KEEP_MODEL": "1"})
        assert load(p)["model"] == PIN
        assert (p / MARKER).read_text().strip() == PIN
        assert "keeping session model and ownership marker" in r.stdout

    def test_uninstall_then_install_equals_first_install(self, repo, tmp_path):
        p = tmp_path / "p"
        run(repo, p)
        first = load(p)
        run(repo, p, "--uninstall")
        run(repo, p)
        assert load(p) == first
        assert (p / MARKER).read_text().strip() == PIN
