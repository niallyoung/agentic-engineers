"""Pytest configuration and fixtures for queue-management tests."""

import pytest

# Sample strings with minimum required words
VALID_SCOPE = "This is an implementation task that requires careful design with comprehensive testing across all error scenarios and edge cases"  # 19 words (>=15)
VALID_CONTEXT = "This is the context for task execution and includes important information about requirements and specifications for successful completion here today and tomorrow"  # 22 words (>=20)
VALID_PLAN_STEP1 = "Implement the core functionality with proper error handling and validation"  # 10 words (>=3)
VALID_PLAN_STEP2 = "Write comprehensive tests for all code paths and edge cases"  # 10 words (>=3)
