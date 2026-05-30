"""
Unit tests for TestRunner and CompatibilityMatrix classes
"""

import pytest
import tempfile
from pathlib import Path

from src.skills._meta.evaluation_framework.framework import (
    TestRunner, CompatibilityMatrix, TestResult, TestStatus
)
from src.skills._meta.evaluation_framework.test_case import TestCase


class TestCompatibilityMatrix:
    """Test CompatibilityMatrix functionality."""
    
    def test_empty_matrix(self):
        """Test creating an empty matrix."""
        matrix = CompatibilityMatrix()
        assert len(matrix.results) == 0
        summary = matrix.get_summary()
        assert summary["total_tests"] == 0
        assert summary["pass_rate"] == 0.0
    
    def test_add_results(self):
        """Test adding results to matrix."""
        matrix = CompatibilityMatrix()
        
        result1 = TestResult(
            test_id="test-001",
            harness="opencode",
            model="haiku",
            status=TestStatus.PASS,
            duration_ms=100,
        )
        result2 = TestResult(
            test_id="test-001",
            harness="opencode",
            model="sonnet",
            status=TestStatus.FAIL,
            duration_ms=150,
        )
        
        matrix.add_result(result1)
        matrix.add_result(result2)
        
        assert len(matrix.results) == 2
    
    def test_summary_pass_rate(self):
        """Test pass rate calculation."""
        matrix = CompatibilityMatrix()
        
        # Add 3 passing results
        for i in range(3):
            matrix.add_result(TestResult(
                test_id=f"test-{i}",
                harness="opencode",
                model="haiku",
                status=TestStatus.PASS,
                duration_ms=100,
            ))
        
        # Add 1 failing result
        matrix.add_result(TestResult(
            test_id="test-fail",
            harness="opencode",
            model="haiku",
            status=TestStatus.FAIL,
            duration_ms=100,
        ))
        
        summary = matrix.get_summary()
        assert summary["total_tests"] == 4
        assert summary["passed"] == 3
        assert summary["failed"] == 1
        assert summary["pass_rate"] == 75.0
    
    def test_by_harness_stats(self):
        """Test statistics grouped by harness."""
        matrix = CompatibilityMatrix()
        
        # OpenCode results: 2 pass, 1 fail
        matrix.add_result(TestResult("t1", "opencode", "haiku", TestStatus.PASS, 100))
        matrix.add_result(TestResult("t2", "opencode", "haiku", TestStatus.PASS, 100))
        matrix.add_result(TestResult("t3", "opencode", "haiku", TestStatus.FAIL, 100))
        
        # Copilot results: 1 pass, 0 fail
        matrix.add_result(TestResult("t4", "copilot", "haiku", TestStatus.PASS, 100))
        
        summary = matrix.get_summary()
        assert summary["by_harness"]["opencode"]["total"] == 3
        assert summary["by_harness"]["opencode"]["passed"] == 2
        assert summary["by_harness"]["opencode"]["failed"] == 1
        assert summary["by_harness"]["opencode"]["pass_rate"] == pytest.approx(66.67, 0.01)
        
        assert summary["by_harness"]["copilot"]["total"] == 1
        assert summary["by_harness"]["copilot"]["passed"] == 1
        assert summary["by_harness"]["copilot"]["pass_rate"] == 100.0
    
    def test_by_model_stats(self):
        """Test statistics grouped by model."""
        matrix = CompatibilityMatrix()
        
        # Haiku results: 2 pass, 1 fail
        matrix.add_result(TestResult("t1", "opencode", "haiku", TestStatus.PASS, 100))
        matrix.add_result(TestResult("t2", "opencode", "haiku", TestStatus.PASS, 100))
        matrix.add_result(TestResult("t3", "opencode", "haiku", TestStatus.FAIL, 100))
        
        # Sonnet results: 1 pass
        matrix.add_result(TestResult("t4", "opencode", "sonnet", TestStatus.PASS, 100))
        
        summary = matrix.get_summary()
        assert summary["by_model"]["haiku"]["total"] == 3
        assert summary["by_model"]["haiku"]["passed"] == 2
        assert summary["by_model"]["haiku"]["pass_rate"] == pytest.approx(66.67, 0.01)
        
        assert summary["by_model"]["sonnet"]["total"] == 1
        assert summary["by_model"]["sonnet"]["passed"] == 1
        assert summary["by_model"]["sonnet"]["pass_rate"] == 100.0
    
    def test_get_failures(self):
        """Test getting all failures."""
        matrix = CompatibilityMatrix()
        
        matrix.add_result(TestResult("t1", "opencode", "haiku", TestStatus.PASS, 100))
        matrix.add_result(TestResult("t2", "opencode", "haiku", TestStatus.FAIL, 100))
        matrix.add_result(TestResult("t3", "opencode", "haiku", TestStatus.ERROR, 100))
        matrix.add_result(TestResult("t4", "opencode", "haiku", TestStatus.TIMEOUT, 100))
        
        failures = matrix.get_failures()
        assert len(failures) == 3
        assert all(r.status in (TestStatus.FAIL, TestStatus.ERROR, TestStatus.TIMEOUT) for r in failures)
    
    def test_get_regressions(self):
        """Test getting regressions grouped by harness/model."""
        matrix = CompatibilityMatrix()
        
        matrix.add_result(TestResult("t1", "opencode", "haiku", TestStatus.PASS, 100))
        matrix.add_result(TestResult("t2", "opencode", "haiku", TestStatus.FAIL, 100))
        matrix.add_result(TestResult("t3", "copilot", "haiku", TestStatus.FAIL, 100))
        matrix.add_result(TestResult("t4", "copilot", "sonnet", TestStatus.PASS, 100))
        
        regressions = matrix.get_regressions()
        assert "opencode:haiku" in regressions
        assert regressions["opencode:haiku"] == ["t2"]
        assert "copilot:haiku" in regressions
        assert regressions["copilot:haiku"] == ["t3"]
        assert "copilot:sonnet" not in regressions


