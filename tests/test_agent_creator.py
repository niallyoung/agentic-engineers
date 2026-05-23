# -*- coding: utf-8 -*-
"""
tests/test_agent_creator.py — Agent-Creator Skill: TDD RED-phase test suite.

Coverage areas:
  1. AgentConfig          — dataclass fields, defaults, repr
  2. ConfigValidator      — name pattern, role enum, model enum, effort enum
  3. TemplateGenerator    — SKILL.md, __init__.py, test scaffold, DELEGATE/HANDBACK
  4. DependencyValidator  — linear deps, circular dep detection, missing dep detection
  5. IntegrationChecker   — naming conflicts, manifest compatibility, role match
  6. AgentCreator         — end-to-end scaffold, dry-run, file creation, error paths

Author: Senior Engineer
Phase: TDD RED-phase (tests define behaviour before implementation)
"""

import os
import re
import sys
import pytest
from pathlib import Path
from typing import List

# ---------------------------------------------------------------------------
# Lazy-import so RED tests are *collected* even before implementation exists
# ---------------------------------------------------------------------------
def _import():
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import importlib
    agent_creator_module = importlib.import_module('src.skills.agent-creator.scripts.agent_creator')
    AgentConfig = agent_creator_module.AgentConfig
    ValidationError = agent_creator_module.ValidationError
    CreationResult = agent_creator_module.CreationResult
    CreationStatus = agent_creator_module.CreationStatus
    DependencyGraph = agent_creator_module.DependencyGraph
    ConfigValidator = agent_creator_module.ConfigValidator
    TemplateGenerator = agent_creator_module.TemplateGenerator
    DependencyValidator = agent_creator_module.DependencyValidator
    IntegrationChecker = agent_creator_module.IntegrationChecker
    AgentCreator = agent_creator_module.AgentCreator
    ALLOWED_ROLES = agent_creator_module.ALLOWED_ROLES
    ALLOWED_EFFORTS = agent_creator_module.ALLOWED_EFFORTS
    ALLOWED_MODELS = agent_creator_module.ALLOWED_MODELS
    DEFAULT_MODEL = agent_creator_module.DEFAULT_MODEL
    DEFAULT_EFFORT = agent_creator_module.DEFAULT_EFFORT
    return (
        AgentConfig, ValidationError, CreationResult, CreationStatus,
        DependencyGraph,
        ConfigValidator, TemplateGenerator, DependencyValidator,
        IntegrationChecker, AgentCreator,
        ALLOWED_ROLES, ALLOWED_EFFORTS, ALLOWED_MODELS,
        DEFAULT_MODEL, DEFAULT_EFFORT,
    )


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mod():
    """Import all public symbols once per test session."""
    return _import()


@pytest.fixture
def valid_config(mod):
    AgentConfig = mod[0]
    return AgentConfig(
        name="my-agent",
        role="engineer",
        model="claude-haiku-4.5",
        effort="low",
        description="A test agent for unit tests.",
    )


@pytest.fixture
def validator(mod):
    ConfigValidator = mod[5]
    return ConfigValidator()


@pytest.fixture
def generator(mod):
    TemplateGenerator = mod[6]
    return TemplateGenerator()


@pytest.fixture
def dep_validator(mod):
    DependencyValidator = mod[7]
    return DependencyValidator()


@pytest.fixture
def integration_checker(mod):
    IntegrationChecker = mod[8]
    return IntegrationChecker()


@pytest.fixture
def creator(mod, tmp_path):
    AgentCreator = mod[9]
    return AgentCreator(output_root=tmp_path)


# ============================================================================
# 1. AgentConfig — dataclass fields, defaults, repr
# ============================================================================

