"""Tests for .claude/hooks/session-start.sh, the Claude Code cloud-session
bootstrap (runs `make install-claude` so agents/skills exist in ~/.claude).

The hook is exercised for real, in a sandbox: PATH holds only stub executables
(make, apt-get, python3 and optionally rsync) that record their invocations,
HOME is an empty temp dir, and CLAUDE_CODE_REMOTE is set or removed explicitly
(the CI/dev sandbox itself may export CLAUDE_CODE_REMOTE=true, so it is never
inherited).
"""
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / ".claude" / "hooks" / "session-start.sh"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"

STUB_TEMPLATE = """#!/bin/bash
# stub {name}: record cwd + argv, optionally fail
printf '%s\\t%s\\n' "$PWD" "$*" >> "$STUB_LOG_DIR/{name}.log"
if [ -n "${{STUB_FAIL_{upper}:-}}" ]; then
  echo "{name}: simulated failure ({name} said no)" >&2
  exit 1
fi
exit 0
"""


@pytest.fixture
def sandbox(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    logs = tmp_path / "logs"
    logs.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    # Real tools the hook needs besides the stubs.
    for tool in ("sed", "cat", "printf", "date"):
        found = shutil.which(tool)
        if found and not (bin_dir / tool).exists():
            (bin_dir / tool).symlink_to(found)

    def stub(name):
        path = bin_dir / name
        path.write_text(STUB_TEMPLATE.format(name=name, upper=name.upper().replace("-", "_")))
        path.chmod(0o755)

    for name in ("make", "apt-get", "python3"):
        stub(name)
    return {"bin": bin_dir, "logs": logs, "home": home, "project": project, "stub": stub}


def run_hook(sb, remote="true", extra_env=None):
    env = {
        "PATH": str(sb["bin"]),
        "HOME": str(sb["home"]),
        "STUB_LOG_DIR": str(sb["logs"]),
        "CLAUDE_PROJECT_DIR": str(sb["project"]),
    }
    if remote is not None:  # None => variable genuinely unset (env is built from scratch)
        env["CLAUDE_CODE_REMOTE"] = remote
    env.update(extra_env or {})
    return subprocess.run(["/bin/bash", str(HOOK)], capture_output=True, text=True, env=env,
                          cwd=sb["home"], timeout=60)


def calls(sb, name):
    log = sb["logs"] / f"{name}.log"
    return log.read_text().splitlines() if log.exists() else []


class TestNotRemote:
    @pytest.mark.parametrize("remote", [None, "false", "", "TRUE", "1"])
    def test_non_remote_session_is_a_noop(self, sandbox, remote):
        before = sorted(p.name for p in sandbox["home"].rglob("*"))
        r = run_hook(sandbox, remote=remote)
        assert r.returncode == 0, r.stderr
        assert r.stdout == "" and r.stderr == ""
        for name in ("make", "apt-get", "python3"):
            assert calls(sandbox, name) == [], f"{name} must not run for CLAUDE_CODE_REMOTE={remote!r}"
        assert sorted(p.name for p in sandbox["home"].rglob("*")) == before

    def test_unset_really_means_unset_even_if_the_outer_env_is_remote(self, sandbox, monkeypatch):
        monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")  # as in this sandbox
        r = run_hook(sandbox, remote=None)  # env built from scratch: variable absent
        assert r.returncode == 0 and calls(sandbox, "make") == []


class TestRemote:
    def test_runs_make_install_claude_from_project_dir(self, sandbox):
        r = run_hook(sandbox)
        assert r.returncode == 0, r.stderr
        made = calls(sandbox, "make")
        assert len(made) == 1
        cwd, argv = made[0].split("\t")
        assert Path(cwd).resolve() == sandbox["project"].resolve()
        assert argv == "install-claude"

    def test_falls_back_to_cwd_when_project_dir_empty(self, sandbox):
        env = {"CLAUDE_PROJECT_DIR": ""}  # `:-` treats empty like unset
        # An empty value is "set" for ${VAR:-}: the hook must still land somewhere sane.
        r = run_hook(sandbox, extra_env=env)
        assert r.returncode == 0, r.stderr
        assert len(calls(sandbox, "make")) == 1

    def test_pyyaml_is_pinned_to_a_compatible_range(self, sandbox):
        run_hook(sandbox)
        pip = [c for c in calls(sandbox, "python3") if "-m pip install" in c]
        assert len(pip) == 1, calls(sandbox, "python3")
        assert "pyyaml>=6.0,<7" in pip[0]
        assert "pytest" in pip[0]

    def test_rsync_is_installed_only_when_missing(self, sandbox):
        r = run_hook(sandbox)  # no rsync on the stub PATH
        assert r.returncode == 0, r.stderr
        assert any("install" in c and "rsync" in c for c in calls(sandbox, "apt-get"))
        sandbox["stub"]("rsync")
        (sandbox["logs"] / "apt-get.log").unlink()
        run_hook(sandbox)
        assert calls(sandbox, "apt-get") == []

    def test_dependency_install_failure_is_non_fatal_but_loud(self, sandbox):
        r = run_hook(sandbox, extra_env={"STUB_FAIL_PYTHON3": "1", "STUB_FAIL_APT_GET": "1"})
        assert r.returncode == 0, r.stderr
        assert len(calls(sandbox, "make")) == 1, "install-claude must still run"
        assert "WARNING" in r.stderr
        assert "python deps" in r.stderr and "simulated failure" in r.stderr  # pip's own error is shown
        assert "rsync" in r.stderr

    def test_make_failure_propagates(self, sandbox):
        r = run_hook(sandbox, extra_env={"STUB_FAIL_MAKE": "1"})
        assert r.returncode != 0


class TestRegistration:
    def test_hook_file_is_executable(self):
        mode = HOOK.stat().st_mode
        assert mode & stat.S_IXUSR, "session-start.sh must be executable"
        assert os.access(HOOK, os.X_OK)

    def test_git_tracks_the_hook_as_executable(self):
        r = subprocess.run(["git", "ls-files", "-s", ".claude/hooks/session-start.sh"],
                           cwd=REPO_ROOT, capture_output=True, text=True)
        if not r.stdout.strip():
            pytest.skip("not a git checkout (or hook untracked)")
        assert r.stdout.startswith("100755"), r.stdout

    def test_settings_registers_hook_under_session_start(self):
        data = json.loads(SETTINGS.read_text())
        commands = [h["command"] for entry in data["hooks"]["SessionStart"] for h in entry["hooks"]]
        assert any(c.endswith(".claude/hooks/session-start.sh") for c in commands), commands
        assert all(c.startswith("$CLAUDE_PROJECT_DIR/") for c in commands if "session-start" in c)

    def test_shebang_and_strict_mode(self):
        text = HOOK.read_text()
        assert text.startswith("#!/bin/bash")
        assert "set -euo pipefail" in text
