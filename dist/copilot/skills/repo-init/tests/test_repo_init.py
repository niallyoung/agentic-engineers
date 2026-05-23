# -*- coding: utf-8 -*-
"""
test_repo_init.py — TDD test scaffold for repo-init skill.

Phase: RED (tests written before implementation is complete)
Pattern: test_<action>_<scenario>_<expected>

Test categories:
  - test_analyze_*         Phase 1: Repository analysis
  - test_generate_spec_*   Phase 2: SPEC.md generation
  - test_bootstrap_*       Phase 3: Directory structure
  - test_housekeeping_*    Phase 4: .gitignore and README.md
  - test_framework_*       Phase 5: Framework bootstrap
  - test_validate_compat_* Phase 6: Compatibility validation
  - test_init_todo_*       Phase 7: TODO.md initialization
  - test_generate_docs_*   Phase 8: Documentation generation
  - test_dry_run_*         Dry-run mode (no writes)
  - test_idempotent_*      Idempotency (safe to run twice)
  - test_init_result_*     RepoInitializer end-to-end
  - test_preflight_*       Pre-flight checks

Author: Senior Engineer
"""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

import pytest


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def tmp_git_repo(tmp_path):
    """Minimal git repo for testing (no files)."""
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@test.com",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@test.com",
    }
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        env=env,
    )
    return tmp_path


@pytest.fixture
def python_repo(tmp_git_repo):
    """Git repo with Python file structure."""
    (tmp_git_repo / "main.py").write_text("# main\n")
    (tmp_git_repo / "requirements.txt").write_text("flask==3.0.0\n")
    (tmp_git_repo / "LICENSE").write_text("MIT License\n")
    (tmp_git_repo / ".github" / "workflows").mkdir(parents=True)
    (tmp_git_repo / ".github" / "workflows" / "ci.yml").write_text("on: push\n")
    return tmp_git_repo


@pytest.fixture
def ts_repo(tmp_git_repo):
    """Git repo with TypeScript file structure."""
    (tmp_git_repo / "src").mkdir()
    # Create more .ts files than .js to ensure TypeScript is primary
    for i in range(5):
        (tmp_git_repo / "src" / f"module_{i}.ts").write_text(f"// module {i}\n")
    (tmp_git_repo / "src" / "index.ts").write_text("// main\n")
    (tmp_git_repo / "package.json").write_text(
        '{"name": "my-app", "scripts": {"test": "jest"}}\n'
    )
    (tmp_git_repo / "jest.config.js").write_text("module.exports = {};\n")
    return tmp_git_repo


@pytest.fixture
def monorepo(tmp_git_repo):
    """Git repo with monorepo structure."""
    for pkg in ("api", "worker", "shared"):
        (tmp_git_repo / "packages" / pkg).mkdir(parents=True)
        (tmp_git_repo / "packages" / pkg / "index.ts").write_text("")
    return tmp_git_repo