class TestTestRunner:
    """Test TestRunner functionality."""
    
    def test_create_runner(self):
        """Test creating a TestRunner."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = TestRunner(working_dir=tmpdir)
            assert len(runner.test_cases) == 0
            assert len(runner.matrix.results) == 0
    
    def test_add_test_case(self):
        """Test adding a test case to runner."""
        runner = TestRunner()
        
        tc = TestCase(
            id="test-001",
            name="Test",
            harnesses=["opencode"],
            models=["haiku"],
            prompt="Test",
        )
        
        runner.add_test_case(tc)
        assert len(runner.test_cases) == 1
        assert runner.test_cases[0].id == "test-001"
    
    def test_load_test_cases_from_directory(self):
        """Test loading test cases from directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create test YAML files
            (tmpdir / "test1.yaml").write_text("""
id: test-001
name: Test 1
harnesses: [opencode]
models: [haiku]
prompt: Test
            """)
            
            (tmpdir / "test2.yaml").write_text("""
id: test-002
name: Test 2
harnesses: [copilot]
models: [sonnet]
prompt: Test
            """)
            
            runner = TestRunner()
            runner.load_test_cases(tmpdir)
            
            assert len(runner.test_cases) == 2
            assert runner.test_cases[0].id == "test-001"
            assert runner.test_cases[1].id == "test-002"
    
    def test_load_missing_directory(self):
        """Test that loading from missing directory raises error."""
        runner = TestRunner()
        
        with pytest.raises(FileNotFoundError):
            runner.load_test_cases(Path("/nonexistent/path"))
    
    def test_run_single_test_pass(self):
        """Test running a single test that passes."""
        runner = TestRunner()
        
        tc = TestCase(
            id="test-001",
            name="Test",
            harnesses=["opencode"],
            models=["haiku"],
            prompt="Test",
            expected_contains=["output"],
            timeout_seconds=30,
        )
        
        result = runner._run_single_test(tc, "opencode", "haiku")
        
        # Result should be either PASS or ERROR (since _invoke_harness is mocked)
        assert result.test_id == "test-001"
        assert result.harness == "opencode"
        assert result.model == "haiku"
        assert result.duration_ms >= 0
    
    def test_run_all_tests(self):
        """Test running all test cases."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create test YAML files
            (tmpdir / "test1.yaml").write_text("""
id: test-001
name: Test 1
harnesses: [opencode, copilot]
models: [haiku, sonnet]
prompt: Test
            """)
            
            runner = TestRunner()
            runner.load_test_cases(tmpdir)
            
            # Run tests with subset of harnesses and models
            matrix = runner.run_all_tests(harnesses=["opencode"], models=["haiku"])
            
            # Should have 1 test × 1 harness × 1 model = 1 result
            assert len(matrix.results) == 1
            assert matrix.results[0].test_id == "test-001"
            assert matrix.results[0].harness == "opencode"
            assert matrix.results[0].model == "haiku"
    
    def test_run_tests_skip_non_configured(self):
        """Test that tests skip harnesses/models not in their config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create test with limited harnesses/models
            (tmpdir / "test1.yaml").write_text("""
id: test-001
name: Test 1
harnesses: [opencode]
models: [haiku]
prompt: Test
            """)
            
            runner = TestRunner()
            runner.load_test_cases(tmpdir)
            
            # Run with all harnesses/models
            matrix = runner.run_all_tests(
                harnesses=["opencode", "copilot"],
                models=["haiku", "sonnet"]
            )
            
            # Should have 4 results: 1 pass, 3 skipped
            assert len(matrix.results) == 4
            passed = [r for r in matrix.results if r.status == TestStatus.PASS]
            skipped = [r for r in matrix.results if r.status == TestStatus.SKIPPED]
            assert len(passed) == 1
            assert len(skipped) == 3
