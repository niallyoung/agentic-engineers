"""
TestRunner: Core test execution engine for the evaluation framework

Executes test cases against harnesses, captures results, and builds compatibility matrix.
"""

import json
import time
import subprocess
import signal
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
from enum import Enum

from .test_case import TestCase, TestCaseValidationError


class TestStatus(Enum):
    """Test execution status."""
    PASS = "pass"
    FAIL = "fail"
    TIMEOUT = "timeout"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class TestResult:
    """Result of a single test execution."""
    test_id: str
    harness: str
    model: str
    status: TestStatus
    duration_ms: int
    tokens_used: int = 0
    output: str = ""
    error_message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "test_id": self.test_id,
            "harness": self.harness,
            "model": self.model,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "timestamp": self.timestamp,
            "error_message": self.error_message if self.error_message else None,
        }


@dataclass
class CompatibilityMatrix:
    """Matrix of test results across harnesses and models."""
    results: List[TestResult] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def add_result(self, result: TestResult):
        """Add a test result to the matrix."""
        self.results.append(result)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Generate summary statistics from results.
        
        Returns:
            Dictionary with:
                - total_tests: Total number of test results
                - passed: Number of passing tests
                - failed: Number of failing tests
                - timeout: Number of timeout tests
                - error: Number of error tests
                - skipped: Number of skipped tests
                - pass_rate: Percentage of passed tests
                - avg_duration_ms: Average test duration
                - by_harness: Summary by harness
                - by_model: Summary by model
                - by_severity: Summary by severity
        """
        if not self.results:
            return {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "timeout": 0,
                "error": 0,
                "skipped": 0,
                "pass_rate": 0.0,
                "avg_duration_ms": 0,
            }
        
        stats = {
            "pass": 0,
            "fail": 0,
            "timeout": 0,
            "error": 0,
            "skipped": 0,
        }
        
        total_duration = 0
        by_harness = {}
        by_model = {}
        
        for result in self.results:
            status_key = result.status.value
            # Convert "pass" to "passed", "fail" to "failed" for dictionary keys
            dict_key = "passed" if status_key == "pass" else ("failed" if status_key == "fail" else status_key)
            
            stats[status_key] += 1
            total_duration += result.duration_ms
            
            # Group by harness
            if result.harness not in by_harness:
                by_harness[result.harness] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "timeout": 0,
                    "error": 0,
                    "skipped": 0,
                }
            by_harness[result.harness]["total"] += 1
            by_harness[result.harness][dict_key] += 1
            
            # Group by model
            if result.model not in by_model:
                by_model[result.model] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "timeout": 0,
                    "error": 0,
                    "skipped": 0,
                }
            by_model[result.model]["total"] += 1
            by_model[result.model][dict_key] += 1
        
        total = len(self.results)
        passed = stats["pass"]
        pass_rate = (passed / total * 100) if total > 0 else 0
        avg_duration = total_duration / total if total > 0 else 0
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": stats["fail"],
            "timeout": stats["timeout"],
            "error": stats["error"],
            "skipped": stats["skipped"],
            "pass_rate": round(pass_rate, 2),
            "avg_duration_ms": round(avg_duration, 2),
            "by_harness": {k: {**v, "pass_rate": round(v["passed"] / v["total"] * 100, 2) if v["total"] > 0 else 0} for k, v in by_harness.items()},
            "by_model": {k: {**v, "pass_rate": round(v["passed"] / v["total"] * 100, 2) if v["total"] > 0 else 0} for k, v in by_model.items()},
        }
    
    def get_failures(self) -> List[TestResult]:
        """Get all failing tests."""
        return [r for r in self.results if r.status in (TestStatus.FAIL, TestStatus.ERROR, TestStatus.TIMEOUT)]
    
    def get_regressions(self) -> Dict[str, List[str]]:
        """
        Get regressions grouped by harness/model.
        
        Returns:
            Dictionary with keys like "harness:model" and list of failed test IDs
        """
        regressions = {}
        for result in self.get_failures():
            key = f"{result.harness}:{result.model}"
            if key not in regressions:
                regressions[key] = []
            regressions[key].append(result.test_id)
        return regressions


class TestRunner:
    """
    Executes test cases against harnesses and captures results.
    
    Features:
    - Load test cases from YAML files or directories
    - Run tests with timeout enforcement
    - Capture output, tokens, latency
    - Build compatibility matrix
    - Generate JSON and Markdown reports
    """
    
    def __init__(self, working_dir: Path = None):
        """
        Initialize TestRunner.
        
        Args:
            working_dir: Working directory for test execution (default: current directory)
        """
        self.working_dir = Path(working_dir or ".")
        self.test_cases: List[TestCase] = []
        self.matrix = CompatibilityMatrix()
        self.harnesses = {"opencode", "copilot", "claude-code", "pi-dev"}
        self.models = {"haiku", "sonnet", "opus"}
    
    def load_test_cases(self, tests_dir: Path):
        """
        Load test cases from a directory containing YAML files.
        
        Args:
            tests_dir: Directory containing test case YAML files
            
        Raises:
            FileNotFoundError: If directory doesn't exist
            TestCaseValidationError: If any test case is invalid
        """
        tests_dir = Path(tests_dir)
        if not tests_dir.exists():
            raise FileNotFoundError(f"Tests directory not found: {tests_dir}")
        
        yaml_files = list(tests_dir.glob("*.yaml")) + list(tests_dir.glob("*.yml"))
        
        for yaml_file in sorted(yaml_files):
            try:
                test_case = TestCase.from_yaml(yaml_file)
                self.test_cases.append(test_case)
            except TestCaseValidationError as e:
                raise TestCaseValidationError(f"Error loading {yaml_file}: {e}")
    
    def add_test_case(self, test_case: TestCase):
        """
        Add a single test case.
        
        Args:
            test_case: TestCase instance
        """
        test_case.validate()  # Validate before adding
        self.test_cases.append(test_case)
    
    def run_all_tests(self, harnesses: List[str] = None, models: List[str] = None) -> CompatibilityMatrix:
        """
        Run all loaded test cases against specified harnesses and models.
        
        Args:
            harnesses: List of harnesses to test (default: all)
            models: List of models to test (default: all)
            
        Returns:
            CompatibilityMatrix with all results
        """
        harnesses = harnesses or list(self.harnesses)
        models = models or list(self.models)
        
        test_count = len(self.test_cases) * len(harnesses) * len(models)
        print(f"Running {test_count} test combinations ({len(self.test_cases)} tests × {len(harnesses)} harnesses × {len(models)} models)")
        
        for i, test_case in enumerate(self.test_cases):
            for harness in harnesses:
                if harness not in test_case.harnesses:
                    # Skip if harness not in test case's harness list
                    for model in models:
                        result = TestResult(
                            test_id=test_case.id,
                            harness=harness,
                            model=model,
                            status=TestStatus.SKIPPED,
                            duration_ms=0,
                        )
                        self.matrix.add_result(result)
                    continue
                
                for model in models:
                    if model not in test_case.models:
                        # Skip if model not in test case's model list
                        result = TestResult(
                            test_id=test_case.id,
                            harness=harness,
                            model=model,
                            status=TestStatus.SKIPPED,
                            duration_ms=0,
                        )
                        self.matrix.add_result(result)
                        continue
                    
                    print(f"[{i+1}/{len(self.test_cases)}] Running {test_case.id} @ {harness}:{model}...", end=" ", flush=True)
                    result = self._run_single_test(test_case, harness, model)
                    self.matrix.add_result(result)
                    print(f"{result.status.value.upper()} ({result.duration_ms}ms)")
        
        return self.matrix
    
    def _run_single_test(self, test_case: TestCase, harness: str, model: str) -> TestResult:
        """
        Execute a single test case against a harness/model.
        
        Args:
            test_case: Test case to run
            harness: Harness to test against
            model: Model to test against
            
        Returns:
            TestResult with execution details
        """
        start_time = time.time()
        
        try:
            # Build test payload
            if test_case.prompt:
                test_input = test_case.prompt
            else:
                test_input = test_case.delegation
            
            # For now, simulate test execution
            # In real implementation, this would invoke the actual harness
            output, error, tokens = self._invoke_harness(harness, model, test_input)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Check timeout
            if duration_ms > test_case.timeout_seconds * 1000:
                return TestResult(
                    test_id=test_case.id,
                    harness=harness,
                    model=model,
                    status=TestStatus.TIMEOUT,
                    duration_ms=duration_ms,
                    error_message=f"Test exceeded timeout of {test_case.timeout_seconds}s",
                    tokens_used=tokens,
                )
            
            # If there was an error, mark as error
            if error:
                return TestResult(
                    test_id=test_case.id,
                    harness=harness,
                    model=model,
                    status=TestStatus.ERROR,
                    duration_ms=duration_ms,
                    output=output,
                    error_message=error,
                    tokens_used=tokens,
                )
            
            # Check expected_contains
            for expected in test_case.expected_contains:
                if expected not in output:
                    return TestResult(
                        test_id=test_case.id,
                        harness=harness,
                        model=model,
                        status=TestStatus.FAIL,
                        duration_ms=duration_ms,
                        output=output,
                        error_message=f"Output missing expected string: '{expected}'",
                        tokens_used=tokens,
                    )
            
            # Check expected_not_contains
            for not_expected in test_case.expected_not_contains:
                if not_expected in output:
                    return TestResult(
                        test_id=test_case.id,
                        harness=harness,
                        model=model,
                        status=TestStatus.FAIL,
                        duration_ms=duration_ms,
                        output=output,
                        error_message=f"Output contains unexpected string: '{not_expected}'",
                        tokens_used=tokens,
                    )
            
            # All checks passed
            return TestResult(
                test_id=test_case.id,
                harness=harness,
                model=model,
                status=TestStatus.PASS,
                duration_ms=duration_ms,
                output=output,
                tokens_used=tokens,
            )
        
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return TestResult(
                test_id=test_case.id,
                harness=harness,
                model=model,
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                error_message=str(e),
            )
    
    def _invoke_harness(self, harness: str, model: str, test_input: str) -> Tuple[str, str, int]:
        """
        Invoke a harness to run a test.
        
        Args:
            harness: Harness name
            model: Model name
            test_input: Test prompt or delegation
            
        Returns:
            Tuple of (output, error_message, tokens_used)
        """
        # This is a placeholder implementation
        # In real implementation, this would invoke the actual harness
        # For now, return mock data
        return ("Test output", "", 0)