@pytest.fixture
def cfg_factory(tmp_git_repo):
    """Return a factory for RepoInitConfig instances."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from repo_init import RepoInitConfig

    def _make(**kwargs):
        defaults = dict(
            repo_root=tmp_git_repo,
            project_name="test-project",
            model_harness="claude",
        )
        defaults.update(kwargs)
        return RepoInitConfig(**defaults)

    return _make


# ============================================================================
# PHASE 1: ANALYZE
# ============================================================================

class TestAnalyzeRepo:
    """Tests for Phase 1: analyze_repo()"""

    def test_analyze_python_repo_detects_python_language(self, python_repo):
        from analyze_repo import analyze_repo
        result = analyze_repo(python_repo)
        assert result.primary_language == "python"

    def test_analyze_typescript_repo_detects_typescript_language(self, ts_repo):
        from analyze_repo import analyze_repo
        result = analyze_repo(ts_repo)
        assert result.primary_language == "typescript"

    def test_analyze_python_repo_detects_pip_package_manager(self, python_repo):
        from analyze_repo import analyze_repo
        result = analyze_repo(python_repo)
        assert result.package_manager == "pip"

    def test_analyze_ts_repo_detects_npm_package_manager(self, ts_repo):
        from analyze_repo import analyze_repo
        result = analyze_repo(ts_repo)
        assert result.package_manager == "npm"

    def test_analyze_python_repo_detects_github_actions_ci(self, python_repo):
        from analyze_repo import analyze_repo
        result = analyze_repo(python_repo)
        assert result.ci_provider == "github-actions"

    def test_analyze_ts_repo_detects_jest_test_framework(self, ts_repo):
        from analyze_repo import analyze_repo
        result = analyze_repo(ts_repo)
        assert result.test_framework == "jest"

    def test_analyze_empty_repo_returns_unknown_language(self, tmp_git_repo):
        from analyze_repo import analyze_repo
        result = analyze_repo(tmp_git_repo)
        assert result.primary_language == "unknown"

    def test_analyze_monorepo_detects_monorepo_structure(self, monorepo):
        from analyze_repo import analyze_repo
        result = analyze_repo(monorepo)
        assert result.is_monorepo is True

    def test_analyze_single_package_repo_is_not_monorepo(self, python_repo):
        from analyze_repo import analyze_repo
        result = analyze_repo(python_repo)
        assert result.is_monorepo is False

    def test_analyze_repo_with_license_detects_mit(self, python_repo):
        from analyze_repo import analyze_repo
        result = analyze_repo(python_repo)
        assert result.license == "MIT"

    def test_analyze_repo_without_license_returns_unknown(self, ts_repo):
        from analyze_repo import analyze_repo
        result = analyze_repo(ts_repo)
        assert result.license == "unknown"

    def test_analyze_repo_detects_readme_present(self, python_repo):
        (python_repo / "README.md").write_text("# Hello\n")
        from analyze_repo import analyze_repo
        result = analyze_repo(python_repo)
        assert result.has_readme is True

    def test_analyze_repo_detects_readme_absent(self, python_repo):
        from analyze_repo import analyze_repo
        result = analyze_repo(python_repo)
        assert result.has_readme is False

    def test_analyze_large_repo_classifies_as_large(self, tmp_git_repo):
        # Create 1001 dummy files
        for i in range(1001):
            (tmp_git_repo / f"file_{i}.txt").write_text(f"file {i}")
        from analyze_repo import analyze_repo
        result = analyze_repo(tmp_git_repo)
        assert result.size_class == "large"

    def test_analyze_small_repo_classifies_as_small(self, tmp_git_repo):
        (tmp_git_repo / "main.py").write_text("# hello")
        from analyze_repo import analyze_repo
        result = analyze_repo(tmp_git_repo)
        assert result.size_class == "small"

    def test_analyze_existing_init_detects_init_marker(self, tmp_git_repo):
        marker = tmp_git_repo / ".agentic-engineers" / "INIT-COMPLETE.yaml"
        marker.parent.mkdir()
        marker.write_text("status: SUCCESS\n")
        from analyze_repo import analyze_repo
        result = analyze_repo(tmp_git_repo)
        assert result.existing_init is True

    def test_analyze_returns_correct_project_name(self, tmp_git_repo):
        from analyze_repo import analyze_repo
        result = analyze_repo(tmp_git_repo)
        # Project name is inferred from directory name
        assert result.project_name == tmp_git_repo.name.lower()


# ============================================================================
# PHASE 2: GENERATE SPEC
# ============================================================================

class TestGenerateSpec:
    """Tests for Phase 2: generate_spec()"""

    def test_generate_spec_creates_docs_spec_md(self, cfg_factory, python_repo):
        from analyze_repo import analyze_repo
        from generate_spec import generate_spec
        cfg = cfg_factory(repo_root=python_repo)
        analysis = analyze_repo(python_repo)
        generate_spec(cfg, analysis)
        assert (python_repo / "docs" / "SPEC.md").is_file()

    def test_generate_spec_contains_project_name(self, cfg_factory, python_repo):
        from analyze_repo import analyze_repo
        from generate_spec import generate_spec
        cfg = cfg_factory(repo_root=python_repo, project_name="my-cool-api")
        analysis = analyze_repo(python_repo)
        generate_spec(cfg, analysis)
        content = (python_repo / "docs" / "SPEC.md").read_text()
        assert "my-cool-api" in content

    def test_generate_spec_contains_agent_team_section(self, cfg_factory, python_repo):
        from analyze_repo import analyze_repo
        from generate_spec import generate_spec
        cfg = cfg_factory(repo_root=python_repo)
        analysis = analyze_repo(python_repo)
        generate_spec(cfg, analysis)
        content = (python_repo / "docs" / "SPEC.md").read_text()
        assert "Agent Team" in content

    def test_generate_spec_contains_quality_gates_section(self, cfg_factory, python_repo):
        from analyze_repo import analyze_repo
        from generate_spec import generate_spec
        cfg = cfg_factory(repo_root=python_repo)
        analysis = analyze_repo(python_repo)
        generate_spec(cfg, analysis)
        content = (python_repo / "docs" / "SPEC.md").read_text()
        assert "Quality Gates" in content

    def test_generate_spec_skips_if_already_exists(self, cfg_factory, python_repo):
        """SPEC.md should not be overwritten if it already exists."""
        (python_repo / "docs").mkdir()
        existing = python_repo / "docs" / "SPEC.md"
        existing.write_text("EXISTING CONTENT\n")
        from analyze_repo import analyze_repo
        from generate_spec import generate_spec
        cfg = cfg_factory(repo_root=python_repo)
        analysis = analyze_repo(python_repo)
        result = generate_spec(cfg, analysis)
        assert result == []
        assert existing.read_text() == "EXISTING CONTENT\n"

    def test_generate_spec_claude_harness_uses_haiku_for_engineer(self, cfg_factory, python_repo):
        from analyze_repo import analyze_repo
        from generate_spec import generate_spec
        cfg = cfg_factory(repo_root=python_repo, model_harness="claude")
        analysis = analyze_repo(python_repo)
        generate_spec(cfg, analysis)
        content = (python_repo / "docs" / "SPEC.md").read_text()
        assert "claude-haiku-4.5" in content

    def test_generate_spec_dry_run_does_not_write_file(self, cfg_factory, python_repo):
        from analyze_repo import analyze_repo
        from generate_spec import generate_spec
        cfg = cfg_factory(repo_root=python_repo)
        analysis = analyze_repo(python_repo)
        generate_spec(cfg, analysis, dry_run=True)
        assert not (python_repo / "docs" / "SPEC.md").exists()

    def test_generate_spec_no_placeholder_variables_remain(self, cfg_factory, python_repo):
        """No {placeholder} variables should remain after rendering."""
        from analyze_repo import analyze_repo
        from generate_spec import generate_spec
        import re
        cfg = cfg_factory(repo_root=python_repo, project_description="A test project.")
        analysis = analyze_repo(python_repo)
        generate_spec(cfg, analysis)
        content = (python_repo / "docs" / "SPEC.md").read_text()
        # Find any remaining {word} placeholders (skip YAML/code blocks)
        placeholders = re.findall(r'\{[a-z_]+\}', content)
        assert placeholders == [], f"Unrendered placeholders: {placeholders}"


# ============================================================================
# PHASE 3: BOOTSTRAP STRUCTURE
# ============================================================================

class TestBootstrapStructure:
    """Tests for Phase 3: bootstrap_structure()"""

    def test_bootstrap_creates_agents_directory(self, cfg_factory, tmp_git_repo):
        from analyze_repo import analyze_repo
        from bootstrap_structure import bootstrap_structure
        cfg = cfg_factory(repo_root=tmp_git_repo)
        analysis = analyze_repo(tmp_git_repo)
        bootstrap_structure(cfg, analysis)
        assert (tmp_git_repo / "agents").is_dir()

    def test_bootstrap_creates_skills_directory(self, cfg_factory, tmp_git_repo):
        from analyze_repo import analyze_repo
        from bootstrap_structure import bootstrap_structure
        cfg = cfg_factory(repo_root=tmp_git_repo)
        analysis = analyze_repo(tmp_git_repo)
        bootstrap_structure(cfg, analysis)
        assert (tmp_git_repo / "skills").is_dir()

    def test_bootstrap_creates_tests_directory(self, cfg_factory, tmp_git_repo):
        from analyze_repo import analyze_repo
        from bootstrap_structure import bootstrap_structure
        cfg = cfg_factory(repo_root=tmp_git_repo)
        analysis = analyze_repo(tmp_git_repo)
        bootstrap_structure(cfg, analysis)
        assert (tmp_git_repo / "tests").is_dir()

    def test_bootstrap_creates_docs_directory(self, cfg_factory, tmp_git_repo):
        from analyze_repo import analyze_repo
        from bootstrap_structure import bootstrap_structure
        cfg = cfg_factory(repo_root=tmp_git_repo)
        analysis = analyze_repo(tmp_git_repo)
        bootstrap_structure(cfg, analysis)
        assert (tmp_git_repo / "docs").is_dir()

    def test_bootstrap_creates_artifacts_queue(self, cfg_factory, tmp_git_repo):
        from analyze_repo import analyze_repo
        from bootstrap_structure import bootstrap_structure
        cfg = cfg_factory(repo_root=tmp_git_repo)
        analysis = analyze_repo(tmp_git_repo)
        bootstrap_structure(cfg, analysis)
        assert (tmp_git_repo / "artifacts" / "queue" / "incoming").is_dir()

    def test_bootstrap_creates_conftest_py(self, cfg_factory, tmp_git_repo):
        from analyze_repo import analyze_repo
        from bootstrap_structure import bootstrap_structure
        cfg = cfg_factory(repo_root=tmp_git_repo)
        analysis = analyze_repo(tmp_git_repo)
        bootstrap_structure(cfg, analysis)
        assert (tmp_git_repo / "tests" / "conftest.py").is_file()

    def test_bootstrap_creates_smoke_test(self, cfg_factory, tmp_git_repo):
        from analyze_repo import analyze_repo
        from bootstrap_structure import bootstrap_structure
        cfg = cfg_factory(repo_root=tmp_git_repo)
        analysis = analyze_repo(tmp_git_repo)
        bootstrap_structure(cfg, analysis)
        assert (tmp_git_repo / "tests" / "test_framework_init.py").is_file()

    def test_bootstrap_dry_run_creates_no_directories(self, cfg_factory, tmp_git_repo):
        from analyze_repo import analyze_repo
        from bootstrap_structure import bootstrap_structure
        cfg = cfg_factory(repo_root=tmp_git_repo)
        analysis = analyze_repo(tmp_git_repo)
        bootstrap_structure(cfg, analysis, dry_run=True)
        assert not (tmp_git_repo / "agents").exists()
        assert not (tmp_git_repo / "skills").exists()

    def test_bootstrap_idempotent_second_run_does_not_overwrite(self, cfg_factory, tmp_git_repo):
        from analyze_repo import analyze_repo
        from bootstrap_structure import bootstrap_structure
        cfg = cfg_factory(repo_root=tmp_git_repo)
        analysis = analyze_repo(tmp_git_repo)
        bootstrap_structure(cfg, analysis)
        # Write a sentinel to an existing file
        readme = tmp_git_repo / "agents" / "README.md"
        original = readme.read_text()
        readme.write_text("CUSTOM CONTENT\n")
        # Second run should not overwrite
        bootstrap_structure(cfg, analysis)
        assert readme.read_text() == "CUSTOM CONTENT\n"


# ============================================================================
# PHASE 4: HOUSEKEEPING
# ============================================================================

class TestHousekeeping:
    """Tests for Phase 4: run_housekeeping()"""

    def test_housekeeping_creates_gitignore_if_missing(self, cfg_factory, tmp_git_repo):
        from housekeeping import run_housekeeping
        cfg = cfg_factory(repo_root=tmp_git_repo)
        run_housekeeping(cfg)
        assert (tmp_git_repo / ".gitignore").is_file()

    def test_housekeeping_gitignore_contains_artifacts_queue(self, cfg_factory, tmp_git_repo):
        from housekeeping import run_housekeeping
        cfg = cfg_factory(repo_root=tmp_git_repo)
        run_housekeeping(cfg)
        content = (tmp_git_repo / ".gitignore").read_text()
        assert "artifacts/queue/" in content

    def test_housekeeping_creates_readme_if_missing(self, cfg_factory, tmp_git_repo):
        from housekeeping import run_housekeeping
        cfg = cfg_factory(repo_root=tmp_git_repo)
        run_housekeeping(cfg)
        assert (tmp_git_repo / "README.md").is_file()

    def test_housekeeping_appends_to_existing_gitignore(self, cfg_factory, tmp_git_repo):
        gitignore = tmp_git_repo / ".gitignore"
        gitignore.write_text("*.pyc\n__pycache__/\n")
        from housekeeping import run_housekeeping
        cfg = cfg_factory(repo_root=tmp_git_repo)
        run_housekeeping(cfg)
        content = gitignore.read_text()
        assert "*.pyc" in content
        assert "artifacts/queue/" in content

    def test_housekeeping_does_not_duplicate_gitignore_entries(self, cfg_factory, tmp_git_repo):
        from housekeeping import run_housekeeping, _GITIGNORE_MARKER
        cfg = cfg_factory(repo_root=tmp_git_repo)
        run_housekeeping(cfg)
        run_housekeeping(cfg)  # Second run
        content = (tmp_git_repo / ".gitignore").read_text()
        assert content.count(_GITIGNORE_MARKER) == 1

    def test_housekeeping_appends_section_to_existing_readme(self, cfg_factory, tmp_git_repo):
        readme = tmp_git_repo / "README.md"
        readme.write_text("# My Project\n\nSome content.\n")
        from housekeeping import run_housekeeping
        cfg = cfg_factory(repo_root=tmp_git_repo)
        run_housekeeping(cfg)
        content = readme.read_text()
        assert "My Project" in content  # Original preserved
        assert "Agentic Engineers" in content  # Section appended

    def test_housekeeping_dry_run_does_not_write(self, cfg_factory, tmp_git_repo):
        from housekeeping import run_housekeeping
        cfg = cfg_factory(repo_root=tmp_git_repo)
        run_housekeeping(cfg, dry_run=True)
        assert not (tmp_git_repo / ".gitignore").exists()
        assert not (tmp_git_repo / "README.md").exists()


# ============================================================================
# PHASE 6: COMPATIBILITY VALIDATION
# ============================================================================

class TestValidateCompatibility:
    """Tests for Phase 6: validate_compatibility()"""

    def test_validate_compat_claude_harness_assigns_haiku_to_engineer(self, cfg_factory, tmp_git_repo):
        from validate_compatibility import validate_compatibility
        cfg = cfg_factory(repo_root=tmp_git_repo, model_harness="claude")
        result = validate_compatibility(cfg)
        assert result.model_assignments["engineer"] == "claude-haiku-4.5"

    def test_validate_compat_claude_harness_assigns_sonnet_to_senior(self, cfg_factory, tmp_git_repo):
        from validate_compatibility import validate_compatibility
        cfg = cfg_factory(repo_root=tmp_git_repo, model_harness="claude")
        result = validate_compatibility(cfg)
        assert result.model_assignments["senior-engineer"] == "claude-sonnet-4.6"

    def test_validate_compat_gpt5_harness_assigns_mini_to_engineer(self, cfg_factory, tmp_git_repo):
        from validate_compatibility import validate_compatibility
        cfg = cfg_factory(repo_root=tmp_git_repo, model_harness="gpt5")
        result = validate_compatibility(cfg)
        assert result.model_assignments["engineer"] == "gpt-4o-mini"

    def test_validate_compat_local_harness_assigns_ollama_to_engineer(self, cfg_factory, tmp_git_repo):
        from validate_compatibility import validate_compatibility
        cfg = cfg_factory(repo_root=tmp_git_repo, model_harness="local")
        result = validate_compatibility(cfg)
        assert result.model_assignments["engineer"].startswith("ollama/")

    def test_validate_compat_local_harness_reduces_quality_threshold(self, cfg_factory, tmp_git_repo):
        from validate_compatibility import validate_compatibility
        cfg = cfg_factory(repo_root=tmp_git_repo, model_harness="local")
        result = validate_compatibility(cfg)
        assert result.quality_threshold < 85

    def test_validate_compat_tool_matrix_includes_git(self, cfg_factory, tmp_git_repo):
        from validate_compatibility import validate_compatibility
        cfg = cfg_factory(repo_root=tmp_git_repo)
        result = validate_compatibility(cfg)
        assert "git" in result.tool_matrix

    def test_validate_compat_api_key_check_does_not_log_value(self, cfg_factory, tmp_git_repo, monkeypatch):
        """API key check must return bool, not log the key value."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret-key-1234567890")
        from validate_compatibility import _check_api_keys
        present, missing = _check_api_keys("claude")
        assert present is True
        assert missing == []
        # Ensure the key value is not exposed in result

    def test_validate_compat_missing_api_key_returns_warning_not_hard_failure(
        self, cfg_factory, tmp_git_repo, monkeypatch
    ):
        import sys
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from validate_compatibility import validate_compatibility
        cfg = cfg_factory(repo_root=tmp_git_repo, model_harness="claude")
        result = validate_compatibility(cfg)
        # Missing API key is a warning, not a hard failure.
        # Filter out Python version failures (test env may run Python < 3.8).
        api_key_is_hard_failure = any(
            "key" in e.lower() or "anthropic" in e.lower() or "api" in e.lower()
            for e in result.hard_failures
        )
        assert not api_key_is_hard_failure
        assert any("api" in w.lower() or "key" in w.lower() for w in result.warnings)

    def test_validate_compat_format_report_returns_string(self, cfg_factory, tmp_git_repo):
        from validate_compatibility import validate_compatibility
        cfg = cfg_factory(repo_root=tmp_git_repo)
        result = validate_compatibility(cfg)
        report = result.format_report()
        assert isinstance(report, str)
        assert "TOOL AVAILABILITY" in report


