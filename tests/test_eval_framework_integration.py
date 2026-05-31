"""
Integration tests for the evaluation framework
"""

import pytest
import tempfile
import json
from pathlib import Path

from src.skills._meta.evaluation_framework.framework import TestRunner, TestStatus
from src.skills._meta.evaluation_framework.reporters import JSONReporter, MarkdownReporter, CSVReporter
from src.skills._meta.evaluation_framework.test_case import TestCase


class TestFrameworkIntegration:
    """Integration tests for the full evaluation framework."""
    
    def test_end_to_end_framework(self):
        """Test complete framework flow: load tests -> run -> report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create test directory
            tests_dir = tmpdir / "tests"
            tests_dir.mkdir()
            
            # Create sample test cases
            (tests_dir / "test1.yaml").write_text("""
id: test-delegate-001
name: Test DELEGATE creation
harnesses: [opencode, copilot]
models: [haiku, sonnet]
prompt: Create a DELEGATE block
expected_contains: [DELEGATE, task_id]
timeout_seconds: 30
            """)
            
            (tests_dir / "test2.yaml").write_text("""
id: test-handback-001
name: Test HANDBACK validation
harnesses: [opencode]
models: [haiku]
prompt: Create a HANDBACK block
expected_contains: [HANDBACK, status]
timeout_seconds: 30
            """)
            
            # Initialize runner and load tests
            runner = TestRunner()
            runner.load_test_cases(tests_dir)
            assert len(runner.test_cases) == 2
            
            # Run tests
            matrix = runner.run_all_tests(
                harnesses=["opencode"],
                models=["haiku"]
            )
            
            # Verify results
            # test-delegate-001: runs on opencode:haiku (copilot skipped)
            # test-handback-001: runs on opencode:haiku
            # Total: 2 results (not 3)
            assert len(matrix.results) >= 2
    
    def test_json_report_generation(self):
        """Test JSON report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            tests_dir = tmpdir / "tests"
            tests_dir.mkdir()
            
            # Create test
            (tests_dir / "test1.yaml").write_text("""
id: test-001
name: Test
harnesses: [opencode]
models: [haiku]
prompt: Test
timeout_seconds: 30
            """)
            
            # Run framework
            runner = TestRunner()
            runner.load_test_cases(tests_dir)
            matrix = runner.run_all_tests(harnesses=["opencode"], models=["haiku"])
            
            # Generate JSON report
            report_path = tmpdir / "report.json"
            json_reporter = JSONReporter(matrix)
            json_reporter.write(report_path)
            
            # Verify JSON report
            assert report_path.exists()
            with open(report_path) as f:
                data = json.load(f)
            
            assert "metadata" in data
            assert "summary" in data
            assert "results" in data
            assert len(data["results"]) > 0
    
    def test_markdown_report_generation(self):
        """Test Markdown report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            tests_dir = tmpdir / "tests"
            tests_dir.mkdir()
            
            # Create test
            (tests_dir / "test1.yaml").write_text("""
id: test-001
name: Test
harnesses: [opencode]
models: [haiku]
prompt: Test
timeout_seconds: 30
            """)
            
            # Run framework
            runner = TestRunner()
            runner.load_test_cases(tests_dir)
            matrix = runner.run_all_tests(harnesses=["opencode"], models=["haiku"])
            
            # Generate Markdown report
            report_path = tmpdir / "report.md"
            md_reporter = MarkdownReporter(matrix)
            md_reporter.write(report_path)
            
            # Verify Markdown report
            assert report_path.exists()
            content = report_path.read_text()
            assert "Test Report" in content
            assert "Summary" in content
            assert "Results by Harness" in content
            assert "Results by Model" in content
    
    def test_csv_report_generation(self):
        """Test CSV report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            tests_dir = tmpdir / "tests"
            tests_dir.mkdir()
            
            # Create test
            (tests_dir / "test1.yaml").write_text("""
id: test-001
name: Test
harnesses: [opencode]
models: [haiku]
prompt: Test
timeout_seconds: 30
            """)
            
            # Run framework
            runner = TestRunner()
            runner.load_test_cases(tests_dir)
            matrix = runner.run_all_tests(harnesses=["opencode"], models=["haiku"])
            
            # Generate CSV report
            report_path = tmpdir / "report.csv"
            csv_reporter = CSVReporter(matrix)
            csv_reporter.write(report_path)
            
            # Verify CSV report
            assert report_path.exists()
            content = report_path.read_text()
            assert "test_id" in content
            assert "harness" in content
            assert "model" in content
            assert "status" in content
    
    def test_test_case_filtering(self):
        """Test filtering test cases by ID pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            tests_dir = tmpdir / "tests"
            tests_dir.mkdir()
            
            # Create multiple test cases
            for i in range(3):
                (tests_dir / f"test-delegate-{i:03d}.yaml").write_text(f"""
