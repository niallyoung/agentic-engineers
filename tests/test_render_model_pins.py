#!/usr/bin/env python3
"""Render-time model pinning: every harness renderer takes its model IDs from
config/models.yaml via scripts/models.py (WP3 of the model-pin work).

Covers:
  * Claude Code agents + settings.json carry EXACT pinned IDs (no floating alias),
    with AGENTIC_CLAUDE_MODEL_RENDER=alias as the explicit reversible override
  * MODEL_MARKER semantics: managed value migrates (old alias / old pin), a
    user-chosen value (or a legacy alias with no marker) is never overwritten
  * --status reports a stale managed value
  * Copilot settings.json / agents use the registry's Copilot ID, never "sonnet"
  * OpenCode: pin used as-is offline; absent pin walks the fallback chain with a
    visible WARN and a model-resolution.json record

Every render runs against a throwaway copy of the repo and a temp harness dir.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS = REPO_ROOT / "scripts" / "models.py"
ROLES = (
    "engineer", "orchestrator", "lead-engineer", "quality-engineer",
    "senior-engineer", "model-engineer", "security-engineer", "principal-engineer",
)
ALIASES = {"haiku", "sonnet", "opus", "fable"}


def registry_id(role: str, harness: str) -> str:
    out = subprocess.run(
        ["python3", str(MODELS), "get", role, "--harness", harness],
        capture_output=True, text=True, check=True, cwd=REPO_ROOT,
    )
    return out.stdout.strip()


@pytest.fixture(scope="module")
def repo(tmp_path_factory):
    """Throwaway repo copy so renders never touch the real git config or dist/."""
    dst = tmp_path_factory.mktemp("pins") / "repo"
    shutil.copytree(
        REPO_ROOT, dst,
        ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", ".pytest_cache", "*.pyc", "node_modules"),
    )
    subprocess.run(["git", "init", "-q", str(dst)], check=True)
    return dst


def run(script, repo, target, *extra, env=None):
    e = {**os.environ, "NO_COLOR": "1", **(env or {})}
    e.pop("AGENTIC_CLAUDE_MODEL_RENDER", None) if not (env and "AGENTIC_CLAUDE_MODEL_RENDER" in env) else None
    return subprocess.run(
        ["bash", str(repo / "renderer" / "scripts" / script), str(repo), str(target), *extra],
        capture_output=True, text=True, env=e,
    )


def fm_model(path: Path) -> str:
    in_fm = False
    for i, line in enumerate(path.read_text().splitlines()):
        if i == 0 and line == "---":
            in_fm = True
            continue
        if in_fm and line == "---":
            break
        if in_fm and line.startswith("model:"):
            return line.split(":", 1)[1].strip()
    return ""


def settings_model(claude: Path):
    f = claude / "settings.json"
    return json.loads(f.read_text()).get("model") if f.exists() else None


# --------------------------------------------------------------------------- #
# Claude Code
# --------------------------------------------------------------------------- #

class TestClaudePinnedIds:
    def test_every_role_is_the_exact_registry_pin(self, repo, tmp_path):
        r = run("render-claude.sh", repo, tmp_path / "c")
        assert r.returncode == 0, r.stderr
        for role in ROLES:
            got = fm_model(tmp_path / "c" / "agents" / f"{role}.md")
            assert got == registry_id(role, "claude"), role
            assert got not in ALIASES, f"{role} rendered a floating alias"

    def test_settings_default_is_orchestrator_pin(self, repo, tmp_path):
        run("render-claude.sh", repo, tmp_path / "c")
        assert settings_model(tmp_path / "c") == registry_id("orchestrator", "claude")

    def test_alias_override_is_explicit_and_reversible(self, repo, tmp_path):
        r = run("render-claude.sh", repo, tmp_path / "c", env={"AGENTIC_CLAUDE_MODEL_RENDER": "alias"})
        assert r.returncode == 0, r.stderr
        for role in ROLES:
            assert fm_model(tmp_path / "c" / "agents" / f"{role}.md") in ALIASES, role
        assert settings_model(tmp_path / "c") in ALIASES

    def test_unknown_role_is_skipped_not_guessed(self, repo):
        out = subprocess.run(
            ["bash", "-c", f'REPO_ROOT="{repo}"; source "{repo}/renderer/lib/render-lib.sh"; map_model no-such-role claude'],
            capture_output=True, text=True,
        )
        assert out.stdout.strip() == "" and out.returncode != 0


class TestMarkerSemantics:
    """settings.json "model" ownership, governed by .agentic-engine-claude-model."""

    @staticmethod
    def seed(claude: Path, model, marker):
        claude.mkdir(parents=True, exist_ok=True)
        data = {} if model is None else {"model": model}
        (claude / "settings.json").write_text(json.dumps(data))
        if marker is not None:
            (claude / ".agentic-engine-claude-model").write_text(marker + "\n")

    def test_fresh_install_sets_and_records_marker(self, repo, tmp_path):
        run("render-claude.sh", repo, tmp_path / "c")
        pin = registry_id("orchestrator", "claude")
        assert settings_model(tmp_path / "c") == pin
        assert (tmp_path / "c" / ".agentic-engine-claude-model").read_text().strip() == pin

    @pytest.mark.parametrize("old", ["sonnet", "claude-sonnet-5", "claude-opus-4-8"])
    def test_managed_old_value_migrates_to_pin(self, repo, tmp_path, old):
        """An installer-written alias or prior pin (value == marker) is updated."""
        c = tmp_path / "c"
        self.seed(c, old, old)
        run("render-claude.sh", repo, c)
        pin = registry_id("orchestrator", "claude")
        assert settings_model(c) == pin
        assert (c / ".agentic-engine-claude-model").read_text().strip() == pin

    def test_user_chosen_value_is_preserved(self, repo, tmp_path):
        c = tmp_path / "c"
        self.seed(c, "opus", "sonnet")  # differs from marker => user-chosen
        r = run("render-claude.sh", repo, c)
        assert settings_model(c) == "opus"
        assert "Keeping your existing session model" in r.stdout

    def test_legacy_alias_without_marker_is_user_chosen(self, repo, tmp_path):
        c = tmp_path / "c"
        self.seed(c, "sonnet", None)
        run("render-claude.sh", repo, c)
        assert settings_model(c) == "sonnet"

    def test_absent_key_stays_absent(self, repo, tmp_path):
        c = tmp_path / "c"
        self.seed(c, None, None)
        run("render-claude.sh", repo, c)
        assert settings_model(c) is None

    def test_status_reports_stale_managed_value(self, repo, tmp_path):
        c = tmp_path / "c"
        self.seed(c, "sonnet", "sonnet")
        r = run("render-claude.sh", repo, c, "--status")
        assert "stale managed value 'sonnet'" in r.stdout
        assert registry_id("orchestrator", "claude") in r.stdout

    def test_status_clean_after_install_and_user_value_not_flagged(self, repo, tmp_path):
        c = tmp_path / "c"
        run("render-claude.sh", repo, c)
        assert "stale managed value" not in run("render-claude.sh", repo, c, "--status").stdout
        c2 = tmp_path / "c2"
        self.seed(c2, "opus", "sonnet")
        assert "stale managed value" not in run("render-claude.sh", repo, c2, "--status").stdout


# --------------------------------------------------------------------------- #
# Copilot
# --------------------------------------------------------------------------- #

class TestCopilot:
    def test_settings_uses_registry_id_not_alias(self, repo, tmp_path):
        r = run("render-copilot.sh", repo, tmp_path / "p")
        assert r.returncode == 0, r.stderr
        data = json.loads((tmp_path / "p" / "settings.json").read_text())
        assert data["model"] == registry_id("orchestrator", "copilot")
        assert data["model"] not in ALIASES

    def test_agent_frontmatter_uses_registry_id(self, repo, tmp_path):
        run("render-copilot.sh", repo, tmp_path / "p")
        for role in ROLES:
            assert fm_model(tmp_path / "p" / "agents" / f"{role}-agent.agent.md") == registry_id(role, "copilot"), role


# --------------------------------------------------------------------------- #
# OpenCode
# --------------------------------------------------------------------------- #

class TestOpenCode:
    def test_offline_renders_the_pin(self, repo, tmp_path):
        r = run("render-opencode.sh", repo, tmp_path / "o",
                env={"OPENCODE_PROVIDER": "anthropic", "OPENCODE_MODELS_CACHE": str(tmp_path / "none.json")})
        assert r.returncode == 0, r.stderr
        for role in ROLES:
            assert fm_model(tmp_path / "o" / "agents" / f"{role}.md") == "anthropic/" + registry_id(role, "opencode"), role
        assert "model-fallback" not in r.stderr

    def test_absent_pin_falls_back_loudly_and_records(self, repo, tmp_path):
        # Provider cache offering only each role's declared fallback(s): pins are absent.
        cache = tmp_path / "cache.json"
        have = {registry_id("engineer", "opencode"), "claude-sonnet-5", "claude-opus-4-8"}
        cache.write_text(json.dumps({"anthropic": {"models": {m: {} for m in have}}}))
        r = run("render-opencode.sh", repo, tmp_path / "o",
                env={"OPENCODE_PROVIDER": "anthropic", "OPENCODE_MODELS_CACHE": str(cache)})
        assert r.returncode == 0, r.stderr
        # Visible WARN on stderr, never silent.
        assert "WARN model-fallback role=lead-engineer" in r.stderr
        assert "WARN model-fallback role=principal-engineer" in r.stderr
        assert fm_model(tmp_path / "o" / "agents" / "lead-engineer.md") == "anthropic/claude-sonnet-5"
        # Principal's first fallback (claude-opus-5) is also absent, so it walks to the second.
        assert fm_model(tmp_path / "o" / "agents" / "principal-engineer.md") == "anthropic/claude-opus-4-8"
        # The un-pinned engineer is available, so no fallback for it.
        assert fm_model(tmp_path / "o" / "agents" / "engineer.md") == "anthropic/" + registry_id("engineer", "opencode")
        rec = json.loads((repo / "dist" / "opencode" / "model-resolution.json").read_text())["roles"]
        assert rec["lead-engineer"]["fallback_used"] is True
        assert rec["lead-engineer"]["used"] == "claude-sonnet-5"
        assert rec["principal-engineer"]["used"] == "claude-opus-4.8"
        assert rec["engineer"]["fallback_used"] is False

    def test_nothing_available_skips_agent_with_warning(self, repo, tmp_path):
        cache = tmp_path / "cache.json"
        cache.write_text(json.dumps({"anthropic": {"models": {"some-other-model": {}}}}))
        r = run("render-opencode.sh", repo, tmp_path / "o",
                env={"OPENCODE_PROVIDER": "anthropic", "OPENCODE_MODELS_CACHE": str(cache)})
        assert "ERROR model-unresolved" in r.stderr
        assert not (tmp_path / "o" / "agents" / "engineer.md").exists()