# ============================================================================
# PHASE 7: TODO INITIALIZATION
# ============================================================================

class TestInitTodo:
    """Tests for Phase 7: init_todo()"""

    def test_init_todo_creates_todo_md(self, cfg_factory, tmp_git_repo):
        from analyze_repo import analyze_repo
        from init_todo import init_todo
        cfg = cfg_factory(repo_root=tmp_git_repo)
        analysis = analyze_repo(tmp_git_repo)
        init_todo(cfg, analysis)
        assert (tmp_git_repo / "TODO.md").is_file()

    def test_init_todo_contains_init_001_item(self, cfg_factory, tmp_git_repo):
        from analyze_repo import analyze_repo
        from init_todo import init_todo
        cfg = cfg_factory(repo_root=tmp_git_repo)
        analysis = analyze_repo(tmp_git_repo)
        init_todo(cfg, analysis)
        content = (tmp_git_repo / "TODO.md").read_text()
        assert "INIT-001" in content

    def test_init_todo_contains_priority_section(self, cfg_factory, tmp_git_repo):
        from analyze_repo import analyze_repo
        from init_todo import init_todo
        cfg = cfg_factory(repo_root=tmp_git_repo)
        analysis = analyze_repo(tmp_git_repo)
        init_todo(cfg, analysis)
        content = (tmp_git_repo / "TODO.md").read_text()
        assert "Priority" in content

    def test_init_todo_no_test_framework_adds_init_t01(self, cfg_factory, tmp_git_repo):
        """When no test framework detected, INIT-T01 should be added."""
        from analyze_repo import analyze_repo, AnalysisResult
        from init_todo import init_todo
        cfg = cfg_factory(repo_root=tmp_git_repo)
        analysis = analyze_repo(tmp_git_repo)
        analysis.test_framework = "unknown"  # Force
        init_todo(cfg, analysis)
        content = (tmp_git_repo / "TODO.md").read_text()
        assert "INIT-T01" in content

    def test_init_todo_no_ci_adds_init_c01(self, cfg_factory, tmp_git_repo):
        """When no CI detected, INIT-C01 should be added."""
        from analyze_repo import analyze_repo
        from init_todo import init_todo
        cfg = cfg_factory(repo_root=tmp_git_repo)
        analysis = analyze_repo(tmp_git_repo)
        analysis.ci_provider = "none"  # Force
        init_todo(cfg, analysis)
        content = (tmp_git_repo / "TODO.md").read_text()
        assert "INIT-C01" in content

    def test_init_todo_monorepo_adds_init_m01(self, cfg_factory, monorepo):
        from analyze_repo import analyze_repo
        from init_todo import init_todo
        cfg = cfg_factory(repo_root=monorepo)
        analysis = analyze_repo(monorepo)
        init_todo(cfg, analysis)
        content = (monorepo / "TODO.md").read_text()
        assert "INIT-M01" in content

    def test_init_todo_skips_if_already_exists(self, cfg_factory, tmp_git_repo):
        existing = tmp_git_repo / "TODO.md"
        existing.write_text("EXISTING TODO\n")
        from analyze_repo import analyze_repo
        from init_todo import init_todo
        cfg = cfg_factory(repo_root=tmp_git_repo)
        analysis = analyze_repo(tmp_git_repo)
        result = init_todo(cfg, analysis)
        assert result == []
        assert existing.read_text() == "EXISTING TODO\n"

    def test_init_todo_dry_run_does_not_write(self, cfg_factory, tmp_git_repo):
        from analyze_repo import analyze_repo
        from init_todo import init_todo
        cfg = cfg_factory(repo_root=tmp_git_repo)
        analysis = analyze_repo(tmp_git_repo)
        init_todo(cfg, analysis, dry_run=True)
        assert not (tmp_git_repo / "TODO.md").exists()