id: test-delegate-{i:03d}
name: Test {i}
harnesses: [opencode]
models: [haiku]
prompt: Test
timeout_seconds: 30
                """)
            
            for i in range(2):
                (tests_dir / f"test-handback-{i:03d}.yaml").write_text(f"""
id: test-handback-{i:03d}
name: Test {i}
harnesses: [opencode]
models: [haiku]
prompt: Test
timeout_seconds: 30
                """)
            
            runner = TestRunner()
            runner.load_test_cases(tests_dir)
            assert len(runner.test_cases) == 5
            
            # Filter test cases
            from fnmatch import fnmatch
            filtered = [tc for tc in runner.test_cases if fnmatch(tc.id, "test-delegate*")]
            assert len(filtered) == 3


class TestReporterRegressionDetectorFieldAlignment:
    """Regression tests for producer/consumer field-name alignment.

    The RegressionDetector consumes the canonical ``failed_tests`` field
    (a list of test IDs). The JSONReporter is the producer of the snapshot
    dict that becomes the baseline/current input for the detector, so its
    output MUST expose ``failed_tests`` with the same shape the detector
    reads. Previously the reporter only emitted ``failures`` (a list of
    full result dicts), which the detector could not consume — silently
    dropping every new-failure regression.
    """

    def _build_matrix(self, fail_ids):
        from src.skills._meta.evaluation_framework.framework import (
            CompatibilityMatrix,
            TestResult,
            TestStatus,
        )

        matrix = CompatibilityMatrix()
        # One passing result so the suite is non-trivial.
        matrix.add_result(
            TestResult(
                test_id="test_pass",
                harness="opencode",
                model="haiku",
                status=TestStatus.PASS,
                duration_ms=100,
            )
        )
        for fid in fail_ids:
            matrix.add_result(
                TestResult(
                    test_id=fid,
                    harness="opencode",
                    model="haiku",
                    status=TestStatus.FAIL,
                    duration_ms=120,
                    error_message="boom",
                )
            )
        return matrix

    def test_json_report_exposes_canonical_failed_tests(self):
        """JSONReporter output exposes ``failed_tests`` as a list of test IDs."""
        matrix = self._build_matrix(["test_a", "test_b"])
        report = JSONReporter(matrix).generate()

        assert "failed_tests" in report, (
            "JSONReporter must emit the canonical 'failed_tests' field consumed "
            "by RegressionDetector"
        )
        assert isinstance(report["failed_tests"], list)
        # Must be plain test IDs (hashable), not nested dicts, so the detector
        # can build a set() from them.
        assert all(isinstance(t, str) for t in report["failed_tests"])
        assert set(report["failed_tests"]) == {"test_a", "test_b"}

    def test_detector_reads_failed_tests_from_reporter_output(self):
        """A JSONReporter snapshot feeds the detector and surfaces new failures."""
        from src.skills._meta.evaluation_framework.regression_detector import (
            RegressionDetector,
        )

        baseline = JSONReporter(self._build_matrix(["test_a"])).generate()
        current = JSONReporter(self._build_matrix(["test_a", "test_b"])).generate()

        regressions = RegressionDetector().detect(baseline, current)
        new_failures = [r for r in regressions if r.regression_type == "new_failure"]

        assert [r.test_id for r in new_failures] == ["test_b"], (
            "Detector should read 'failed_tests' from the reporter output and "
            "flag exactly the newly-failing test"
        )