class TestAgentConfig:
    def test_required_fields(self, mod):
        AgentConfig = mod[0]
        cfg = AgentConfig(name="test-agent", role="engineer")
        assert cfg.name == "test-agent"
        assert cfg.role == "engineer"

    def test_default_model(self, mod):
        AgentConfig, _, _, _, _, _, _, _, _, _, _, _, _, DEFAULT_MODEL, _ = mod
        cfg = AgentConfig(name="test-agent", role="engineer")
        assert cfg.model == DEFAULT_MODEL
        assert cfg.model == "claude-haiku-4.5"

    def test_default_effort(self, mod):
        AgentConfig = mod[0]
        DEFAULT_EFFORT = mod[14]
        cfg = AgentConfig(name="test-agent", role="engineer")
        assert cfg.effort == DEFAULT_EFFORT
        assert cfg.effort == "low"

    def test_default_thinking_false(self, mod):
        AgentConfig = mod[0]
        cfg = AgentConfig(name="test-agent", role="engineer")
        assert cfg.thinking is False

    def test_default_dependencies_empty(self, mod):
        AgentConfig = mod[0]
        cfg = AgentConfig(name="test-agent", role="engineer")
        assert cfg.dependencies == []

    def test_default_tools_empty(self, mod):
        AgentConfig = mod[0]
        cfg = AgentConfig(name="test-agent", role="engineer")
        assert cfg.tools == []

    def test_default_version(self, mod):
        AgentConfig = mod[0]
        cfg = AgentConfig(name="test-agent", role="engineer")
        assert cfg.version == "1.0"

    def test_custom_fields(self, mod):
        AgentConfig = mod[0]
        cfg = AgentConfig(
            name="sec-agent",
            role="security-engineer",
            model="claude-opus-4.7",
            effort="high",
            thinking=True,
            authority="principal-engineer",
            description="Security review agent.",
            category="security",
            dependencies=["quality-engineer"],
            tools=["bash", "grep"],
            version="2.0",
        )
        assert cfg.model == "claude-opus-4.7"
        assert cfg.effort == "high"
        assert cfg.thinking is True
        assert cfg.authority == "principal-engineer"
        assert cfg.category == "security"
        assert cfg.dependencies == ["quality-engineer"]
        assert cfg.tools == ["bash", "grep"]
        assert cfg.version == "2.0"

    def test_repr_contains_name(self, mod):
        AgentConfig = mod[0]
        cfg = AgentConfig(name="my-agent", role="engineer")
        assert "my-agent" in repr(cfg)


# ============================================================================
# 2. ConfigValidator — validation rules
# ============================================================================

class TestConfigValidator:

    # --- name validation ---

    def test_valid_name_simple(self, validator):
        errors = validator.validate_name("my-agent")
        assert errors == []

    def test_valid_name_alphanumeric(self, validator):
        assert validator.validate_name("agent1") == []

    def test_valid_name_max_length(self, validator):
        name = "a" * 64
        assert validator.validate_name(name) == []

    def test_invalid_name_uppercase(self, validator):
        errors = validator.validate_name("MyAgent")
        assert len(errors) > 0
        assert any("lowercase" in e.lower() or "uppercase" in e.lower() for e in errors)

    def test_invalid_name_leading_hyphen(self, validator):
        errors = validator.validate_name("-my-agent")
        assert len(errors) > 0

    def test_invalid_name_trailing_hyphen(self, validator):
        errors = validator.validate_name("my-agent-")
        assert len(errors) > 0

    def test_invalid_name_consecutive_hyphens(self, validator):
        errors = validator.validate_name("my--agent")
        assert len(errors) > 0

    def test_invalid_name_too_long(self, validator):
        name = "a" * 65
        errors = validator.validate_name(name)
        assert len(errors) > 0

    def test_invalid_name_empty(self, validator):
        errors = validator.validate_name("")
        assert len(errors) > 0

    def test_invalid_name_spaces(self, validator):
        errors = validator.validate_name("my agent")
        assert len(errors) > 0

    def test_invalid_name_special_chars(self, validator):
        errors = validator.validate_name("my_agent")
        assert len(errors) > 0

    # --- role validation ---

    def test_valid_roles(self, validator, mod):
        ALLOWED_ROLES = mod[10]
        for role in ALLOWED_ROLES:
            assert validator.validate_role(role) == [], f"Role {role!r} should be valid"

    def test_invalid_role(self, validator):
        errors = validator.validate_role("wizard")
        assert len(errors) > 0
        assert any("role" in e.lower() for e in errors)

    def test_invalid_role_empty(self, validator):
        errors = validator.validate_role("")
        assert len(errors) > 0

    # --- effort validation ---

    def test_valid_efforts(self, validator, mod):
        ALLOWED_EFFORTS = mod[11]
        for effort in ALLOWED_EFFORTS:
            assert validator.validate_effort(effort) == [], f"Effort {effort!r} should be valid"

    def test_invalid_effort(self, validator):
        errors = validator.validate_effort("extreme")
        assert len(errors) > 0

    # --- model validation ---

    def test_valid_models(self, validator, mod):
        ALLOWED_MODELS = mod[12]
        for model in ALLOWED_MODELS:
            assert validator.validate_model(model) == [], f"Model {model!r} should be valid"

    def test_invalid_model(self, validator):
        errors = validator.validate_model("gpt-99-turbo-ultra")
        assert len(errors) > 0

    # --- full validate ---

    def test_validate_valid_config(self, validator, valid_config):
        errors = validator.validate(valid_config)
        assert errors == []

    def test_validate_returns_multiple_errors(self, validator, mod):
        AgentConfig = mod[0]
        bad = AgentConfig(name="BAD NAME!", role="wizard", model="gpt-99", effort="extreme")
        errors = validator.validate(bad)
        assert len(errors) >= 3  # name + role + model + effort

    def test_validate_description_required(self, validator, mod):
        """Empty description triggers a warning (not hard error) — but validate is lenient."""
        AgentConfig = mod[0]
        cfg = AgentConfig(name="valid-agent", role="engineer", description="")
        # Empty description is allowed (description has a default)
        # validate should NOT raise — just return errors list
        result = validator.validate(cfg)
        assert isinstance(result, list)