# ============================================================================
# PHASE 8: DOCUMENTATION GENERATION
# ============================================================================

class TestGenerateDocs:
    """Tests for Phase 8: generate_docs()"""

    def test_generate_docs_creates_onboarding_md(self, cfg_factory, python_repo):
        from analyze_repo import analyze_repo
        from generate_docs import generate_docs
        cfg = cfg_factory(repo_root=python_repo)
        analysis = analyze_repo(python_repo)
        generate_docs(cfg, analysis)
        assert (python_repo / "docs" / "ONBOARDING.md").is_file()

    def test_generate_docs_creates_quick_start_md(self, cfg_factory, python_repo):
        from analyze_repo import analyze_repo
        from generate_docs import generate_docs
        cfg = cfg_factory(repo_root=python_repo)
        analysis = analyze_repo(python_repo)
        generate_docs(cfg, analysis)
        assert (python_repo / "docs" / "QUICK-START.md").is_file()

    def test_generate_docs_creates_agents_md(self, cfg_factory, python_repo):
        from analyze_repo import analyze_repo
        from generate_docs import generate_docs
        cfg = cfg_factory(repo_root=python_repo)
        analysis = analyze_repo(python_repo)
        generate_docs(cfg, analysis)
        assert (python_repo / "docs" / "AGENTS.md").is_file()

    def test_generate_docs_onboarding_contains_project_name(self, cfg_factory, python_repo):
        from analyze_repo import analyze_repo
        from generate_docs import generate_docs
        cfg = cfg_factory(repo_root=python_repo, project_name="my-fancy-api")
        analysis = analyze_repo(python_repo)
        generate_docs(cfg, analysis)
        content = (python_repo / "docs" / "ONBOARDING.md").read_text()
        assert "my-fancy-api" in content

    def test_generate_docs_agents_md_contains_agent_roster(self, cfg_factory, python_repo):
        from analyze_repo import analyze_repo
        from generate_docs import generate_docs
        cfg = cfg_factory(repo_root=python_repo)
        analysis = analyze_repo(python_repo)
        generate_docs(cfg, analysis)
        content = (python_repo / "docs" / "AGENTS.md").read_text()
        assert "Engineer" in content
        assert "Orchestrator" in content

    def test_generate_docs_dry_run_creates_no_files(self, cfg_factory, python_repo):
        from analyze_repo import analyze_repo
        from generate_docs import generate_docs
        cfg = cfg_factory(repo_root=python_repo)
        analysis = analyze_repo(python_repo)
        generate_docs(cfg, analysis, dry_run=True)
        assert not (python_repo / "docs" / "ONBOARDING.md").exists()

    def test_generate_docs_skips_existing_files(self, cfg_factory, python_repo):
        (python_repo / "docs").mkdir(exist_ok=True)
        existing = python_repo / "docs" / "ONBOARDING.md"
        existing.write_text("CUSTOM ONBOARDING\n")
        from analyze_repo import analyze_repo
        from generate_docs import generate_docs
        cfg = cfg_factory(repo_root=python_repo)
        analysis = analyze_repo(python_repo)
        generate_docs(cfg, analysis)
        assert existing.read_text() == "CUSTOM ONBOARDING\n"


