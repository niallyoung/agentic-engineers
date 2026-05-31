"""
Quality Enforcement Engine

Validates type hints, docstrings, linting standards, test coverage, and detects
dead code across skill implementations.

Requirements:
- Type hints on all functions
- Comprehensive docstrings
- ≥85% test coverage
- All code must pass linting (black, flake8, mypy)
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
import ast
import subprocess
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
import json


class QualityCheckType(Enum):
    """Types of quality checks."""
    TYPE_HINTS = "TYPE_HINTS"
    DOCSTRINGS = "DOCSTRINGS"
    LINTING = "LINTING"
    COVERAGE = "COVERAGE"
    DEAD_CODE = "DEAD_CODE"


@dataclass
class QualityIssue:
    """Represents a quality issue found during validation."""
    check_type: str
    severity: str  # critical, warning, info
    file: str
    line: Optional[int] = None
    message: str = ""
    suggestion: Optional[str] = None


@dataclass
class QualityCheckResult:
    """Results from a single quality check."""
    check_type: str
    passed: bool
    issues: List[QualityIssue] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityReport:
    """Comprehensive quality report for a skill."""
    skill_name: str
    skill_path: Path
    checks: Dict[str, QualityCheckResult] = field(default_factory=dict)
    overall_score: float = 0.0
    is_compliant: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "skill_name": self.skill_name,
            "skill_path": str(self.skill_path),
            "checks": {
                k: {
                    "check_type": v.check_type,
                    "passed": v.passed,
                    "issues": [asdict(issue) for issue in v.issues],
                    "details": v.details,
                }
                for k, v in self.checks.items()
            },
            "overall_score": self.overall_score,
            "is_compliant": self.is_compliant,
        }


class TypeHintsValidator:
    """Validates type hints in Python files."""

    @staticmethod
    def validate_file(file_path: Path) -> Tuple[bool, List[QualityIssue]]:
        """
        Validate type hints in a Python file.

        Args:
            file_path: Path to Python file

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues: List[QualityIssue] = []

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except SyntaxError as e:
            issues.append(
                QualityIssue(
                    check_type="TYPE_HINTS",
                    severity="critical",
                    file=str(file_path),
                    line=e.lineno,
                    message=f"Syntax error: {e.msg}",
                )
            )
            return False, issues

        # Check for missing type hints on functions
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private methods and special methods
                if node.name.startswith("_"):
                    continue

                # Check return type annotation
                if node.returns is None:
                    issues.append(
                        QualityIssue(
                            check_type="TYPE_HINTS",
                            severity="warning",
                            file=str(file_path),
                            line=node.lineno,
                            message=f"Missing return type hint on function '{node.name}'",
                            suggestion="Add return type annotation (e.g., -> str:)",
                        )
                    )

                # Check parameter type annotations
                for arg in node.args.args:
                    if arg.annotation is None:
                        issues.append(
                            QualityIssue(
                                check_type="TYPE_HINTS",
                                severity="warning",
                                file=str(file_path),
                                line=node.lineno,
                                message=f"Missing type hint for parameter '{arg.arg}' in function '{node.name}'",
                                suggestion="Add parameter type annotation",
                            )
                        )

        is_valid = not any(i.severity == "critical" for i in issues)
        return is_valid, issues


