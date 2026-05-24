"""
Tests for workflow-review skill.

Tests:
- WorkflowReport dataclass construction
- WorkflowReviewer initialization
- diagram generation
- consistency checks
- cycle detection
- unused agent detection
- missing quality gate detection
- full review() integration
- CLI-style invocation
- edge cases (empty manifest, missing fields, etc.)
"""
import pytest
import sys
import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Load module via importlib (supports hyphenated directory name)
# ---------------------------------------------------------------------------
import importlib.util

_SKILL_SCRIPT = (
    Path(__file__).parent.parent
    / "src"
    / "skills"
    / "workflow-review"
    / "scripts"
    / "workflow_review.py"
)

_spec = importlib.util.spec_from_file_location("workflow_review", _SKILL_SCRIPT)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

WorkflowReviewer = _module.WorkflowReviewer
WorkflowReport = _module.WorkflowReport
WorkflowNode = _module.WorkflowNode
WorkflowEdge = _module.WorkflowEdge
WorkflowDiagram = _module.WorkflowDiagram
WorkflowConsistencyChecker = _module.WorkflowConsistencyChecker
CycleDetector = _module.CycleDetector

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_MANIFEST = {
    "version": "1.0",
    "agents": {
        "orchestrator": {
            "name": "Orchestrator",
            "type": "routing",
            "status": "active",
            "description": "Routes tasks",
            "model": "claude-haiku-4.5",
        },
        "engineer": {
            "name": "Engineer",
            "type": "implementation",
            "status": "active",
            "description": "Implements tasks",
            "model": "claude-haiku-4.5",
        },
        "quality-engineer": {
            "name": "Quality Engineer",
            "type": "validation",
            "status": "active",
            "description": "Validates work",
            "model": "claude-sonnet-4.6",
        },
    },
    "skills": {},
}

NO_SKILLS_MANIFEST = {
    "version": "1.0",
    "agents": {
        "orchestrator": {
            "name": "Orchestrator",
            "type": "routing",
            "status": "active",
            "description": "Routes tasks",
            "model": "claude-haiku-4.5",
        },
    },
    # No 'skills' key at all
}

EMPTY_MANIFEST = {}