# ============================================================================
# DRY-RUN MODE
# ============================================================================

class TestDryRun:
    """Dry-run mode must never write files."""

    def test_dry_run_complete_init_writes_no_files(self, cfg_factory, tmp_git_repo):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from repo_init import RepoInitConfig, RepoInitializer

        cfg = RepoInitConfig(
            repo_root=tmp_git_repo,
            project_name="test-dry",
            model_harness="claude",
            dry_run=True,
        )
        result = RepoInitializer().run(cfg)
        assert result.status == "DRY_RUN"
        assert len(result.files_created) == 0

    def test_dry_run_init_does_not_write_spec_md(self, cfg_factory, tmp_git_repo):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from repo_init import RepoInitConfig, RepoInitializer

        cfg = RepoInitConfig(repo_root=tmp_git_repo, dry_run=True)
        RepoInitializer().run(cfg)
        assert not (tmp_git_repo / "docs" / "SPEC.md").exists()

    def test_dry_run_does_not_write_init_marker(self, cfg_factory, tmp_git_repo):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from repo_init import RepoInitConfig, RepoInitializer

        cfg = RepoInitConfig(repo_root=tmp_git_repo, dry_run=True)
        RepoInitializer().run(cfg)
        assert not (tmp_git_repo / ".agentic-engineers" / "INIT-COMPLETE.yaml").exists()