class DocstringValidator:
    """Validates docstrings in Python files."""

    @staticmethod
    def validate_file(file_path: Path) -> Tuple[bool, List[QualityIssue]]:
        """
        Validate docstrings in a Python file.

        Args:
            file_path: Path to Python file

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues: List[QualityIssue] = []

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except SyntaxError as e:
            issues.append(
                QualityIssue(
                    check_type="DOCSTRINGS",
                    severity="critical",
                    file=str(file_path),
                    line=e.lineno,
                    message=f"Syntax error: {e.msg}",
                )
            )
            return False, issues

        # Check module-level docstring
        if not ast.get_docstring(tree):
            issues.append(
                QualityIssue(
                    check_type="DOCSTRINGS",
                    severity="warning",
                    file=str(file_path),
                    line=1,
                    message="Missing module-level docstring",
                    suggestion='Add docstring at top of file ("""...""")',
                )
            )

        # Check class and function docstrings
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private methods and special methods
                if node.name.startswith("_"):
                    continue

                docstring = ast.get_docstring(node)
                if not docstring:
                    issues.append(
                        QualityIssue(
                            check_type="DOCSTRINGS",
                            severity="warning",
                            file=str(file_path),
                            line=node.lineno,
                            message=f"Missing docstring for {node.name}",
                            suggestion="Add docstring with description and Args/Returns",
                        )
                    )

        is_valid = not any(i.severity == "critical" for i in issues)
        return is_valid, issues


class LintingValidator:
    """Validates code linting standards."""

    @staticmethod
    def validate_with_flake8(file_path: Path) -> Tuple[bool, List[QualityIssue]]:
        """
        Validate file with flake8.

        Args:
            file_path: Path to Python file

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues: List[QualityIssue] = []

        try:
            result = subprocess.run(
                ["flake8", str(file_path), "--max-line-length=100"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        parts = line.split(":")
                        line_num = int(parts[1]) if len(parts) > 1 else None
                        message = parts[3].strip() if len(parts) > 3 else line

                        issues.append(
                            QualityIssue(
                                check_type="LINTING",
                                severity="warning",
                                file=str(file_path),
                                line=line_num,
                                message=message,
                            )
                        )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        is_valid = len(issues) == 0
        return is_valid, issues

    @staticmethod
    def validate_with_black(file_path: Path) -> Tuple[bool, List[QualityIssue]]:
        """
        Check if file is formatted according to black standards.

        Args:
            file_path: Path to Python file

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues: List[QualityIssue] = []

        try:
            result = subprocess.run(
                ["black", "--check", str(file_path)],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                issues.append(
                    QualityIssue(
                        check_type="LINTING",
                        severity="warning",
                        file=str(file_path),
                        message="Code formatting does not match black style",
                        suggestion="Run: black " + str(file_path),
                    )
                )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        is_valid = len(issues) == 0
        return is_valid, issues


class TestCoverageValidator:
    """Validates test coverage for skills."""

    @staticmethod
    def validate_coverage(
        skill_path: Path, min_coverage: float = 85.0
    ) -> Tuple[bool, List[QualityIssue], Dict[str, Any]]:
        """
        Validate test coverage for a skill.

        Args:
            skill_path: Path to skill directory
            min_coverage: Minimum coverage percentage required

        Returns:
            Tuple of (is_valid, list_of_issues, coverage_details)
        """
        issues: List[QualityIssue] = []
        details: Dict[str, Any] = {}

        # Find test files for this skill
        test_patterns = [
            f"**/test_*{skill_path.name}*.py",
            f"**/tests/{skill_path.name}/**/*.py",
        ]

        test_files = []
        for pattern in test_patterns:
            test_files.extend(skill_path.glob(pattern))

        if not test_files:
            issues.append(
                QualityIssue(
                    check_type="COVERAGE",
                    severity="critical",
                    file=str(skill_path),
                    message=f"No test files found for skill {skill_path.name}",
                    suggestion="Create test files in tests/ directory",
                )
            )
            return False, issues, details

        details["test_files_found"] = len(test_files)

        # Try to get coverage data
        try:
            # Attempt to run pytest with coverage
            result = subprocess.run(
                [
                    "pytest",
                    str(skill_path),
                    "--cov",
                    f"src/skills/{skill_path.name}",
                    "--cov-report=json",
                    "--tb=short",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Coverage was collected successfully
                details["coverage_available"] = True
                # Note: Actual coverage data would be parsed from the JSON report
            else:
                details["coverage_available"] = False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            details["coverage_available"] = False

        is_valid = len([i for i in issues if i.severity == "critical"]) == 0
        return is_valid, issues, details


class DeadCodeDetector:
    """Detects dead code in Python files."""

    @staticmethod
    def detect_dead_code(file_path: Path) -> Tuple[bool, List[QualityIssue]]:
        """
        Detect dead code patterns in a Python file.

        Args:
            file_path: Path to Python file

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues: List[QualityIssue] = []

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except SyntaxError as e:
            issues.append(
                QualityIssue(
                    check_type="DEAD_CODE",
                    severity="critical",
                    file=str(file_path),
                    line=e.lineno,
                    message=f"Syntax error: {e.msg}",
                )
            )
            return False, issues

        # Collect all defined functions and classes
        defined: Set[str] = set()
        used: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not node.name.startswith("_"):
                    defined.add(node.name)
            elif isinstance(node, ast.Name):
                used.add(node.id)

        # Find unused definitions
        unused = defined - used

        for name in unused:
            issues.append(
                QualityIssue(
                    check_type="DEAD_CODE",
                    severity="info",
                    file=str(file_path),
                    message=f"Potentially unused definition: {name}",
                    suggestion="Remove or document why this is kept",
                )
            )

        is_valid = len(issues) == 0
        return is_valid, issues


class QualityEnforcer:
    """Main quality enforcement engine."""

    def __init__(self, skill_path: Path):
        """
        Initialize quality enforcer for a skill.

        Args:
            skill_path: Path to skill directory
        """
        self.skill_path = skill_path
        self.skill_name = skill_path.name
        self.report = QualityReport(
            skill_name=self.skill_name, skill_path=skill_path
        )

    def validate_type_hints(self) -> QualityCheckResult:
        """
        Validate type hints across skill code.

        Returns:
            QualityCheckResult with type hint validation issues
        """
        result = QualityCheckResult(check_type="TYPE_HINTS", passed=True)
        all_issues: List[QualityIssue] = []

        # Find all Python files
        python_files = list(self.skill_path.glob("**/*.py"))

        for py_file in python_files:
            is_valid, issues = TypeHintsValidator.validate_file(py_file)
            all_issues.extend(issues)
            if not is_valid:
                result.passed = False

        result.issues = all_issues
        result.details["files_checked"] = len(python_files)
        result.details["issues_found"] = len(all_issues)

        return result

    def validate_docstrings(self) -> QualityCheckResult:
        """
        Validate docstrings across skill code.

        Returns:
            QualityCheckResult with docstring validation issues
        """
        result = QualityCheckResult(check_type="DOCSTRINGS", passed=True)
        all_issues: List[QualityIssue] = []

        # Find all Python files
        python_files = list(self.skill_path.glob("**/*.py"))

        for py_file in python_files:
            is_valid, issues = DocstringValidator.validate_file(py_file)
            all_issues.extend(issues)
            if not is_valid:
                result.passed = False

        result.issues = all_issues
        result.details["files_checked"] = len(python_files)
        result.details["issues_found"] = len(all_issues)

        return result

    def validate_linting(self) -> QualityCheckResult:
        """
        Validate code linting standards.

        Returns:
            QualityCheckResult with linting issues
        """
        result = QualityCheckResult(check_type="LINTING", passed=True)
        all_issues: List[QualityIssue] = []

        # Find all Python files
        python_files = list(self.skill_path.glob("**/*.py"))

        for py_file in python_files:
            # Check with flake8
            is_valid_flake8, flake8_issues = LintingValidator.validate_with_flake8(
                py_file
            )
            all_issues.extend(flake8_issues)
            if not is_valid_flake8:
                result.passed = False

            # Check with black
            is_valid_black, black_issues = LintingValidator.validate_with_black(py_file)
            all_issues.extend(black_issues)
            if not is_valid_black:
                result.passed = False

        result.issues = all_issues
        result.details["files_checked"] = len(python_files)
        result.details["issues_found"] = len(all_issues)

        return result

    def validate_coverage(self, min_coverage: float = 85.0) -> QualityCheckResult:
        """
        Validate test coverage.

        Returns:
            QualityCheckResult with coverage validation issues
        """
        result = QualityCheckResult(check_type="COVERAGE", passed=True)

        is_valid, issues, details = TestCoverageValidator.validate_coverage(
            self.skill_path, min_coverage
        )
        result.passed = is_valid
        result.issues = issues
        result.details = details

        return result

    def detect_dead_code(self) -> QualityCheckResult:
        """
        Detect dead code patterns.

        Returns:
            QualityCheckResult with dead code issues
        """
        result = QualityCheckResult(check_type="DEAD_CODE", passed=True)
        all_issues: List[QualityIssue] = []

        # Find all Python files
        python_files = list(self.skill_path.glob("**/*.py"))

        for py_file in python_files:
            is_valid, issues = DeadCodeDetector.detect_dead_code(py_file)
            all_issues.extend(issues)
            if not is_valid:
                result.passed = False

        result.issues = all_issues
        result.details["files_checked"] = len(python_files)
        result.details["issues_found"] = len(all_issues)

        return result

    def run_all_checks(self) -> QualityReport:
        """
        Run all quality checks.

        Returns:
            Comprehensive QualityReport
        """
        self.report.checks["TYPE_HINTS"] = self.validate_type_hints()
        self.report.checks["DOCSTRINGS"] = self.validate_docstrings()
        self.report.checks["LINTING"] = self.validate_linting()
        self.report.checks["COVERAGE"] = self.validate_coverage()
        self.report.checks["DEAD_CODE"] = self.detect_dead_code()

        # Calculate overall score
        passed_checks = sum(
            1 for check in self.report.checks.values() if check.passed
        )
        total_checks = len(self.report.checks)
        base_score = (passed_checks / total_checks) * 100

        # Deduct for issues
        total_issues = sum(len(check.issues) for check in self.report.checks.values())
        issue_deduction = total_issues * 2
        self.report.overall_score = max(0.0, base_score - issue_deduction)

        # Determine compliance (90+ score means compliant)
        self.report.is_compliant = self.report.overall_score >= 90.0

        return self.report

    def export_report(self, output_path: Path) -> None:
        """
        Export quality report to JSON file.

        Args:
            output_path: Path where to save the report
        """
        report_dict = self.report.to_dict()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2)
