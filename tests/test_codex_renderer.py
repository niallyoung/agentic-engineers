"""Codex renderer integration tests.

These tests exercise the Codex harness without touching the user's real
~/.codex or ~/.agents directories.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
RENDERER = REPO_ROOT / "renderer" / "scripts" / "render-codex.py"

EXPECTED_AGENTS = {
    "orchestrator",
    "engineer",
    "senior-engineer",
    "lead-engineer",
    "quality-engineer",
    "principal-engineer",
    "security-engineer",
    "model-engineer",
}


def source_skill_count() -> int:
    return len(
        [
            path
            for path in (REPO_ROOT / "src" / "skills").iterdir()
            if path.is_dir() and (path / "SKILL.md").exists()
        ]
    )


def toml_scalar(text: str, key: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"{key} = "):
            value = line.split("=", 1)[1].strip()
            return value.strip('"')
    raise AssertionError(f"missing TOML key {key!r}")


def run(*args: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(args),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
    return result


@pytest.fixture(scope="module")
def rendered_codex() -> Path:
    result = run("make", "render-codex", timeout=240)
    assert result.returncode == 0, result.stdout + result.stderr
    return REPO_ROOT / "dist" / "codex"


def test_render_codex_outputs_custom_agent_toml(rendered_codex):
    agents_dir = rendered_codex / "agents"
    rendered = {path.stem for path in agents_dir.glob("*.toml")}
    assert rendered == EXPECTED_AGENTS

    for agent_file in agents_dir.glob("*.toml"):
        text = agent_file.read_text(encoding="utf-8")
        assert toml_scalar(text, "name") == agent_file.stem
        assert toml_scalar(text, "description")
        assert "developer_instructions = " in text
        assert toml_scalar(text, "model") in {"gpt-5.4-mini", "gpt-5.5"}
        assert toml_scalar(text, "model_reasoning_effort") in {"low", "medium", "high"}
        assert "gpt-5.2" not in text
        assert "gpt-5.3-codex" not in text


def test_render_codex_outputs_docs_config_and_skills(rendered_codex):
    assert (rendered_codex / "AGENTS.md").is_file()
    assert (rendered_codex / "config.toml").is_file()
    skills = [path for path in (rendered_codex / "skills").iterdir() if (path / "SKILL.md").exists()]
    assert len(skills) == source_skill_count()

    config = (rendered_codex / "config.toml").read_text(encoding="utf-8")
    assert 'sandbox_mode = "workspace-write"' in config
    assert 'approval_policy = "on-request"' in config
    assert "network_access = false" in config


def test_install_codex_honors_destdir_and_skill_root(tmp_path):
    result = run("make", "install-codex", f"DESTDIR={tmp_path}", "BACKUP=never", timeout=240)
    assert result.returncode == 0, result.stdout + result.stderr

    codex_home = tmp_path / ".codex"
    skills_root = tmp_path / ".agents" / "skills"
    assert codex_home.is_dir()
    assert skills_root.is_dir()
    assert {path.stem for path in (codex_home / "agents").glob("*.toml")} == EXPECTED_AGENTS
    assert (codex_home / "agents" / ".agentic-engine-codex").is_file()
    assert len([path for path in skills_root.iterdir() if (path / "SKILL.md").exists()]) == source_skill_count()

    validate = run(
        sys.executable,
        str(RENDERER),
        str(REPO_ROOT),
        str(codex_home),
        "--skills-root",
        str(skills_root),
        "--validate",
    )
    assert validate.returncode == 0, validate.stdout + validate.stderr


def test_reinstall_preserves_foreign_codex_files(tmp_path):
    first = run("make", "install-codex", f"DESTDIR={tmp_path}", "BACKUP=never", timeout=240)
    assert first.returncode == 0, first.stdout + first.stderr

    codex_home = tmp_path / ".codex"
    skills_root = tmp_path / ".agents" / "skills"
    foreign_agent = codex_home / "agents" / "user-agent.toml"
    foreign_agent.write_text(
        'name = "user-agent"\ndescription = "foreign"\ndeveloper_instructions = "stay"\n',
        encoding="utf-8",
    )

    foreign_config = codex_home / "config.toml"
    foreign_config.write_text('model = "user-choice"\n', encoding="utf-8")

    foreign_skill = skills_root / "user-skill"
    foreign_skill.mkdir()
    (foreign_skill / "SKILL.md").write_text(
        "---\nname: user-skill\ndescription: foreign skill\n---\n",
        encoding="utf-8",
    )

    second = run("make", "install-codex", f"DESTDIR={tmp_path}", "BACKUP=never", timeout=240)
    assert second.returncode == 0, second.stdout + second.stderr

    assert foreign_agent.read_text(encoding="utf-8").startswith('name = "user-agent"')
    assert foreign_config.read_text(encoding="utf-8") == 'model = "user-choice"\n'
    assert (codex_home / "agentic-engineers.config.toml").is_file()
    assert (foreign_skill / "SKILL.md").is_file()


def test_uninstall_codex_removes_managed_only(tmp_path):
    install = run("make", "install-codex", f"DESTDIR={tmp_path}", "BACKUP=never", timeout=240)
    assert install.returncode == 0, install.stdout + install.stderr

    codex_home = tmp_path / ".codex"
    foreign_agent = codex_home / "agents" / "user-agent.toml"
    foreign_agent.write_text(
        'name = "user-agent"\ndescription = "foreign"\ndeveloper_instructions = "stay"\n',
        encoding="utf-8",
    )

    uninstall = run("make", "uninstall-codex", f"DESTDIR={tmp_path}", timeout=240)
    assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr

    assert foreign_agent.is_file()
    assert not (codex_home / "agents" / "engineer.toml").exists()
    assert not (codex_home / "AGENTS.md").exists()
