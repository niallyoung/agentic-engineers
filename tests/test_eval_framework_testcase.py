"""
Unit tests for TestCase class
"""

import pytest
import tempfile
from pathlib import Path
import yaml

from src.skills._meta.evaluation_framework.test_case import TestCase, TestCaseValidationError


class TestTestCaseCreation:
    """Test TestCase creation and validation."""
    
    def test_valid_test_case(self):
        """Test creating a valid test case."""
        tc = TestCase(
            id="test-001",
            name="Test case 1",
            harnesses=["opencode", "copilot"],
            models=["haiku", "sonnet"],
            prompt="Test prompt",
            expected_contains=["output"],
            timeout_seconds=30,
        )
        assert tc.id == "test-001"
        assert tc.name == "Test case 1"
        assert len(tc.harnesses) == 2
        assert len(tc.models) == 2
    
    def test_missing_id(self):
        """Test that missing id raises validation error."""
        with pytest.raises(TestCaseValidationError):
            TestCase(
                id="",
                name="Test",
                harnesses=["opencode"],
                models=["haiku"],
                prompt="Test",
            )
    
    def test_missing_prompt_and_delegation(self):
        """Test that either prompt or delegation must be provided."""
        with pytest.raises(TestCaseValidationError):
            TestCase(
                id="test-001",
                name="Test",
                harnesses=["opencode"],
                models=["haiku"],
            )
    
    def test_both_prompt_and_delegation(self):
        """Test that both prompt and delegation cannot be provided."""
        with pytest.raises(TestCaseValidationError):
            TestCase(
                id="test-001",
                name="Test",
                harnesses=["opencode"],
                models=["haiku"],
                prompt="Prompt",
                delegation="Delegation",
            )
    
    def test_invalid_harness(self):
        """Test that invalid harness raises validation error."""
        with pytest.raises(TestCaseValidationError):
            TestCase(
                id="test-001",
                name="Test",
                harnesses=["invalid-harness"],
                models=["haiku"],
                prompt="Test",
            )
    
    def test_invalid_model(self):
        """Test that invalid model raises validation error."""
        with pytest.raises(TestCaseValidationError):
            TestCase(
                id="test-001",
                name="Test",
                harnesses=["opencode"],
                models=["invalid-model"],
                prompt="Test",
            )
    
    def test_invalid_timeout(self):
        """Test that invalid timeout raises validation error."""
        with pytest.raises(TestCaseValidationError):
            TestCase(
                id="test-001",
                name="Test",
                harnesses=["opencode"],
                models=["haiku"],
                prompt="Test",
                timeout_seconds=0,
            )
    
    def test_invalid_severity(self):
        """Test that invalid severity raises validation error."""
        with pytest.raises(TestCaseValidationError):
            TestCase(
                id="test-001",
                name="Test",
                harnesses=["opencode"],
                models=["haiku"],
                prompt="Test",
                severity="invalid",
            )


class TestTestCaseYAMLLoading:
    """Test TestCase loading from YAML."""
    
    def test_load_valid_yaml(self):
        """Test loading a valid test case from YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "test.yaml"
            yaml_path.write_text("""
id: test-001
name: Test case
harnesses:
  - opencode
  - copilot
models:
  - haiku
  - sonnet
prompt: Test prompt
expected_contains:
  - output
timeout_seconds: 30
            """)
            
            tc = TestCase.from_yaml(yaml_path)
            assert tc.id == "test-001"
            assert tc.name == "Test case"
            assert len(tc.harnesses) == 2
            assert len(tc.models) == 2
    
    def test_load_invalid_yaml(self):
        """Test that loading invalid YAML raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "test.yaml"
            yaml_path.write_text("invalid: yaml: content: [")
            
            with pytest.raises(TestCaseValidationError):
                TestCase.from_yaml(yaml_path)
    
    def test_load_missing_file(self):
        """Test that loading missing file raises error."""
        with pytest.raises(TestCaseValidationError):
            TestCase.from_yaml(Path("/nonexistent/path.yaml"))


class TestTestCaseSerialization:
    """Test TestCase serialization to/from dict and YAML."""
    
    def test_to_dict(self):
        """Test converting test case to dictionary."""
        tc = TestCase(
            id="test-001",
            name="Test",
            harnesses=["opencode"],
            models=["haiku"],
            prompt="Test",
            expected_contains=["output"],
        )
        d = tc.to_dict()
        assert d["id"] == "test-001"
        assert d["name"] == "Test"
        assert d["harnesses"] == ["opencode"]
        assert d["models"] == ["haiku"]
    
    def test_roundtrip_yaml(self):
        """Test roundtrip: TestCase -> YAML -> TestCase."""
        tc1 = TestCase(
            id="test-001",
            name="Test case",
            harnesses=["opencode", "copilot"],
            models=["haiku", "sonnet"],
            prompt="Test prompt",
            expected_contains=["output"],
            expected_not_contains=["error"],
            timeout_seconds=45,
            category="delegation",
            severity="high",
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "test.yaml"
            tc1.to_yaml(yaml_path)
            tc2 = TestCase.from_yaml(yaml_path)
            
            assert tc1.id == tc2.id
            assert tc1.name == tc2.name
            assert tc1.harnesses == tc2.harnesses
            assert tc1.models == tc2.models
            assert tc1.prompt == tc2.prompt
            assert tc1.expected_contains == tc2.expected_contains
            assert tc1.timeout_seconds == tc2.timeout_seconds
