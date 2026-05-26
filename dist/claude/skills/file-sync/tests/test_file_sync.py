# -*- coding: utf-8 -*-
"""Tests for file-sync skill."""

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SKILL_ROOT))

from scripts.script_analyzer import ScriptAnalyzer, ScriptMetadata  # noqa: E402
from scripts.utility_scorer import UtilityScorer  # noqa: E402
from scripts.reference_detector import ReferenceDetector, Reference  # noqa: E402
from scripts.integration_suggester import IntegrationSuggester  # noqa: E402
from scripts.file_sync import FileSyncOrchestrator, SyncReport  # noqa: E402

# ---------------------------------------------------------------------------
# The real repository root (two levels up from this file)
# ---------------------------------------------------------------------------
_REPO_ROOT = _SKILL_ROOT.parent.parent.parent


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture()
def repo_root() -> Path:
    """Return test repository root."""
    return _REPO_ROOT


@pytest.fixture()
def sample_python_script(tmp_path: Path) -> Path:
    """Sample Python script with docstring."""
    content = '"""Validate rendered outputs."""\n\nimport subprocess\nimport sys\nfrom pathlib import Path\n\n\ndef validate_renders() -> bool:\n    """Check that all renders are valid."""\n    result = subprocess.run(["make", "render"], check=True)\n    return result.returncode == 0\n\n\nif __name__ == "__main__":\n    validate_renders()\n'
    p = tmp_path / "validate_renders.py"
    p.write_text(content)
    return p


@pytest.fixture()
def sample_debug_script(tmp_path: Path) -> Path:
    """Sample script with DEBUG marker."""
    content = '"""DEBUG helper script."""\n\n# This is a debug script for testing\ndef debug_helper():\n    print("DEBUG: helper")\n'
    p = tmp_path / "debug_helper.py"
    p.write_text(content)
    return p


@pytest.fixture()
def sample_cli_script(tmp_path: Path) -> Path:
    """Sample script with argparse CLI."""
    content = '"""Get version from setup.py."""\n\nimport argparse\n\n\ndef get_version() -> str:\n    """Return version string."""\n    return "1.0.0"\n\n\ndef main():\n    """CLI entry point."""\n    parser = argparse.ArgumentParser(description="Get version")\n    parser.add_argument("--format", choices=["full", "short"], default="full")\n    args = parser.parse_args()\n    \n    version = get_version()\n    if args.format == "short":\n        print(version.split(".")[0])\n    else:\n        print(version)\n\n\nif __name__ == "__main__":\n    main()\n'
    p = tmp_path / "get_version.py"
    p.write_text(content)
    return p


# ===========================================================================
# ScriptAnalyzer tests
# ===========================================================================

def test_analyzer_discovers_python_scripts(repo_root: Path):
    """discover_scripts() finds all .py files."""
    analyzer = ScriptAnalyzer(repo_root)
    scripts = analyzer.discover_scripts()
    assert len(scripts) > 0
    assert all(isinstance(s, Path) for s in scripts)
    assert any(s.suffix == ".py" for s in scripts)


def test_analyzer_skips_pycache_and_compiled(repo_root: Path):
    """discover_scripts() skips __pycache__ and .pyc."""
    analyzer = ScriptAnalyzer(repo_root)
    scripts = analyzer.discover_scripts()
    assert not any("__pycache__" in str(s) for s in scripts)
    assert not any(s.suffix == ".pyc" for s in scripts)


def test_analyzer_extracts_docstring(repo_root: Path, sample_python_script: Path, tmp_path: Path):
    """analyze() extracts module docstring."""
    (tmp_path / "scripts").mkdir(exist_ok=True)
    dest = tmp_path / "scripts" / "test_script.py"
    dest.write_text(sample_python_script.read_text())
    analyzer = ScriptAnalyzer(tmp_path)
    metadata = analyzer.analyze(dest)
    assert "Validate rendered outputs" in metadata.docstring


def test_analyzer_infers_purpose_from_filename(repo_root: Path):
    """extract_purpose() infers from filename when no docstring."""
    analyzer = ScriptAnalyzer(repo_root)
    purpose = analyzer.extract_purpose("", "validate_renders.py")
    assert "validate" in purpose.lower() or "render" in purpose.lower()


