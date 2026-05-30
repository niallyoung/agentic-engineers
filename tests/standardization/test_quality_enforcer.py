"""
Unit tests for the quality enforcement engine.

Tests:
- Type hints validation
- Docstring presence and quality
- Linting standards enforcement
- Dead code detection
- Overall quality scoring
"""

import pytest
from pathlib import Path
import tempfile
from src.standardization.quality_enforcer import (
    TypeHintsValidator,
    DocstringValidator,
    DeadCodeDetector,
    QualityEnforcer,
    QualityCheckResult,
)


@pytest.fixture
def temp_skill_dir():
    """Create a temporary skill directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def well_typed_python_file(temp_skill_dir):
    """Create a well-typed Python file."""
    content = '''"""Module with proper type hints and docstrings."""

def add_numbers(a: int, b: int) -> int:
    """Add two numbers together.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        Sum of the two numbers
    """
    return a + b


class Calculator:
    """A simple calculator class."""
    
    def multiply(self, x: float, y: float) -> float:
        """Multiply two numbers.
        
        Args:
            x: First number
            y: Second number
            
        Returns:
            Product of the two numbers
        """
        return x * y
'''
    py_file = temp_skill_dir / "well_typed.py"
    py_file.write_text(content)
    return py_file


@pytest.fixture
def poorly_typed_python_file(temp_skill_dir):
    """Create a Python file with missing type hints."""
    content = '''"""Module with missing type hints."""

def add_numbers(a, b):
    """Add two numbers."""
    return a + b


def multiply(x, y):
    return x * y
'''
    py_file = temp_skill_dir / "poorly_typed.py"
    py_file.write_text(content)
    return py_file


@pytest.fixture
def missing_docstrings_file(temp_skill_dir):
    """Create a file with missing docstrings."""
    content = '''def function_without_docstring(x: int) -> int:
    return x * 2

class ClassWithoutDocstring:
    def method_without_docstring(self, value: str) -> str:
        return value.upper()
'''
    py_file = temp_skill_dir / "missing_docs.py"
    py_file.write_text(content)
    return py_file


class TestTypeHintsValidation:
    """Tests for type hints validation."""

    def test_well_typed_file(self, well_typed_python_file):
        """Test validation of well-typed file."""
        is_valid, issues = TypeHintsValidator.validate_file(well_typed_python_file)

        # Should have minimal issues
        assert is_valid or len(issues) == 0

    def test_poorly_typed_file(self, poorly_typed_python_file):
        """Test validation of file with missing type hints."""
        is_valid, issues = TypeHintsValidator.validate_file(poorly_typed_python_file)

        # Should report missing type hints
        type_hint_issues = [i for i in issues if "type hint" in i.message.lower()]
        assert len(type_hint_issues) > 0

    def test_syntax_error_handling(self, temp_skill_dir):
        """Test handling of syntax errors."""
        py_file = temp_skill_dir / "syntax_error.py"
        py_file.write_text("def broken(:\n    pass")

        is_valid, issues = TypeHintsValidator.validate_file(py_file)

        assert not is_valid
        assert any(i.severity == "critical" for i in issues)


class TestDocstringValidation:
    """Tests for docstring validation."""

    def test_well_documented_file(self, well_typed_python_file):
        """Test validation of well-documented file."""
        is_valid, issues = DocstringValidator.validate_file(well_typed_python_file)

        # Should have minimal docstring issues
        critical_issues = [i for i in issues if i.severity == "critical"]
        assert len(critical_issues) == 0

    def test_missing_docstrings(self, missing_docstrings_file):
        """Test detection of missing docstrings."""
        is_valid, issues = DocstringValidator.validate_file(missing_docstrings_file)

        # Should report missing docstrings
        docstring_issues = [i for i in issues if "docstring" in i.message.lower()]
        assert len(docstring_issues) > 0

    def test_module_docstring_missing(self, temp_skill_dir):
        """Test detection of missing module docstring."""
        py_file = temp_skill_dir / "no_module_doc.py"
        py_file.write_text('def function() -> None:\n    """A function."""\n    pass')

        is_valid, issues = DocstringValidator.validate_file(py_file)

        # Should report missing module docstring
        module_issues = [i for i in issues if "module" in i.message.lower()]
        assert len(module_issues) > 0


class TestDeadCodeDetection:
    """Tests for dead code detection."""

    def test_unused_function_detection(self, temp_skill_dir):
        """Test detection of unused functions."""
        py_file = temp_skill_dir / "dead_code.py"
        content = '''"""Module with dead code."""

def used_function() -> str:
    return "used"

def unused_function() -> str:
    return "never called"

result = used_function()
'''
        py_file.write_text(content)

        is_valid, issues = DeadCodeDetector.detect_dead_code(py_file)

        # Should detect unused function
        unused_issues = [i for i in issues if "unused" in i.message.lower()]
        assert len(unused_issues) > 0

    def test_syntax_error_handling(self, temp_skill_dir):
        """Test handling of syntax errors."""
        py_file = temp_skill_dir / "syntax_error.py"
        py_file.write_text("def broken(:\n    pass")

        is_valid, issues = DeadCodeDetector.detect_dead_code(py_file)

        assert not is_valid
        assert any(i.severity == "critical" for i in issues)


class TestQualityEnforcer:
    """Tests for the quality enforcer."""

    def test_quality_enforcer_initialization(self, temp_skill_dir):
        """Test initialization of quality enforcer."""
        skill_path = temp_skill_dir / "test-skill"
        skill_path.mkdir()

        enforcer = QualityEnforcer(skill_path)

        assert enforcer.skill_name == "test-skill"
        assert enforcer.skill_path == skill_path

    def test_type_hints_validation(self, temp_skill_dir):
        """Test type hints validation through enforcer."""
        skill_path = temp_skill_dir / "test-skill"
        skill_path.mkdir()

        # Create a well-typed file
        py_file = skill_path / "module.py"
        content = '''"""Well-typed module."""

def add(a: int, b: int) -> int:
    """Add numbers."""
    return a + b
'''
        py_file.write_text(content)

        enforcer = QualityEnforcer(skill_path)
        result = enforcer.validate_type_hints()

        assert isinstance(result, QualityCheckResult)
        assert result.check_type == "TYPE_HINTS"
        assert result.details["files_checked"] >= 1

    def test_docstring_validation(self, temp_skill_dir):
        """Test docstring validation through enforcer."""
        skill_path = temp_skill_dir / "test-skill"
        skill_path.mkdir()

        # Create a well-documented file
        py_file = skill_path / "module.py"
        content = '''"""Well-documented module."""

def function() -> str:
    """A function."""
    return "result"
'''
        py_file.write_text(content)

        enforcer = QualityEnforcer(skill_path)
        result = enforcer.validate_docstrings()

        assert isinstance(result, QualityCheckResult)
        assert result.check_type == "DOCSTRINGS"
        assert result.details["files_checked"] >= 1

    def test_overall_quality_score(self, temp_skill_dir):
        """Test overall quality score calculation."""
        skill_path = temp_skill_dir / "test-skill"
        skill_path.mkdir()

        # Create a reasonable quality file
        py_file = skill_path / "module.py"
        content = '''"""A test module."""

def function(x: int) -> int:
    """Process a number."""
    return x * 2
'''
        py_file.write_text(content)

        enforcer = QualityEnforcer(skill_path)
        report = enforcer.run_all_checks()

        assert 0 <= report.overall_score <= 100
        assert len(report.checks) >= 5  # Should have run multiple checks


class TestQualityReporting:
    """Tests for quality report generation."""

    def test_quality_report_structure(self, temp_skill_dir):
        """Test structure of quality report."""
        skill_path = temp_skill_dir / "test-skill"
        skill_path.mkdir()

        enforcer = QualityEnforcer(skill_path)
        report = enforcer.run_all_checks()

        # Check report structure
        assert report.skill_name == "test-skill"
        assert report.skill_path == skill_path
        assert isinstance(report.overall_score, float)
        assert isinstance(report.is_compliant, bool)
        assert len(report.checks) > 0

    def test_compliance_determination(self, temp_skill_dir):
        """Test compliance determination."""
        skill_path = temp_skill_dir / "test-skill"
        skill_path.mkdir()

        enforcer = QualityEnforcer(skill_path)
        report = enforcer.run_all_checks()

        # Compliance requires score >= 90
        if report.overall_score >= 90:
            assert report.is_compliant is True
        else:
            assert report.is_compliant is False


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_skill_directory(self, temp_skill_dir):
        """Test handling of empty skill directory."""
        skill_path = temp_skill_dir / "empty-skill"
        skill_path.mkdir()

        enforcer = QualityEnforcer(skill_path)
        result = enforcer.validate_type_hints()

        # Should handle empty directory gracefully
        assert result.details["files_checked"] == 0

    def test_nested_python_files(self, temp_skill_dir):
        """Test validation of nested Python files."""
        skill_path = temp_skill_dir / "test-skill"
        skill_path.mkdir()

        # Create nested structure
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir()
        py_file = scripts_dir / "main.py"
        py_file.write_text('"""A script."""\n\ndef main() -> None:\n    """Main function."""\n    pass')

        enforcer = QualityEnforcer(skill_path)
        result = enforcer.validate_docstrings()

        # Should find the nested file
        assert result.details["files_checked"] >= 1