def _write_tmp_manifest(data):
    """Write a YAML manifest to a NamedTemporaryFile and return its Path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    )
    yaml.dump(data, tmp)
    tmp.close()
    return Path(tmp.name)


# ---------------------------------------------------------------------------
# 1. WorkflowReport dataclass fields
# ---------------------------------------------------------------------------

class TestWorkflowReportDataclass:
    def test_has_timestamp_field(self):
        """WorkflowReport has timestamp field."""
        r = WorkflowReport(
            timestamp="2026-01-01T00:00:00Z",
            diagram="",
            consistency_checklist={},
            cycles_detected=[],
            unused_agents=[],
            missing_quality_gates=[],
            recommendations=[],
            quality_score=100.0,
            passed=True,
        )
        assert r.timestamp == "2026-01-01T00:00:00Z"

    def test_has_diagram_field(self):
        r = WorkflowReport(
            timestamp="t",
            diagram="DIAGRAM",
            consistency_checklist={},
            cycles_detected=[],
            unused_agents=[],
            missing_quality_gates=[],
            recommendations=[],
            quality_score=80.0,
            passed=True,
        )
        assert r.diagram == "DIAGRAM"

    def test_has_quality_score_field(self):
        r = WorkflowReport(
            timestamp="t",
            diagram="",
            consistency_checklist={},
            cycles_detected=[],
            unused_agents=[],
            missing_quality_gates=[],
            recommendations=[],
            quality_score=55.5,
            passed=False,
        )
        assert r.quality_score == 55.5

    def test_has_passed_field(self):
        r = WorkflowReport(
            timestamp="t",
            diagram="",
            consistency_checklist={},
            cycles_detected=[],
            unused_agents=[],
            missing_quality_gates=[],
            recommendations=[],
            quality_score=0.0,
            passed=False,
        )
        assert r.passed is False

    def test_all_required_fields_exist(self):
        """All 9 required fields are present."""
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(WorkflowReport)}
        required = {
            "timestamp", "diagram", "consistency_checklist", "cycles_detected",
            "unused_agents", "missing_quality_gates", "recommendations",
            "quality_score", "passed",
        }
        assert required.issubset(field_names)


# ---------------------------------------------------------------------------
# 2. WorkflowReviewer initialization
# ---------------------------------------------------------------------------

class TestWorkflowReviewerInit:
    def test_can_be_instantiated_with_path(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            assert reviewer is not None
        finally:
            os.unlink(manifest_path)

    def test_can_be_instantiated_without_args(self):
        reviewer = WorkflowReviewer()
        assert reviewer is not None

    def test_stores_manifest_path(self):
        p = Path("/tmp/fake.yaml")
        reviewer = WorkflowReviewer(p)
        assert reviewer.manifest_path == p


# ---------------------------------------------------------------------------
# 3. Diagram generation
# ---------------------------------------------------------------------------

class TestGenerateDiagram:
    def test_returns_non_empty_string(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            diagram = reviewer.generate_diagram()
            assert isinstance(diagram, str)
            assert len(diagram) > 0
        finally:
            os.unlink(manifest_path)

    def test_contains_agent_names(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            diagram = reviewer.generate_diagram()
            # Should reference at least one agent from the manifest
            assert "Orchestrator" in diagram or "Engineer" in diagram or "DELEGATE" in diagram
        finally:
            os.unlink(manifest_path)

    def test_contains_header(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            diagram = reviewer.generate_diagram()
            assert "AGENT WORKFLOW DIAGRAM" in diagram
        finally:
            os.unlink(manifest_path)

    def test_contains_delegate_keyword(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            diagram = reviewer.generate_diagram()
            assert "DELEGATE" in diagram
        finally:
            os.unlink(manifest_path)

    def test_diagram_with_empty_manifest(self):
        """Empty manifest should still produce a diagram without error."""
        manifest_path = _write_tmp_manifest(EMPTY_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            diagram = reviewer.generate_diagram()
            assert isinstance(diagram, str)
        finally:
            os.unlink(manifest_path)


# ---------------------------------------------------------------------------
# 4. Consistency checks
# ---------------------------------------------------------------------------

class TestCheckConsistency:
    def test_returns_dict_with_required_keys(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            result = reviewer.check_consistency()
            assert isinstance(result, dict)
            assert "passed" in result
            assert "failed" in result
            assert "warnings" in result
        finally:
            os.unlink(manifest_path)

    def test_passed_is_list(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            result = reviewer.check_consistency()
            assert isinstance(result["passed"], list)
        finally:
            os.unlink(manifest_path)

    def test_failed_is_list(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            result = reviewer.check_consistency()
            assert isinstance(result["failed"], list)
        finally:
            os.unlink(manifest_path)

    def test_orchestrator_agent_passes_has_orchestrator(self):
        """Manifest with orchestrator agent -> has_orchestrator in passed."""
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            result = reviewer.check_consistency()
            assert "has_orchestrator" in result["passed"]
        finally:
            os.unlink(manifest_path)

    def test_validation_agent_passes_has_quality_gates(self):
        """Manifest with validation-type agent -> has_quality_gates in passed."""
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            result = reviewer.check_consistency()
            assert "has_quality_gates" in result["passed"]
        finally:
            os.unlink(manifest_path)

    def test_missing_skills_section_handled_gracefully(self):
        """Manifest without skills section does not raise."""
        manifest_path = _write_tmp_manifest(NO_SKILLS_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            result = reviewer.check_consistency()
            assert isinstance(result, dict)
        finally:
            os.unlink(manifest_path)

    def test_empty_manifest_handled_gracefully(self):
        """Completely empty manifest does not raise."""
        manifest_path = _write_tmp_manifest(EMPTY_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            result = reviewer.check_consistency()
            assert isinstance(result, dict)
        finally:
            os.unlink(manifest_path)

    def test_agents_documented_passes_when_all_have_descriptions(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            result = reviewer.check_consistency()
            assert "agents_documented" in result["passed"]
        finally:
            os.unlink(manifest_path)

    def test_agents_documented_fails_when_description_missing(self):
        bad_manifest = {
            "agents": {
                "engineer": {
                    "name": "Engineer",
                    "type": "implementation",
                    "status": "active",
                    "description": "",
                    "model": "claude-haiku-4.5",
                }
            }
        }
        manifest_path = _write_tmp_manifest(bad_manifest)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            result = reviewer.check_consistency()
            assert "agents_documented" in result["failed"]
        finally:
            os.unlink(manifest_path)


# ---------------------------------------------------------------------------
# 5. Cycle detection
# ---------------------------------------------------------------------------

class TestDetectCycles:
    def test_returns_list(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            cycles = reviewer.detect_cycles()
            assert isinstance(cycles, list)
        finally:
            os.unlink(manifest_path)

    def test_no_cycles_in_valid_manifest(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            cycles = reviewer.detect_cycles()
            assert cycles == []
        finally:
            os.unlink(manifest_path)

    def test_cycle_detector_direct(self):
        """CycleDetector with a hand-built cyclic adjacency detects the cycle."""
        nodes = [
            WorkflowNode("A", "a", "routing", "desc", "model", "active"),
            WorkflowNode("B", "b", "implementation", "desc", "model", "active"),
        ]
        detector = CycleDetector(nodes)
        # Inject a cycle manually into the adjacency
        detector.adjacency = {"A": ["B"], "B": ["A"]}
        cycles = detector.detect()
        assert len(cycles) > 0


# ---------------------------------------------------------------------------
# 6. Full review()
# ---------------------------------------------------------------------------

class TestReview:
    def test_returns_workflow_report_instance(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            report = reviewer.review()
            assert isinstance(report, WorkflowReport)
        finally:
            os.unlink(manifest_path)

    def test_passed_is_bool(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            report = reviewer.review()
            assert isinstance(report.passed, bool)
        finally:
            os.unlink(manifest_path)

    def test_quality_score_between_0_and_100(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            report = reviewer.review()
            assert 0.0 <= report.quality_score <= 100.0
        finally:
            os.unlink(manifest_path)

    def test_diagram_is_non_empty_string(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            report = reviewer.review()
            assert isinstance(report.diagram, str)
            assert len(report.diagram) > 0
        finally:
            os.unlink(manifest_path)

    def test_recommendations_is_list(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            report = reviewer.review()
            assert isinstance(report.recommendations, list)
        finally:
            os.unlink(manifest_path)

    def test_timestamp_is_string(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            report = reviewer.review()
            assert isinstance(report.timestamp, str)
            assert len(report.timestamp) > 0
        finally:
            os.unlink(manifest_path)

    def test_cycles_detected_is_list(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            report = reviewer.review()
            assert isinstance(report.cycles_detected, list)
        finally:
            os.unlink(manifest_path)

    def test_unused_agents_is_list(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            report = reviewer.review()
            assert isinstance(report.unused_agents, list)
        finally:
            os.unlink(manifest_path)

    def test_quality_score_healthy_manifest_passes(self):
        """Healthy manifest (orchestrator + quality-engineer) should have score >= 70."""
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            report = reviewer.review()
            assert report.quality_score >= 70.0
            assert report.passed is True
        finally:
            os.unlink(manifest_path)

    def test_missing_quality_gates_is_list(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            report = reviewer.review()
            assert isinstance(report.missing_quality_gates, list)
        finally:
            os.unlink(manifest_path)

    def test_consistency_checklist_has_expected_structure(self):
        manifest_path = _write_tmp_manifest(MINIMAL_MANIFEST)
        try:
            reviewer = WorkflowReviewer(manifest_path)
            report = reviewer.review()
            cl = report.consistency_checklist
            assert "passed" in cl
            assert "failed" in cl
            assert "warnings" in cl
        finally:
            os.unlink(manifest_path)


# ---------------------------------------------------------------------------
# 7. Real FRAMEWORK-MANIFEST.yaml integration
# ---------------------------------------------------------------------------

class TestRealManifest:
    REAL_MANIFEST = Path("config/FRAMEWORK-MANIFEST.yaml")

    def test_real_manifest_agents_are_processed(self):
        """All agents in the real FRAMEWORK-MANIFEST.yaml are loaded."""
        if not self.REAL_MANIFEST.exists():
            pytest.skip("config/FRAMEWORK-MANIFEST.yaml not found")
        reviewer = WorkflowReviewer(self.REAL_MANIFEST)
        report = reviewer.review()
        # Real manifest has 8 agents; at minimum we expect > 0
        assert len(reviewer._build_nodes()) > 0

    def test_real_manifest_review_returns_report(self):
        if not self.REAL_MANIFEST.exists():
            pytest.skip("config/FRAMEWORK-MANIFEST.yaml not found")
        reviewer = WorkflowReviewer(self.REAL_MANIFEST)
        report = reviewer.review()
        assert isinstance(report, WorkflowReport)

    def test_real_manifest_quality_score_is_valid(self):
        if not self.REAL_MANIFEST.exists():
            pytest.skip("config/FRAMEWORK-MANIFEST.yaml not found")
        reviewer = WorkflowReviewer(self.REAL_MANIFEST)
        report = reviewer.review()
        assert 0.0 <= report.quality_score <= 100.0

    def test_real_manifest_passes(self):
        """The real framework manifest should yield a passing quality score."""
        if not self.REAL_MANIFEST.exists():
            pytest.skip("config/FRAMEWORK-MANIFEST.yaml not found")
        reviewer = WorkflowReviewer(self.REAL_MANIFEST)
        report = reviewer.review()
        assert report.quality_score >= 70.0, (
            "Real manifest quality score too low: {:.1f}. Failed: {}".format(
                report.quality_score, report.consistency_checklist.get("failed", [])
            )
        )