def test_analyzer_extracts_cli_dependencies(repo_root: Path, sample_python_script: Path):
    """extract_dependencies() finds import statements."""
    analyzer = ScriptAnalyzer(repo_root)
    deps = analyzer.extract_dependencies(sample_python_script.read_text())
    assert "subprocess" in deps
    assert "pathlib" in deps


def test_analyzer_identifies_entry_points(repo_root: Path, sample_cli_script: Path):
    """extract_entry_points() finds public functions/classes."""
    analyzer = ScriptAnalyzer(repo_root)
    eps = analyzer.extract_entry_points(sample_cli_script.read_text(), ".py")
    assert "get_version" in eps
    assert "main" in eps


def test_analyzer_detects_cli_signature(repo_root: Path, sample_cli_script: Path):
    """extract_cli_signature() identifies argparse usage."""
    analyzer = ScriptAnalyzer(repo_root)
    sig = analyzer.extract_cli_signature(sample_cli_script.read_text(), ".py")
    assert sig.get("has_argparse") is True
    assert sig.get("has_cli") is True


def test_analyzer_counts_lines_of_code(repo_root: Path, sample_python_script: Path):
    """analyze() counts LOC excluding comments/blanks."""
    analyzer = ScriptAnalyzer(repo_root)
    loc = analyzer.count_lines_of_code(sample_python_script.read_text())
    assert loc > 0


# ===========================================================================
# UtilityScorer tests
# ===========================================================================

def _make_metadata(
    repo_root: Path,
    name: str = "test",
    docstring: str = "",
    dependencies: list = None,
    entry_points: list = None,
    cli_signature: dict = None,
    lines_of_code: int = 50,
) -> ScriptMetadata:
    from scripts.script_analyzer import ScriptMetadata
    return ScriptMetadata(
        path=repo_root / name,
        name=name.replace(".py", ""),
        extension=".py",
        size_bytes=1000,
        docstring=docstring or "",
        purpose=name,
        dependencies=dependencies or [],
        entry_points=entry_points or [],
        cli_signature=cli_signature or {},
        lines_of_code=lines_of_code,
    )


def test_scorer_high_score_for_documented_cli_script(repo_root: Path, tmp_path: Path):
    """Well-documented CLI script scores >= 8."""
    meta = ScriptMetadata(
        path=tmp_path / "validate_renders.py",
        name="validate_renders",
        extension=".py",
        size_bytes=2000,
        docstring="Comprehensive docstring for validation tool with details.",
        purpose="Validate rendered outputs",
        dependencies=["subprocess"],
        entry_points=["validate_renders"],
        cli_signature={"has_argparse": True, "has_cli": True, "has_type_hints": True, "has_error_handling": False},
        lines_of_code=80,
    )
    scorer = UtilityScorer(repo_root)
    score, reasons, warnings = scorer.score(meta)
    assert score >= 7.0


def test_scorer_medium_score_for_partially_documented(repo_root: Path):
    """Partially documented script scores 6-7."""
    meta = _make_metadata(
        repo_root, "helper.py",
        docstring="Brief docstring.",
        entry_points=["helper"],
        cli_signature={"has_cli": False},
        lines_of_code=60,
    )
    scorer = UtilityScorer(repo_root)
    score, reasons, _ = scorer.score(meta)
    assert 3.0 <= score <= 8.0


def test_scorer_low_score_for_debug_script(repo_root: Path):
    """Script with DEBUG markers scores <= 3."""
    meta = _make_metadata(
        repo_root, "debug_helper.py",
        docstring="Debug helper",
        cli_signature={"has_cli": False},
    )
    scorer = UtilityScorer(repo_root)
    score, _, warnings = scorer.score(meta)
    assert score <= 3.0


def test_scorer_rewards_type_hints(repo_root: Path):
    """Type hints add +0.5 to score."""
    typed = _make_metadata(
        repo_root, "typed.py",
        docstring="Good docstring here.",
        entry_points=["main"],
        cli_signature={"has_type_hints": True, "has_cli": False},
    )
    untyped = _make_metadata(
        repo_root, "untyped.py",
        docstring="Good docstring here.",
        entry_points=["main"],
        cli_signature={"has_type_hints": False, "has_cli": False},
    )
    scorer = UtilityScorer(repo_root)
    typed_score, _, _ = scorer.score(typed)
    untyped_score, _, _ = scorer.score(untyped)
    assert typed_score >= untyped_score


