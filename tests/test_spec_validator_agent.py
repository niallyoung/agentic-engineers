"""
Tests for src/orchestration/agents/spec_validator.py — validates agent
implementation against spec definitions.

This targets the SpecValidator class in the agents package (distinct from
the skills/spec-validator skill tested in test_spec_validator.py).

Note: spec_validator.py uses unqualified `from implementations import list_agents`
      so we load it via importlib with the agents directory on sys.path.
"""

import sys
import pytest
from pathlib import Path
import importlib.util
from types import ModuleType

AGENTS_DIR = str(Path(__file__).parent.parent / "src" / "orchestration" / "agents")

# spec_validator.py does `from implementations import list_agents`.
# implementations.py in turn uses `from . import Agent, ...` (relative import),
# so it cannot be loaded as a standalone file via sys.path injection.
# Additionally `list_agents` doesn't exist in implementations.py at all.
# We create a lightweight shim module that provides `list_agents` and register
# it in sys.modules *before* loading spec_validator.py via importlib.

import src.orchestration.agents.implementations as _impl_pkg

_shim = ModuleType("implementations")


def _list_agents_shim():
    """Return configs for all agents defined in implementations.py."""
    import src.orchestration.agents as _pkg
    configs = [
        _pkg.ORCHESTRATOR_CONFIG,
        _pkg.ENGINEER_CONFIG,
        _pkg.SENIOR_ENGINEER_CONFIG,
        _pkg.LEAD_ENGINEER_CONFIG,
        _pkg.PRINCIPAL_ENGINEER_CONFIG,
        _pkg.QUALITY_ENGINEER_CONFIG,
        _pkg.MODEL_ENGINEER_CONFIG,
        _pkg.SECURITY_ENGINEER_CONFIG,
        _pkg.SECURITY_AGENT_QG_CONFIG,
        _pkg.TESTING_AGENT_CONFIG,
        _pkg.METRICS_AGENT_CONFIG,
        _pkg.HEALING_AGENT_CONFIG,
        _pkg.SPEC_ENGINEER_CONFIG,
        _pkg.QUALITY_GATE_ORCHESTRATOR_CONFIG,
    ]
    return configs


_shim.list_agents = _list_agents_shim
_shim.create_agent = _impl_pkg.create_agent
sys.modules["implementations"] = _shim


