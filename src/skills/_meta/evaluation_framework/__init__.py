"""
Evaluation Framework for agentic-engineers

This module provides a comprehensive test harness for validating framework compatibility
across different harnesses and models. It includes:

- TestCase: Data class for defining test cases
- TestRunner: Executes tests against harnesses and captures results
- Reporters: JSON and Markdown result reporting
- CLI: Command-line interface for running tests
"""

__version__ = "1.0.0"
__author__ = "agentic-engineers"

from .test_case import TestCase, TestCaseValidationError
from .framework import TestRunner, TestResult, CompatibilityMatrix, TestStatus
from .reporters import JSONReporter, MarkdownReporter, CSVReporter

__all__ = [
    "TestCase",
    "TestCaseValidationError",
    "TestRunner",
    "TestResult",
    "CompatibilityMatrix",
    "TestStatus",
    "JSONReporter",
    "MarkdownReporter",
    "CSVReporter",
]