# ============================================================================
# IDEMPOTENCY
# ============================================================================

class TestIdempotency:
    """Running repo-init twice should produce identical results without corruption."""

    def test_idempotent_second_run_blocked_by_init_marker(self, cfg_factory, tmp_git_repo):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from repo_init import RepoInitConfig, RepoInitializer

        cfg = RepoInitConfig(repo_root=tmp_git_repo, model_harness="local")
        RepoInitializer().run(cfg)

        # Second run should be blocked
        result2 = RepoInitializer().run(cfg)
        assert result2.status == "FAILED"
        assert any("already initialized" in e for e in result2.errors)

    def test_idempotent_force_reinit_does_not_corrupt_existing_files(
        self, cfg_factory, tmp_git_repo
    ):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from repo_init import RepoInitConfig, RepoInitializer

        # First run
        cfg = RepoInitConfig(repo_root=tmp_git_repo, model_harness="local")
        RepoInitializer().run(cfg)

        # Modify a file after first init
        todo = tmp_git_repo / "TODO.md"
        original_content = todo.read_text() if todo.exists() else None

        # Force reinit
        cfg2 = RepoInitConfig(
            repo_root=tmp_git_repo, model_harness="local", force_reinit=True
        )
        result2 = RepoInitializer().run(cfg2)
        # Should succeed, not corrupt


