"""`make fresh-install-claude`: wipe the framework's managed Claude files, then install clean.

Dog-food regression: after `uninstall-claude` the installer used to leave an empty
settings.json behind. The next install then read "file exists, no model key" as the
operator deliberately inheriting their account default and never restored the
Orchestrator pin. A fresh install must give the same result as a first install.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def make(target, destdir, **env):
    return subprocess.run(
        ["make", "-C", str(REPO_ROOT), target, f"DESTDIR={destdir}", "BACKUP=never"],
        capture_output=True, text=True, timeout=240, env={**os.environ, **env},
    )


def pin():
    r = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "models.py"), "get", "orchestrator",
         "--harness", "claude", "--field", "id"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def settings(dest):
    return json.loads((dest / ".claude" / "settings.json").read_text())


@pytest.fixture
def dest(tmp_path):
    d = tmp_path / "home"
    d.mkdir()
    return d


class TestTarget:
    def test_target_exists_and_is_listed_in_help(self):
        out = subprocess.run(["make", "-C", str(REPO_ROOT), "help"], capture_output=True, text=True).stdout
        assert "fresh-install-claude" in out

    def test_target_is_phony(self):
        text = (REPO_ROOT / "Makefile").read_text()
        phony = text.split(".PHONY:", 1)[1].split("\n\n", 1)[0]
        assert "fresh-install-claude" in phony


class TestFreshInstall:
    def test_fresh_install_from_nothing_pins_the_orchestrator(self, dest):
        r = make("fresh-install-claude", dest)
        assert r.returncode == 0, r.stdout + r.stderr
        assert settings(dest)["model"] == pin()

    def test_fresh_install_over_an_existing_install_restores_the_pin(self, dest):
        assert make("install-claude", dest).returncode == 0
        r = make("fresh-install-claude", dest)
        assert r.returncode == 0, r.stdout + r.stderr
        assert settings(dest)["model"] == pin()
        assert len(list((dest / ".claude" / "agents").glob("*.md"))) == 8

    def test_uninstall_leaves_no_empty_settings_file_behind(self, dest):
        """Root cause of the dog-food finding: a leftover {} read as 'operator owns the model'."""
        assert make("install-claude", dest).returncode == 0
        assert make("uninstall-claude", dest).returncode == 0
        assert not (dest / ".claude" / "settings.json").exists()

    def test_install_after_uninstall_equals_a_first_install(self, dest):
        assert make("install-claude", dest).returncode == 0
        first = settings(dest)
        assert make("uninstall-claude", dest).returncode == 0
        assert make("install-claude", dest).returncode == 0
        assert settings(dest) == first

    def test_foreign_settings_keys_survive_a_fresh_install(self, dest):
        assert make("install-claude", dest).returncode == 0
        data = settings(dest)
        data["theme"] = "dark"
        (dest / ".claude" / "settings.json").write_text(json.dumps(data))
        r = make("fresh-install-claude", dest)
        assert r.returncode == 0, r.stdout + r.stderr
        after = settings(dest)
        assert after["theme"] == "dark"
        assert after["model"] == pin()

    def test_user_chosen_model_survives_a_fresh_install(self, dest):
        (dest / ".claude").mkdir()
        (dest / ".claude" / "settings.json").write_text(json.dumps({"model": "opus"}))
        r = make("fresh-install-claude", dest)
        assert r.returncode == 0, r.stdout + r.stderr
        assert settings(dest)["model"] == "opus"

    def test_foreign_agents_and_skills_survive_a_fresh_install(self, dest):
        assert make("install-claude", dest).returncode == 0
        (dest / ".claude" / "agents" / "my-agent.md").write_text("mine\n")
        (dest / ".claude" / "skills" / "my-skill").mkdir()
        (dest / ".claude" / "skills" / "my-skill" / "SKILL.md").write_text("mine\n")
        r = make("fresh-install-claude", dest)
        assert r.returncode == 0, r.stdout + r.stderr
        assert (dest / ".claude" / "agents" / "my-agent.md").read_text() == "mine\n"
        assert (dest / ".claude" / "skills" / "my-skill" / "SKILL.md").exists()

    def test_fresh_install_replaces_a_stale_managed_agent(self, dest):
        assert make("install-claude", dest).returncode == 0
        agent = dest / ".claude" / "agents" / "engineer.md"
        agent.write_text(agent.read_text() + "\nSTALE LOCAL EDIT\n")
        assert make("fresh-install-claude", dest).returncode == 0
        assert "STALE LOCAL EDIT" not in agent.read_text()