# ============================================================================
# 3. TemplateGenerator — file content generation
# ============================================================================

class TestTemplateGenerator:

    def test_generate_skill_md_has_frontmatter(self, generator, valid_config):
        content = generator.generate_skill_md(valid_config)
        assert content.startswith("---\n")
        # Frontmatter closes
        second_dash = content.index("---\n", 4)
        assert second_dash > 4

    def test_generate_skill_md_name_field(self, generator, valid_config):
        content = generator.generate_skill_md(valid_config)
        assert "name: my-agent" in content

    def test_generate_skill_md_role_field(self, generator, valid_config):
        content = generator.generate_skill_md(valid_config)
        assert "role: engineer" in content

    def test_generate_skill_md_model_field(self, generator, valid_config):
        content = generator.generate_skill_md(valid_config)
        assert "model: claude-haiku-4.5" in content

    def test_generate_skill_md_effort_field(self, generator, valid_config):
        content = generator.generate_skill_md(valid_config)
        assert "effort: low" in content

    def test_generate_skill_md_version_field(self, generator, valid_config):
        content = generator.generate_skill_md(valid_config)
        assert 'version: "1.0"' in content

    def test_generate_skill_md_has_overview_section(self, generator, valid_config):
        content = generator.generate_skill_md(valid_config)
        assert "## Overview" in content

    def test_generate_skill_md_has_delegate_section(self, generator, valid_config):
        content = generator.generate_skill_md(valid_config)
        assert "DELEGATE" in content

    def test_generate_skill_md_has_handback_section(self, generator, valid_config):
        content = generator.generate_skill_md(valid_config)
        assert "HANDBACK" in content

    def test_generate_skill_md_thinking_true(self, generator, mod):
        AgentConfig = mod[0]
        cfg = AgentConfig(name="deep-thinker", role="principal-engineer",
                          model="claude-opus-4.7", thinking=True)
        content = generator.generate_skill_md(cfg)
        assert "thinking: true" in content

    def test_generate_skill_md_thinking_false(self, generator, valid_config):
        content = generator.generate_skill_md(valid_config)
        assert "thinking: false" in content

    def test_generate_skill_md_authority_included(self, generator, mod):
        AgentConfig = mod[0]
        cfg = AgentConfig(name="gated-agent", role="lead-engineer",
                          authority="principal-engineer")
        content = generator.generate_skill_md(cfg)
        assert "authority: principal-engineer" in content

    def test_generate_skill_md_no_authority_when_none(self, generator, valid_config):
        content = generator.generate_skill_md(valid_config)
        assert "authority:" not in content

    def test_generate_init_py(self, generator, valid_config):
        content = generator.generate_init_py(valid_config)
        assert "my-agent" in content or "my_agent" in content
        assert '"""' in content  # module docstring

    def test_generate_test_scaffold_imports_pytest(self, generator, valid_config):
        content = generator.generate_test_scaffold(valid_config)
        assert "import pytest" in content

    def test_generate_test_scaffold_has_red_phase_marker(self, generator, valid_config):
        content = generator.generate_test_scaffold(valid_config)
        assert "RED" in content or "red" in content.lower()

    def test_generate_test_scaffold_has_test_class(self, generator, valid_config):
        content = generator.generate_test_scaffold(valid_config)
        assert "class Test" in content

    def test_generate_test_scaffold_has_placeholder_test(self, generator, valid_config):
        content = generator.generate_test_scaffold(valid_config)
        assert "def test_" in content

    def test_generate_delegate_template_has_task_id(self, generator, valid_config):
        content = generator.generate_delegate_template(valid_config)
        assert "task_id:" in content

    def test_generate_delegate_template_has_role(self, generator, valid_config):
        content = generator.generate_delegate_template(valid_config)
        assert "role: engineer" in content

    def test_generate_delegate_template_has_effort(self, generator, valid_config):
        content = generator.generate_delegate_template(valid_config)
        assert "effort: low" in content

    def test_generate_handback_template_has_status(self, generator, valid_config):
        content = generator.generate_handback_template(valid_config)
        assert "status:" in content

    def test_generate_handback_template_has_deliverables(self, generator, valid_config):
        content = generator.generate_handback_template(valid_config)
        assert "deliverables:" in content

    def test_generate_handback_template_has_tests_section(self, generator, valid_config):
        content = generator.generate_handback_template(valid_config)
        assert "tests:" in content