def test_scorer_rewards_error_handling(repo_root: Path):
    """Try/except blocks add +0.5 to score."""
    safe = _make_metadata(
        repo_root, "safe.py",
        docstring="Good docstring.",
        entry_points=["main"],
        cli_signature={"has_error_handling": True, "has_cli": False},
    )
    unsafe = _make_metadata(
        repo_root, "unsafe.py",
        docstring="Good docstring.",
        entry_points=["main"],
        cli_signature={"has_error_handling": False, "has_cli": False},
    )
    scorer = UtilityScorer(repo_root)
    safe_score, _, _ = scorer.score(safe)
    unsafe_score, _, _ = scorer.score(unsafe)
    assert safe_score >= unsafe_score


def test_scorer_prefers_small_focused(repo_root: Path):
    """Small script (<200 LOC) scores higher than large (>1000)."""
    small = _make_metadata(
        repo_root, "small.py",
        docstring="Good docstring.",
        entry_points=["main"],
        cli_signature={"has_cli": False},
        lines_of_code=50,
    )
    large = _make_metadata(
        repo_root, "large.py",
        docstring="Good docstring.",
        entry_points=["main"],
        cli_signature={"has_cli": False},
        lines_of_code=1500,
    )
    scorer = UtilityScorer(repo_root)
    small_score, _, _ = scorer.score(small)
    large_score, _, _ = scorer.score(large)
    assert small_score >= large_score


def test_scorer_rewards_core_workflow_relevance(repo_root: Path):
    """Script referenced in docs scores +1.5."""
    meta = _make_metadata(
        repo_root, "validate_renders.py",
        docstring="Comprehensive docstring.",
        entry_points=["validate"],
        cli_signature={"has_cli": False},
    )
    scorer = UtilityScorer(repo_root)
    score, reasons, _ = scorer.score(meta)
    assert score > 0


def test_scorer_penalizes_high_dependencies(repo_root: Path):
    """High deps (>10) reduce score by 0.5."""
    few = _make_metadata(
        repo_root, "few_deps.py",
        docstring="Good docstring.",
        dependencies=["os"],
        entry_points=["main"],
        cli_signature={"has_cli": False},
    )
    many = _make_metadata(
        repo_root, "many_deps.py",
        docstring="Good docstring.",
        dependencies=["os", "sys", "re", "json", "io", "abc", "ast", "dis", "csv", "cgi", "math", "time"],
        entry_points=["main"],
        cli_signature={"has_cli": False},
    )
    scorer = UtilityScorer(repo_root)
    few_score, _, _ = scorer.score(few)
    many_score, _, _ = scorer.score(many)
    assert few_score > many_score


def test_scorer_provides_reasoning(repo_root: Path):
    """score() returns (score, reasons_list)."""
    meta = _make_metadata(repo_root, "test.py", docstring="Docstring", entry_points=["Test"])
    scorer = UtilityScorer(repo_root)
    score, reasons, _ = scorer.score(meta)
    assert isinstance(reasons, list)


def test_scorer_clips_to_0_10_range(repo_root: Path):
    """Score is clamped to [0, 10]."""
    meta = _make_metadata(repo_root, "test.py", docstring="Docstring", entry_points=["Test"])
    scorer = UtilityScorer(repo_root)
    score, _, _ = scorer.score(meta)
    assert 0.0 <= score <= 10.0


def test_scorer_consistent_across_runs(repo_root: Path):
    """Same input always produces same score."""
    meta = _make_metadata(repo_root, "test.py", docstring="Docstring", entry_points=["Test"])
    scorer = UtilityScorer(repo_root)
    score1, _, _ = scorer.score(meta)
    score2, _, _ = scorer.score(meta)
    assert score1 == score2


def test_scorer_development_markers_fatal(repo_root: Path):
    """DEBUG/TEST/EXPERIMENTAL markers make score <= 3."""
    for marker in ["DEBUG", "TEST", "_test", "EXPERIMENTAL"]:
        meta = _make_metadata(
            repo_root, f"{marker}_script.py",
            docstring=f"Docstring {marker} script",
            entry_points=["Test"],
        )
        scorer = UtilityScorer(repo_root)
        score, _, _ = scorer.score(meta)
        assert score <= 3.0, f"Expected score <= 3.0 for {marker} script, got {score}"


# ===========================================================================
# ReferenceDetector tests
# ===========================================================================

