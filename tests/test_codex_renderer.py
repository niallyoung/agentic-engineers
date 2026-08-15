"""Codex renderer integration tests.

These tests exercise the Codex harness without touching the user's real
~/.codex directory.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml


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


def load_model_registry() -> dict:
    """Load the codex role->model mapping straight from the renderer.

    There is no standalone models.yaml registry (src/config/ was removed in
    the framework slimdown) — CODEX_MODEL_BY_ROLE in render-codex.py is now
    the single source of truth for Codex model assignment.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("render_codex", RENDERER)
    module = importlib.util.module_from_spec(spec)
    sys.modules["render_codex"] = module  # dataclass annotation resolution needs this
    spec.loader.exec_module(module)
    return module.CODEX_MODEL_BY_ROLE


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
        assert "nickname_candidates = []" not in text
        assert "handoff_type: HANDBACK" in text
        assert "gpt-5.2" not in text
        assert "gpt-5.3-codex" not in text


def test_render_codex_outputs_docs_config_and_skills(rendered_codex):
    assert (rendered_codex / "AGENTS.md").is_file()
    assert (rendered_codex / "config.toml").is_file()
    assert (rendered_codex / "agentic-engineers-orchestrator.config.toml").is_file()
    skills = [path for path in (rendered_codex / "skills").iterdir() if (path / "SKILL.md").exists()]
    assert len(skills) == source_skill_count()

    agents_doc = (rendered_codex / "AGENTS.md").read_text(encoding="utf-8")
    assert "codex --profile agentic-engineers-orchestrator" in agents_doc
    assert "delegate:" in agents_doc
    assert "handoff_type: HANDBACK" in agents_doc
    assert "Orchestrator-only" in agents_doc
    assert "does not implement user tasks itself" in agents_doc
    assert "Dispatch Model" in agents_doc
    assert "expected_handback" not in agents_doc
    assert "semicolon-separated tasks" in agents_doc
    assert "spawn independent tasks in parallel" in agents_doc.lower()
    assert "same-file edits coordinated" in agents_doc

    config = (rendered_codex / "config.toml").read_text(encoding="utf-8")
    assert 'sandbox_mode = "workspace-write"' in config
    assert 'approval_policy = "on-request"' in config
    assert "multi_agent = true" in config
    assert "network_access = false" in config

    profile = (rendered_codex / "agentic-engineers-orchestrator.config.toml").read_text(encoding="utf-8")
    assert 'model = "gpt-5.4-mini"' in profile
    assert 'model_reasoning_effort = "low"' in profile
    assert "developer_instructions = " in profile
    assert "Delegate Prefix" in profile
    assert "multi_agent = true" in profile
    assert "does not implement user tasks itself" in profile
    assert "expected_handback" not in profile
    assert "semicolon-separated tasks" in profile
    assert "spawn independent tasks in parallel" in profile.lower()
    assert "same-file edits coordinated" in profile


def test_render_codex_model_mapping_matches_source_registry(rendered_codex):
    role_models = load_model_registry()

    orchestrator_profile = (rendered_codex / "agentic-engineers-orchestrator.config.toml").read_text(
        encoding="utf-8"
    )
    engineer_agent = (rendered_codex / "agents" / "engineer.toml").read_text(encoding="utf-8")
    security_agent = (rendered_codex / "agents" / "security-engineer.toml").read_text(
        encoding="utf-8"
    )

    assert f'model = "{role_models["general_orchestrator"]}"' in orchestrator_profile
    assert f'model = "{role_models["engineer"]}"' in engineer_agent
    assert f'model = "{role_models["security_engineer"]}"' in security_agent


def test_render_codex_validate_checks_agents_contract(rendered_codex):
    validate = run(
        sys.executable,
        str(RENDERER),
        str(REPO_ROOT),
        str(rendered_codex),
        "--skills-root",
        str(rendered_codex / "skills"),
        "--validate",
    )
    assert validate.returncode == 0, validate.stdout + validate.stderr


def test_install_codex_honors_destdir_and_skill_root(tmp_path):
    result = run("make", "install-codex", f"DESTDIR={tmp_path}", "BACKUP=never", timeout=240)
    assert result.returncode == 0, result.stdout + result.stderr

    codex_home = tmp_path / ".codex"
    skills_root = tmp_path / ".codex" / "skills"
    assert codex_home.is_dir()
    assert skills_root.is_dir()
    assert (codex_home / "agentic-engineers-orchestrator.config.toml").is_file()
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
    skills_root = tmp_path / ".codex" / "skills"
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
    assert (codex_home / "agentic-engineers-orchestrator.config.toml").is_file()
    assert (foreign_skill / "SKILL.md").is_file()


def test_foreign_orchestrator_profile_is_preserved_and_fails_validation(tmp_path):
    codex_home = tmp_path / ".codex"
    codex_home.mkdir(parents=True)
    foreign_profile = codex_home / "agentic-engineers-orchestrator.config.toml"
    foreign_profile.write_text('model = "user-choice"\n', encoding="utf-8")

    install = run("make", "install-codex", f"DESTDIR={tmp_path}", "BACKUP=never", timeout=240)
    assert install.returncode == 0, install.stdout + install.stderr
    assert foreign_profile.read_text(encoding="utf-8") == 'model = "user-choice"\n'

    validate = run(
        sys.executable,
        str(RENDERER),
        str(REPO_ROOT),
        str(codex_home),
        "--skills-root",
        str(tmp_path / ".codex" / "skills"),
        "--validate",
    )
    assert validate.returncode == 1
    assert "agentic-engineers-orchestrator.config.toml is foreign or unmanaged" in (
        validate.stdout + validate.stderr
    )


def test_uninstall_codex_removes_managed_only(tmp_path):
    install = run("make", "install-codex", f"DESTDIR={tmp_path}", "BACKUP=never", timeout=240)
    assert install.returncode == 0, install.stdout + install.stderr

    codex_home = tmp_path / ".codex"
    skills_root = tmp_path / ".codex" / "skills"
    foreign_agent = codex_home / "agents" / "user-agent.toml"
    foreign_agent.write_text(
        'name = "user-agent"\ndescription = "foreign"\ndeveloper_instructions = "stay"\n',
        encoding="utf-8",
    )
    foreign_skill = skills_root / "user-skill"
    foreign_skill.mkdir()
    (foreign_skill / "SKILL.md").write_text(
        "---\nname: user-skill\ndescription: foreign skill\n---\n",
        encoding="utf-8",
    )

    uninstall = run("make", "uninstall-codex", f"DESTDIR={tmp_path}", timeout=240)
    assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr

    assert foreign_agent.is_file()
    assert (foreign_skill / "SKILL.md").is_file()
    assert not (codex_home / "agents" / "engineer.toml").exists()
    assert not (codex_home / "AGENTS.md").exists()
    assert not (codex_home / "agentic-engineers-orchestrator.config.toml").exists()
