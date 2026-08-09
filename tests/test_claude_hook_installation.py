"""
Tests for render-claude.sh's DELEGATE/HANDBACK protocol-guard hook
installation: the PreToolUse hook (renderer/scripts/claude-delegate-guard.py)
must be installed into a fresh $CLAUDE/hooks/ directory and wired into
$CLAUDE/settings.json non-destructively, idempotently, and removably.

These tests always render into a temp directory (never the developer's real
~/.claude), matching the project convention used by tests/claude/conftest.py
and the DELEGATE that commissioned this hook: "validate via dist/ or a temp
dir instead" of re-running install against a live ~/.claude.
"""

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
RENDER_CLAUDE = REPO_ROOT / "renderer" / "scripts" / "render-claude.sh"
GUARD_SCRIPT = REPO_ROOT / "renderer" / "scripts" / "claude-delegate-guard.py"


def _render(dest, mode=None, timeout=60):
    cmd = ["bash", str(RENDER_CLAUDE), str(REPO_ROOT), str(dest)]
    if mode:
        cmd.append(mode)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _settings(dest):
    settings_file = Path(dest) / "settings.json"
    if not settings_file.exists():
        return {}
    return json.loads(settings_file.read_text())


def _our_pretooluse_entries(settings):
    entries = settings.get("hooks", {}).get("PreToolUse", [])
    return [
        e for e in entries
        if any("claude-delegate-guard.py" in h.get("command", "") for h in e.get("hooks", []))
    ]


class TestGuardScriptSource:
    def test_guard_script_exists(self):
        assert GUARD_SCRIPT.exists()

    def test_guard_script_executable(self):
        import os
        assert os.access(GUARD_SCRIPT, os.X_OK)


class TestFreshInstall:
    def test_install_writes_hook_file(self, tmp_path):
        result = _render(tmp_path)
        assert result.returncode == 0, result.stderr
        hook_file = tmp_path / "hooks" / "claude-delegate-guard.py"
        assert hook_file.exists()
        assert hook_file.read_text() == GUARD_SCRIPT.read_text()

    def test_install_writes_marker(self, tmp_path):
        _render(tmp_path)
        assert (tmp_path / "hooks" / ".agentic-engine-claude").exists()

    def test_install_hook_file_is_executable(self, tmp_path):
        import os
        _render(tmp_path)
        hook_file = tmp_path / "hooks" / "claude-delegate-guard.py"
        assert os.access(hook_file, os.X_OK)

    def test_install_wires_settings_json(self, tmp_path):
        _render(tmp_path)
        settings = _settings(tmp_path)
        entries = _our_pretooluse_entries(settings)
        assert len(entries) == 1
        assert entries[0]["matcher"] in ("Task|Agent", "Agent|Task")

    def test_install_hook_points_at_absolute_installed_path(self, tmp_path):
        _render(tmp_path)
        settings = _settings(tmp_path)
        entries = _our_pretooluse_entries(settings)
        command = entries[0]["hooks"][0]["command"]
        assert str(tmp_path) in command
        assert command.endswith("hooks/claude-delegate-guard.py")


class TestIdempotency:
    def test_install_twice_does_not_duplicate_entry(self, tmp_path):
        _render(tmp_path)
        _render(tmp_path)
        settings = _settings(tmp_path)
        entries = _our_pretooluse_entries(settings)
        assert len(entries) == 1

    def test_install_twice_settings_still_valid_json(self, tmp_path):
        _render(tmp_path)
        result = _render(tmp_path)
        assert result.returncode == 0, result.stderr
        # _settings() itself calls json.loads — raises on invalid JSON
        _settings(tmp_path)


class TestNonDestructiveMerge:
    def test_preserves_unrelated_top_level_keys(self, tmp_path):
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / "settings.json").write_text(json.dumps({
            "editorMode": "vim",
            "statusLine": {"type": "command", "command": "bash ~/foo.sh"},
        }))
        _render(tmp_path)
        settings = _settings(tmp_path)
        assert settings["editorMode"] == "vim"
        assert settings["statusLine"]["command"] == "bash ~/foo.sh"

    def test_preserves_foreign_pretooluse_entries(self, tmp_path):
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / "settings.json").write_text(json.dumps({
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Bash", "hooks": [{"type": "command", "command": "~/my-own-guard.sh"}]}
                ]
            }
        }))
        _render(tmp_path)
        settings = _settings(tmp_path)
        entries = settings["hooks"]["PreToolUse"]
        matchers = {e["matcher"] for e in entries}
        assert "Bash" in matchers
        assert any(m in ("Task|Agent", "Agent|Task") for m in matchers)
        assert len(entries) == 2

    def test_preserves_foreign_hook_event_names(self, tmp_path):
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / "settings.json").write_text(json.dumps({
            "hooks": {
                "SessionStart": [{"hooks": [{"type": "command", "command": "echo hi"}]}],
            }
        }))
        _render(tmp_path)
        settings = _settings(tmp_path)
        assert "SessionStart" in settings["hooks"]
        assert settings["hooks"]["SessionStart"][0]["hooks"][0]["command"] == "echo hi"


class TestUninstall:
    def test_uninstall_removes_hook_file(self, tmp_path):
        _render(tmp_path)
        result = _render(tmp_path, "--uninstall")
        assert result.returncode == 0, result.stderr
        assert not (tmp_path / "hooks" / "claude-delegate-guard.py").exists()

    def test_uninstall_removes_our_pretooluse_entry(self, tmp_path):
        _render(tmp_path)
        _render(tmp_path, "--uninstall")
        settings = _settings(tmp_path)
        assert _our_pretooluse_entries(settings) == []

    def test_uninstall_preserves_foreign_pretooluse_entries(self, tmp_path):
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / "settings.json").write_text(json.dumps({
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Bash", "hooks": [{"type": "command", "command": "~/my-own-guard.sh"}]}
                ]
            }
        }))
        _render(tmp_path)
        _render(tmp_path, "--uninstall")
        settings = _settings(tmp_path)
        entries = settings["hooks"]["PreToolUse"]
        assert len(entries) == 1
        assert entries[0]["matcher"] == "Bash"

    def test_uninstall_cleans_up_empty_hooks_key(self, tmp_path):
        _render(tmp_path)
        _render(tmp_path, "--uninstall")
        settings = _settings(tmp_path)
        # Nothing else populated "hooks" in this fixture, so it should be
        # fully removed rather than left behind as {}.
        assert "hooks" not in settings

    def test_uninstall_does_not_remove_foreign_hook_file(self, tmp_path):
        _render(tmp_path)
        # Simulate a user dropping their own file at the same path after our
        # marker was removed — uninstall must never delete a foreign file.
        hooks_dir = tmp_path / "hooks"
        marker = hooks_dir / ".agentic-engine-claude"
        marker.unlink()
        _render(tmp_path, "--uninstall")
        assert (hooks_dir / "claude-delegate-guard.py").exists()


class TestStatus:
    def test_status_reports_missing_before_install(self, tmp_path):
        tmp_path.mkdir(parents=True, exist_ok=True)
        result = _render(tmp_path, "--status")
        assert result.returncode == 0
        assert "not installed" in result.stdout
        assert "not wired" in result.stdout

    def test_status_reports_installed_after_install(self, tmp_path):
        _render(tmp_path)
        result = _render(tmp_path, "--status")
        assert result.returncode == 0
        assert "hook claude-delegate-guard.py" in result.stdout
        assert "wired" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