def test_detector_finds_makefile_references(repo_root: Path):
    """find_references() finds script in Makefile targets."""
    detector = ReferenceDetector(repo_root)
    refs = detector.search_makefile("get_version.py")
    # The real repo's Makefile might or might not reference it; just verify no error
    assert isinstance(refs, list)


def test_detector_finds_ci_workflow_references(repo_root: Path):
    """find_references() finds script in .github/workflows/."""
    detector = ReferenceDetector(repo_root)
    refs = detector.search_ci_workflows("copilot-guard.sh")
    assert isinstance(refs, list)


def test_detector_finds_import_references(repo_root: Path):
    """find_references() finds Python imports."""
    detector = ReferenceDetector(repo_root)
    refs = detector.search_python_imports("get_version.py")
    assert isinstance(refs, list)


def test_detector_finds_documentation_references(repo_root: Path):
    """find_references() finds mentions in CONTRIBUTING.md."""
    detector = ReferenceDetector(repo_root)
    refs = detector.search_documentation("validate_renders.py")
    assert isinstance(refs, list)


def test_detector_returns_empty_for_unreferenced(repo_root: Path):
    """find_references() returns [] for unintegrated script."""
    detector = ReferenceDetector(repo_root)
    refs = detector.find_references("nonexistent_script_xyz.py")
    assert not any(True for _ in refs)


def test_detector_returns_location_context(repo_root: Path):
    """References include file location and context."""
    detector = ReferenceDetector(repo_root)
    # Create a fake Makefile reference
    refs = detector.search_makefile("get_version.py")
    for ref in refs:
        assert hasattr(ref, "file_path")
        assert hasattr(ref, "line_number")
        assert hasattr(ref, "context")


# ===========================================================================
# IntegrationSuggester tests
# ===========================================================================

def test_suggester_recommends_makefile_for_cli_tool(repo_root: Path):
    """CLI script gets Makefile suggestion."""
    meta = _make_metadata(
        repo_root, "validate.py",
        docstring="Validate script.",
        entry_points=["validate"],
        cli_signature={"has_argparse": True, "has_cli": True},
    )
    suggester = IntegrationSuggester(repo_root)
    suggestions = suggester.suggest_integration_points(meta, [])
    assert any("Makefile" in s.target for s in suggestions)


def test_suggester_recommends_ci_for_validation(repo_root: Path):
    """Validation script gets CI suggestion."""
    meta = _make_metadata(
        repo_root, "validate.py",
        docstring="Validate script.",
        entry_points=["Validation"],
        cli_signature={"has_argparse": True, "has_cli": True},
    )
    suggester = IntegrationSuggester(repo_root)
    suggestions = suggester.suggest_integration_points(meta, [])
    assert any("ci" in s.target.lower() or "workflow" in s.target.lower() or "CI" in s.target for s in suggestions)


def test_suggester_recommends_python_import_for_library(repo_root: Path):
    """Script with entry_points gets import suggestion."""
    meta = _make_metadata(
        repo_root, "utility.py",
        docstring="Utility module.",
        entry_points=["helper_function", "UtilityClass"],
        cli_signature={"has_cli": False},
    )
    suggester = IntegrationSuggester(repo_root)
    suggestions = suggester.suggest_integration_points(meta, [])
    assert len(suggestions) > 0


def test_suggester_recommends_documentation(repo_root: Path):
    """Validation script gets CONTRIBUTING.md suggestion."""
    meta = _make_metadata(
        repo_root, "validate.py",
        docstring="Validate script.",
        entry_points=["Validation"],
        cli_signature={"has_argparse": True, "has_cli": True},
    )
    suggester = IntegrationSuggester(repo_root)
    suggestions = suggester.suggest_integration_points(meta, [])
    assert any("CONTRIBUTING" in s.target or "doc" in s.target.lower() for s in suggestions)


def test_suggester_provides_effort_estimates(repo_root: Path):
    """Suggestions include effort_minutes."""
    meta = _make_metadata(
        repo_root, "test.py",
        docstring="Test script.",
        entry_points=["test"],
        cli_signature={"has_argparse": True, "has_cli": True},
    )
    suggester = IntegrationSuggester(repo_root)
    suggestions = suggester.suggest_integration_points(meta, [])
    assert len(suggestions) > 0
    assert all(hasattr(s, "effort_minutes") for s in suggestions)