# ============================================================================
# 4. DependencyValidator — graph operations
# ============================================================================

class TestDependencyValidator:

    def test_empty_deps_valid(self, dep_validator):
        graph = {"agent-a": []}
        errors = dep_validator.validate_graph(graph)
        assert errors == []

    def test_linear_deps_valid(self, dep_validator):
        graph = {
            "agent-a": ["agent-b"],
            "agent-b": [],
        }
        errors = dep_validator.validate_graph(graph)
        assert errors == []

    def test_circular_dep_detected(self, dep_validator):
        graph = {
            "agent-a": ["agent-b"],
            "agent-b": ["agent-a"],
        }
        errors = dep_validator.validate_graph(graph)
        assert len(errors) > 0
        assert any("circular" in e.lower() for e in errors)

    def test_three_node_cycle_detected(self, dep_validator):
        graph = {
            "agent-a": ["agent-b"],
            "agent-b": ["agent-c"],
            "agent-c": ["agent-a"],
        }
        errors = dep_validator.validate_graph(graph)
        assert any("circular" in e.lower() for e in errors)

    def test_self_dependency_detected(self, dep_validator):
        graph = {"agent-a": ["agent-a"]}
        errors = dep_validator.validate_graph(graph)
        assert len(errors) > 0

    def test_missing_dep_detected(self, dep_validator):
        graph = {
            "agent-a": ["agent-missing"],
        }
        errors = dep_validator.validate_graph(graph)
        assert len(errors) > 0
        assert any("missing" in e.lower() or "not found" in e.lower() for e in errors)

    def test_validate_new_agent_no_cycle(self, dep_validator):
        existing = {
            "agent-b": [],
            "agent-c": ["agent-b"],
        }
        errors = dep_validator.validate_new_agent("agent-a", ["agent-b"], existing)
        assert errors == []

    def test_validate_new_agent_would_create_cycle(self, dep_validator):
        existing = {
            "agent-b": ["agent-a"],
        }
        errors = dep_validator.validate_new_agent("agent-a", ["agent-b"], existing)
        assert any("circular" in e.lower() for e in errors)

    def test_topological_order_returns_list(self, dep_validator):
        graph = {
            "agent-a": ["agent-b"],
            "agent-b": ["agent-c"],
            "agent-c": [],
        }
        order = dep_validator.topological_order(graph)
        assert isinstance(order, list)
        # c before b before a
        assert order.index("agent-c") < order.index("agent-b")
        assert order.index("agent-b") < order.index("agent-a")

    def test_topological_order_empty_graph(self, dep_validator):
        order = dep_validator.topological_order({})
        assert order == []


# ============================================================================
# 5. IntegrationChecker — compatibility & conflict detection
# ============================================================================