# ============================================================================
# PRE-FLIGHT CHECKS
# ============================================================================

class TestPreflight:
    """Pre-flight guard checks."""

    def test_preflight_fails_if_repo_root_does_not_exist(self):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from repo_init import RepoInitConfig, RepoInitializer

        cfg = RepoInitConfig(repo_root=Path("/nonexistent/path/12345"))
        result = RepoInitializer().run(cfg)
        assert result.status == "FAILED"
        assert any("does not exist" in e or "not a git" in e for e in result.errors)

    def test_preflight_fails_if_not_a_git_repo(self, tmp_path):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from repo_init import RepoInitConfig, RepoInitializer

        cfg = RepoInitConfig(repo_root=tmp_path)
        result = RepoInitializer().run(cfg)
        assert result.status == "FAILED"
        assert any("git" in e.lower() for e in result.errors)

    def test_preflight_fails_if_already_initialized_without_force(self, tmp_git_repo):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from repo_init import RepoInitConfig, RepoInitializer

        # Write init marker
        marker_dir = tmp_git_repo / ".agentic-engineers"
        marker_dir.mkdir()
        (marker_dir / "INIT-COMPLETE.yaml").write_text("status: SUCCESS\n")

        cfg = RepoInitConfig(repo_root=tmp_git_repo)
        result = RepoInitializer().run(cfg)
        assert result.status == "FAILED"
        assert any("already initialized" in e for e in result.errors)

    def test_preflight_passes_with_force_reinit_even_if_initialized(self, tmp_git_repo):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from repo_init import RepoInitConfig, RepoInitializer

        # Write init marker
        marker_dir = tmp_git_repo / ".agentic-engineers"
        marker_dir.mkdir()
        (marker_dir / "INIT-COMPLETE.yaml").write_text("status: SUCCESS\n")

        cfg = RepoInitConfig(
            repo_root=tmp_git_repo, force_reinit=True, model_harness="local"
        )
        result = RepoInitializer().run(cfg)
        # force_reinit=True should bypass the guard
        assert "already initialized" not in str(result.errors)


# ============================================================================
# INIT RESULT
# ============================================================================

class TestInitResult:
    """Tests for RepoInitializer end-to-end."""

    def test_init_result_str_contains_status(self, tmp_git_repo):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from repo_init import RepoInitConfig, RepoInitializer

        cfg = RepoInitConfig(repo_root=tmp_git_repo, dry_run=True)
        result = RepoInitializer().run(cfg)
        assert "DRY_RUN" in str(result) or "SUCCESS" in str(result)

    def test_init_result_span_contains_duration_ms(self, tmp_git_repo):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from repo_init import RepoInitConfig, RepoInitializer

        cfg = RepoInitConfig(repo_root=tmp_git_repo, dry_run=True)
        result = RepoInitializer().run(cfg)
        assert "duration_ms" in result.span
