"""
TestCase class definition for evaluation framework

Defines the structure and validation rules for test cases in the evaluation framework.
Test cases can be defined in YAML or as Python dataclasses.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import yaml
from pathlib import Path


class TestCaseValidationError(Exception):
    """Raised when a test case fails validation."""
    pass


@dataclass
class TestCase:
    """
    Represents a single test case for harness/model compatibility testing.
    
    Attributes:
        id: Unique identifier for the test case (e.g., "test-delegate-basic-001")
        name: Human-readable test name
        harnesses: List of harnesses to test (e.g., ["opencode", "copilot", "claude-code"])
        models: List of models to test (e.g., ["haiku", "sonnet", "opus"])
        prompt: The test prompt/input to send to the harness
        delegation: Optional: A DELEGATE block instead of a prompt
        expected_contains: List of strings that should appear in the output
        expected_not_contains: List of strings that should NOT appear in the output
        timeout_seconds: Maximum time allowed for test execution
        requirements: Optional list of requirements or setup instructions
        category: Test category (e.g., "delegation", "prompt", "skill")
        severity: Test severity - "critical", "high", "medium", "low"
    """
    
    id: str
    name: str
    harnesses: List[str]
    models: List[str]
    timeout_seconds: int = 30
    category: str = "general"
    severity: str = "medium"
    expected_contains: List[str] = field(default_factory=list)
    expected_not_contains: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    prompt: Optional[str] = None
    delegation: Optional[str] = None
    
    def __post_init__(self):
        """Validate test case after initialization."""
        self.validate()
    
    def validate(self):
        """
        Validate the test case for correctness.
        
        Raises:
            TestCaseValidationError: If validation fails
        """
        # Check required fields
        if not self.id or not isinstance(self.id, str):
            raise TestCaseValidationError("id must be a non-empty string")
        
        if not self.name or not isinstance(self.name, str):
            raise TestCaseValidationError("name must be a non-empty string")
        
        if not self.harnesses or not isinstance(self.harnesses, list):
            raise TestCaseValidationError("harnesses must be a non-empty list")
        
        if not self.models or not isinstance(self.models, list):
            raise TestCaseValidationError("models must be a non-empty list")
        
        # Check that at least prompt or delegation is provided
        if not self.prompt and not self.delegation:
            raise TestCaseValidationError("Either 'prompt' or 'delegation' must be provided")
        
        if self.prompt and self.delegation:
            raise TestCaseValidationError("Only one of 'prompt' or 'delegation' can be provided")
        
        # Validate harnesses
        valid_harnesses = {"opencode", "copilot", "claude-code", "pi-dev"}
        for harness in self.harnesses:
            if harness not in valid_harnesses:
                raise TestCaseValidationError(
                    f"Invalid harness '{harness}'. Must be one of: {valid_harnesses}"
                )
        
        # Validate models
        valid_models = {"haiku", "sonnet", "opus"}
        for model in self.models:
            if model not in valid_models:
                raise TestCaseValidationError(
                    f"Invalid model '{model}'. Must be one of: {valid_models}"
                )
        
        # Validate timeout
        if not isinstance(self.timeout_seconds, int) or self.timeout_seconds <= 0:
            raise TestCaseValidationError("timeout_seconds must be a positive integer")
        
        # Validate severity
        valid_severities = {"critical", "high", "medium", "low"}
        if self.severity not in valid_severities:
            raise TestCaseValidationError(
                f"Invalid severity '{self.severity}'. Must be one of: {valid_severities}"
            )
    
    @staticmethod
    def from_yaml(yaml_path: Path) -> "TestCase":
        """
        Load a test case from a YAML file.
        
        Args:
            yaml_path: Path to YAML file
            
        Returns:
            Loaded TestCase instance
            
        Raises:
            TestCaseValidationError: If YAML is invalid or test case fails validation
        """
        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
        except Exception as e:
            raise TestCaseValidationError(f"Failed to load YAML from {yaml_path}: {e}")
        
        if not isinstance(data, dict):
            raise TestCaseValidationError(f"YAML file must contain a dictionary, got {type(data)}")
        
        try:
            return TestCase(**data)
        except TypeError as e:
            raise TestCaseValidationError(f"Invalid TestCase fields: {e}")
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "TestCase":
        """
        Create a test case from a dictionary.
        
        Args:
            data: Dictionary with test case fields
            
        Returns:
            Created TestCase instance
            
        Raises:
            TestCaseValidationError: If test case fails validation
        """
        try:
            return TestCase(**data)
        except TypeError as e:
            raise TestCaseValidationError(f"Invalid TestCase fields: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test case to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "harnesses": self.harnesses,
            "models": self.models,
            "timeout_seconds": self.timeout_seconds,
            "category": self.category,
            "severity": self.severity,
            "expected_contains": self.expected_contains,
            "expected_not_contains": self.expected_not_contains,
            "requirements": self.requirements,
            "prompt": self.prompt,
            "delegation": self.delegation,
        }
    
    def to_yaml(self, yaml_path: Path):
        """
        Save test case to a YAML file.
        
        Args:
            yaml_path: Path to save YAML file
        """
        with open(yaml_path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)