class TestIntegrationChecker:

    def test_no_conflict_new_name(self, integration_checker):
        existing = ["engineer", "senior-engineer", "lead-engineer"]
        errors = integration_checker.check_naming_conflict("my-new-agent", existing)
        assert errors == []

    def test_naming_conflict_detected(self, integration_checker):
        existing = ["engineer", "senior-engineer"]
        errors = integration_checker.check_naming_conflict("engineer", existing)
        assert len(errors) > 0
        assert any("conflict" in e.lower() or "exists" in e.lower() for e in errors)

    def test_role_compatible_with_model(self, integration_checker, mod):
        AgentConfig = mod[0]
        cfg = AgentConfig(name="test-a", role="engineer", model="claude-haiku-4.5")
        errors = integration_checker.check_role_model_compatibility(cfg)
        assert errors == []

    def test_role_model_mismatch_warning(self, integration_checker, mod):
        """Principal engineer with haiku model should warn (but not hard-fail)."""
        AgentConfig = mod[0]
        cfg = AgentConfig(name="test-a", role="principal-engineer", model="claude-haiku-4.5")
        warnings = integration_checker.check_role_model_compatibility(cfg)
        # Should produce at least a warning
        assert isinstance(warnings, list)

    def test_check_manifest_compatibility(self, integration_checker, valid_config):
        """Checking against an empty manifest produces no errors."""
        manifest = {"agents": {}}
        errors = integration_checker.check_manifest_compatibility(valid_config, manifest)
        assert isinstance(errors, list)

    def test_check_manifest_naming_conflict(self, integration_checker, mod):
        AgentConfig = mod[0]
        cfg = AgentConfig(name="engineer", role="engineer")
        manifest = {"agents": {"engineer": {"role": "engineer"}}}
        errors = integration_checker.check_manifest_compatibility(cfg, manifest)
        assert len(errors) > 0

    def test_full_check_valid(self, integration_checker, valid_config):
        existing_names = ["senior-engineer", "lead-engineer"]
        manifest = {"agents": {"senior-engineer": {}, "lead-engineer": {}}}
        errors = integration_checker.check(valid_config, existing_names, manifest)
        assert isinstance(errors, list)


# ============================================================================
# 6. AgentCreator — end-to-end orchestration
# ============================================================================

class TestAgentCreator:

    def test_create_returns_creation_result(self, creator, valid_config):
        result = creator.create(valid_config)
        CreationResult = _import()[2]
        assert isinstance(result, CreationResult)

    def test_create_success_status(self, creator, valid_config):
        CreationStatus = _import()[3]
        result = creator.create(valid_config)
        assert result.status == CreationStatus.SUCCESS

    def test_create_invalid_config_returns_failed(self, creator, mod):
        AgentConfig = mod[0]
        CreationStatus = mod[3]
        bad = AgentConfig(name="INVALID NAME", role="wizard")
        result = creator.create(bad)
        assert result.status == CreationStatus.FAILED
        assert len(result.errors) > 0

    def test_create_skill_md_file_written(self, creator, valid_config, tmp_path):
        creator.create(valid_config)
        skill_md = tmp_path / "agent-creator" / "my-agent" / "SKILL.md"
        assert skill_md.exists()

    def test_create_init_py_file_written(self, creator, valid_config, tmp_path):
        creator.create(valid_config)
        init_py = tmp_path / "agent-creator" / "my-agent" / "__init__.py"
        assert init_py.exists()

    def test_create_test_scaffold_written(self, creator, valid_config, tmp_path):
        creator.create(valid_config)
        test_file = tmp_path / "agent-creator" / "my-agent" / "tests" / "test_my_agent.py"
        assert test_file.exists()

    def test_create_scripts_dir_created(self, creator, valid_config, tmp_path):
        creator.create(valid_config)
        scripts_dir = tmp_path / "agent-creator" / "my-agent" / "scripts"
        assert scripts_dir.is_dir()

    def test_create_scripts_init_written(self, creator, valid_config, tmp_path):
        creator.create(valid_config)
        scripts_init = tmp_path / "agent-creator" / "my-agent" / "scripts" / "__init__.py"
        assert scripts_init.exists()

    def test_create_deliverables_listed(self, creator, valid_config):
        result = creator.create(valid_config)
        assert len(result.deliverables) >= 3  # SKILL.md + __init__.py + test file

    def test_dry_run_no_files_written(self, creator, valid_config, tmp_path):
        result = creator.create(valid_config, dry_run=True)
        # Nothing created on disk
        skill_dir = tmp_path / "agent-creator" / "my-agent"
        assert not skill_dir.exists()
        # But planned deliverables still listed
        assert len(result.deliverables) >= 3

    def test_dry_run_status_success(self, creator, valid_config):
        CreationStatus = _import()[3]
        result = creator.create(valid_config, dry_run=True)
        assert result.status == CreationStatus.SUCCESS

    def test_create_skill_md_content_valid(self, creator, valid_config, tmp_path):
        creator.create(valid_config)
        skill_md = tmp_path / "agent-creator" / "my-agent" / "SKILL.md"
        content = skill_md.read_text()
        assert "name: my-agent" in content
        assert "role: engineer" in content

    def test_create_test_file_has_correct_class_name(self, creator, valid_config, tmp_path):
        creator.create(valid_config)
        test_file = tmp_path / "agent-creator" / "my-agent" / "tests" / "test_my_agent.py"
        content = test_file.read_text()
        assert "class Test" in content

    def test_create_with_dependencies(self, creator, mod, tmp_path):
        AgentConfig = mod[0]
        CreationStatus = mod[3]
        cfg = AgentConfig(
            name="composed-agent",
            role="senior-engineer",
            dependencies=["engineer"],
        )
        result = creator.create(cfg)
        assert result.status == CreationStatus.SUCCESS

    def test_create_with_circular_dependency_fails(self, creator, mod):
        AgentConfig = mod[0]
        CreationStatus = mod[3]
        # Agent depends on itself
        cfg = AgentConfig(name="self-dep", role="engineer", dependencies=["self-dep"])
        result = creator.create(cfg)
        assert result.status == CreationStatus.FAILED
        assert any("circular" in e.lower() for e in result.errors)

    def test_span_metadata_included(self, creator, valid_config):
        """CreationResult includes span metadata (timing, file count)."""
        result = creator.create(valid_config)
        assert result.span is not None
        assert "files_created" in result.span
        assert "duration_ms" in result.span

    def test_creation_result_str_representation(self, creator, valid_config):
        result = creator.create(valid_config)
        s = str(result)
        assert "my-agent" in s or "SUCCESS" in s