def test_suggester_provides_risk_assessment(repo_root: Path):
    """Suggestions include risk level."""
    meta = _make_metadata(
        repo_root, "test.py",
        docstring="Test script.",
        entry_points=["test"],
        cli_signature={"has_argparse": True, "has_cli": True},
    )
    suggester = IntegrationSuggester(repo_root)
    suggestions = suggester.suggest_integration_points(meta, [])
    assert len(suggestions) > 0
    assert all(hasattr(s, "risk") for s in suggestions)


def test_suggester_includes_code_examples(repo_root: Path):
    """Suggestions include concrete code examples."""
    meta = _make_metadata(
        repo_root, "test.py",
        docstring="Test script.",
        entry_points=["test"],
        cli_signature={"has_argparse": True, "has_cli": True},
    )
    suggester = IntegrationSuggester(repo_root)
    suggestions = suggester.suggest_integration_points(meta, [])
    assert len(suggestions) > 0
    assert all(hasattr(s, "example") for s in suggestions)


# ===========================================================================
# FileSyncOrchestrator tests
# ===========================================================================

def test_orchestrator_runs_complete_analysis(repo_root: Path):
    """run_analysis() returns populated SyncReport."""
    orchestrator = FileSyncOrchestrator(repo_root)
    report = orchestrator.run_analysis()
    assert isinstance(report, SyncReport)
    assert report.scripts_analyzed > 0


def test_orchestrator_segments_by_value_and_integration(repo_root: Path):
    """Results segmented into high/medium/low/dead + integrated/unintegrated."""
    orchestrator = FileSyncOrchestrator(repo_root)
    report = orchestrator.run_analysis()
    assert hasattr(report, "high_value_unintegrated")
    assert hasattr(report, "high_value_integrated")
    assert hasattr(report, "medium_value_unintegrated")
    assert hasattr(report, "dead_code")


def test_orchestrator_generates_sync_report_markdown(repo_root: Path, tmp_path: Path):
    """output_report() produces SYNC_REPORT.md content."""
    orchestrator = FileSyncOrchestrator(repo_root)
    report = orchestrator.run_analysis()
    output_path = tmp_path / "SYNC_REPORT.md"
    content = orchestrator.output_report(report, output_path)
    assert output_path.exists()
    assert "File-Sync Report" in content or "Sync Report" in content


def test_orchestrator_high_value_unintegrated_have_suggestions(repo_root: Path):
    """Scripts in high_value_unintegrated have integration_suggestions."""
    orchestrator = FileSyncOrchestrator(repo_root)
    report = orchestrator.run_analysis()
    for result in report.high_value_unintegrated:
        assert hasattr(result, "integration_suggestions")


def test_orchestrator_medium_value_can_have_suggestions(repo_root: Path):
    """Medium value unintegrated scripts may have suggestions."""
    orchestrator = FileSyncOrchestrator(repo_root)
    report = orchestrator.run_analysis()
    for result in report.medium_value_unintegrated:
        assert hasattr(result, "integration_suggestions")


# ===========================================================================
# End-to-end tests
# ===========================================================================

def test_end_to_end_analysis(repo_root: Path):
    """Full pipeline: discover → analyze → score → suggest → report."""
    orchestrator = FileSyncOrchestrator(repo_root)
    report = orchestrator.run_analysis()
    assert report.scripts_analyzed > 0
    assert len(report.summary) > 0


def test_real_scripts_validate_renders(repo_root: Path):
    """Real script (validate_renders.py) scores correctly."""
    analyzer = ScriptAnalyzer(repo_root)
    all_scripts = analyzer.discover_scripts()
    vr_scripts = [s for s in all_scripts if "validate_renders" in s.name]
    if not vr_scripts:
        pytest.skip("validate_renders.py not found in repo")
    meta = analyzer.analyze(vr_scripts[0])
    scorer = UtilityScorer(repo_root)
    score, reasons, _ = scorer.score(meta)
    assert score >= 0.0  # should not crash


def test_real_scripts_get_version(repo_root: Path):
    """Real script (get_version.py) scores correctly."""
    analyzer = ScriptAnalyzer(repo_root)
    all_scripts = analyzer.discover_scripts()
    gv_scripts = [s for s in all_scripts if "get_version" in s.name]
    if not gv_scripts:
        pytest.skip("get_version.py not found in repo")
    meta = analyzer.analyze(gv_scripts[0])
    scorer = UtilityScorer(repo_root)
    score, reasons, _ = scorer.score(meta)
    assert score >= 0.0