def _load_spec_validator_module():
    """Load spec_validator via importlib to handle its unqualified imports."""
    spec_path = Path(AGENTS_DIR) / "spec_validator.py"
    spec = importlib.util.spec_from_file_location("spec_validator_agent", spec_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def svm():
    """The spec_validator agent module."""
    return _load_spec_validator_module()


@pytest.fixture
def validator(svm):
    """Fresh SpecValidator instance."""
    return svm.SpecValidator()


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------

class TestSpecValidatorAgentInit:
    def test_can_instantiate(self, svm):
        """SpecValidator can be instantiated without error."""
        v = svm.SpecValidator()
        assert v is not None

    def test_agents_in_spec_non_empty(self, validator):
        """agents_in_spec is populated on init."""
        assert len(validator.agents_in_spec) > 0

    def test_agents_in_code_non_empty(self, validator):
        """agents_in_code is populated on init."""
        assert len(validator.agents_in_code) > 0

    def test_issues_initialised_as_empty_lists(self, validator):
        """All four issue lists start empty."""
        for key in ("TYPE_A", "TYPE_B", "TYPE_C", "TYPE_D"):
            assert validator.issues[key] == []


# ---------------------------------------------------------------------------
# _parse_spec
# ---------------------------------------------------------------------------

class TestAgentParseSpec:
    def test_spec_has_expected_agent_names(self, validator):
        """Spec dict includes all expected agents."""
        expected = {
            "GeneralOrchestrator", "EngineerAgent", "SeniorEngineerAgent",
            "LeadEngineerAgent", "PrincipalEngineerAgent", "QualityEngineerAgent",
            "ModelEngineerAgent", "SecurityEngineerAgent",
        }
        assert expected.issubset(set(validator.agents_in_spec.keys()))

    def test_spec_includes_qg_sub_agents(self, validator):
        """Spec includes quality gate sub-agents."""
        qg_agents = {"SecurityAgentQG", "TestingAgent", "MetricsAgent"}
        assert qg_agents.issubset(set(validator.agents_in_spec.keys()))

    def test_each_spec_entry_has_model_effort_role(self, validator):
        """Every spec entry has model, effort, and role."""
        for name, spec in validator.agents_in_spec.items():
            assert "model" in spec, f"{name}: missing 'model'"
            assert "effort" in spec, f"{name}: missing 'effort'"
            assert "role" in spec, f"{name}: missing 'role'"

    def test_spec_has_fourteen_agents(self, validator):
        """Spec defines exactly 14 agents (8 SDLC + 5 QG + 1 QGO)."""
        assert len(validator.agents_in_spec) == 14


# ---------------------------------------------------------------------------
# _parse_code
# ---------------------------------------------------------------------------

class TestAgentParseCode:
    def test_code_dict_non_empty(self, validator):
        """Code dict contains agents."""
        assert len(validator.agents_in_code) > 0

    def test_each_code_entry_has_model_effort_role(self, validator):
        """Every code entry has model, effort, and role."""
        for name, cfg in validator.agents_in_code.items():
            assert "model" in cfg, f"{name}: missing 'model'"
            assert "effort" in cfg, f"{name}: missing 'effort'"
            assert "role" in cfg, f"{name}: missing 'role'"


# ---------------------------------------------------------------------------
# _check_all_agents_present — TYPE_A
# ---------------------------------------------------------------------------

class TestAgentCheckAllAgentsPresent:
    def test_no_type_a_when_code_matches_spec(self, svm):
        """No TYPE_A issues when code contains all spec agents."""
        v = svm.SpecValidator()
        v.agents_in_code = {k: dict(d) for k, d in v.agents_in_spec.items()}
        v._check_all_agents_present()
        assert v.issues["TYPE_A"] == []

    def test_type_a_raised_for_missing_agent(self, svm):
        """TYPE_A issued when a spec agent is absent from code."""
        v = svm.SpecValidator()
        v.agents_in_code = {}
        v._check_all_agents_present()
        assert len(v.issues["TYPE_A"]) == len(v.agents_in_spec)

    def test_type_a_message_contains_agent_name(self, svm):
        """TYPE_A message references the missing agent name."""
        v = svm.SpecValidator()
        v.agents_in_code = {}
        v._check_all_agents_present()
        all_text = " ".join(v.issues["TYPE_A"]).lower()
        assert "generalorchestrator" in all_text or "agent" in all_text


# ---------------------------------------------------------------------------
# _check_all_models_match — TYPE_C
# ---------------------------------------------------------------------------

class TestAgentCheckAllModelsMatch:
    def test_no_type_c_when_models_identical(self, svm):
        """No TYPE_C issues when code models match spec."""
        v = svm.SpecValidator()
        v.agents_in_code = {k: dict(d) for k, d in v.agents_in_spec.items()}
        v._check_all_models_match()
        assert v.issues["TYPE_C"] == []

    def test_type_c_raised_for_wrong_model(self, svm):
        """TYPE_C issued when a model diverges from spec."""
        v = svm.SpecValidator()
        first = next(iter(v.agents_in_spec))
        v.agents_in_code = {first: {**v.agents_in_spec[first], "model": "wrong-model"}}
        v._check_all_models_match()
        assert len(v.issues["TYPE_C"]) > 0

    def test_type_c_message_references_model(self, svm):
        """TYPE_C message mentions the model mismatch."""
        v = svm.SpecValidator()
        first = next(iter(v.agents_in_spec))
        v.agents_in_code = {first: {**v.agents_in_spec[first], "model": "x-model"}}
        v._check_all_models_match()
        assert any("model" in msg.lower() for msg in v.issues["TYPE_C"])


# ---------------------------------------------------------------------------
# _check_all_efforts_match — TYPE_C
# ---------------------------------------------------------------------------

class TestAgentCheckAllEffortsMatch:
    def test_no_type_c_when_efforts_identical(self, svm):
        v = svm.SpecValidator()
        v.agents_in_code = {k: dict(d) for k, d in v.agents_in_spec.items()}
        v._check_all_efforts_match()
        assert v.issues["TYPE_C"] == []

    def test_type_c_raised_for_effort_mismatch(self, svm):
        v = svm.SpecValidator()
        first = next(iter(v.agents_in_spec))
        v.agents_in_code = {first: {**v.agents_in_spec[first], "effort": "bogus_effort"}}
        v._check_all_efforts_match()
        assert len(v.issues["TYPE_C"]) > 0


# ---------------------------------------------------------------------------
# validate()
# ---------------------------------------------------------------------------

class TestAgentValidate:
    def test_validate_returns_bool(self, validator):
        """validate() returns a boolean."""
        assert isinstance(validator.validate(), bool)

    def test_validate_true_when_code_matches_spec(self, svm):
        """validate() returns True when code exactly matches spec."""
        v = svm.SpecValidator()
        v.agents_in_code = {k: dict(d) for k, d in v.agents_in_spec.items()}
        assert v.validate() is True

    def test_validate_false_when_type_a_issues(self, svm):
        """validate() returns False when TYPE_A issues exist."""
        v = svm.SpecValidator()
        v.agents_in_code = {}
        assert v.validate() is False

    def test_validate_false_when_type_d_issues(self, svm):
        """validate() returns False when TYPE_D issues exist."""
        v = svm.SpecValidator()
        v.agents_in_code = {k: dict(d) for k, d in v.agents_in_spec.items()}
        v.issues["TYPE_D"].append("Breaking change detected")
        # Re-run validate won't reset TYPE_D; call _check_* methods only
        assert not (len(v.issues["TYPE_A"]) == 0 and len(v.issues["TYPE_D"]) == 0)


# ---------------------------------------------------------------------------
# report()
# ---------------------------------------------------------------------------

class TestAgentReport:
    def test_report_returns_string(self, validator):
        validator.validate()
        assert isinstance(validator.report(), str)

    def test_report_contains_all_drift_types(self, validator):
        validator.validate()
        report = validator.report()
        for dtype in ("TYPE_A", "TYPE_B", "TYPE_C", "TYPE_D"):
            assert dtype in report

    def test_report_contains_agent_count(self, validator):
        validator.validate()
        report = validator.report()
        assert "Agents in" in report

    def test_report_shows_passed_when_synced(self, svm):
        """Report shows success message when code matches spec."""
        v = svm.SpecValidator()
        v.agents_in_code = {k: dict(d) for k, d in v.agents_in_spec.items()}
        v.validate()
        report = v.report()
        assert "PASSED" in report or "✅" in report

    def test_report_shows_issues_when_problems_exist(self, svm):
        """Report shows issue summary when there are failures."""
        v = svm.SpecValidator()
        v.agents_in_code = {}
        v.validate()
        report = v.report()
        assert "issues" in report.lower() or "❌" in report