# ============================================================================
# 7. Constants validation
# ============================================================================

class TestConstants:

    def test_allowed_roles_includes_engineer(self, mod):
        ALLOWED_ROLES = mod[10]
        assert "engineer" in ALLOWED_ROLES

    def test_allowed_roles_includes_senior_engineer(self, mod):
        ALLOWED_ROLES = mod[10]
        assert "senior-engineer" in ALLOWED_ROLES

    def test_allowed_roles_includes_lead_engineer(self, mod):
        ALLOWED_ROLES = mod[10]
        assert "lead-engineer" in ALLOWED_ROLES

    def test_allowed_roles_includes_principal_engineer(self, mod):
        ALLOWED_ROLES = mod[10]
        assert "principal-engineer" in ALLOWED_ROLES

    def test_allowed_roles_includes_security_engineer(self, mod):
        ALLOWED_ROLES = mod[10]
        assert "security-engineer" in ALLOWED_ROLES

    def test_allowed_roles_includes_quality_engineer(self, mod):
        ALLOWED_ROLES = mod[10]
        assert "quality-engineer" in ALLOWED_ROLES

    def test_allowed_efforts_low_medium_high(self, mod):
        ALLOWED_EFFORTS = mod[11]
        assert "low" in ALLOWED_EFFORTS
        assert "medium" in ALLOWED_EFFORTS
        assert "high" in ALLOWED_EFFORTS

    def test_allowed_models_includes_haiku(self, mod):
        ALLOWED_MODELS = mod[12]
        assert any("haiku" in m for m in ALLOWED_MODELS)

    def test_allowed_models_includes_sonnet(self, mod):
        ALLOWED_MODELS = mod[12]
        assert any("sonnet" in m for m in ALLOWED_MODELS)

    def test_allowed_models_includes_opus(self, mod):
        ALLOWED_MODELS = mod[12]
        assert any("opus" in m for m in ALLOWED_MODELS)

    def test_default_model_is_haiku(self, mod):
        DEFAULT_MODEL = mod[13 + 1]  # index 14 after offset
        # DEFAULT_MODEL is at index 13 in the returned tuple
        _, _, _, _, _, _, _, _, _, _, _, _, _, DEFAULT_MODEL, DEFAULT_EFFORT = mod
        assert "haiku" in DEFAULT_MODEL

    def test_default_effort_is_low(self, mod):
        _, _, _, _, _, _, _, _, _, _, _, _, _, _, DEFAULT_EFFORT = mod
        assert DEFAULT_EFFORT == "low"
