"""Data models for skill interoperability testing."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime


class TestStatus(str, Enum):
    """Test result status codes."""
    PASS = "✅"
    FAIL = "❌"
    YELLOW = "🟡"
    TIMEOUT = "⏱"
    UNAVAILABLE = "⊘"
    SKIPPED = "⊘"


class FailureMode(str, Enum):
    """Types of failures that can occur during skill invocation."""
    SKILL_UNAVAILABLE = "skill_unavailable"
    INVOCATION_FAILED = "invocation_failed"
    SCHEMA_INVALID = "schema_invalid"
    LATENCY_EXCEEDED = "latency_exceeded"
    HANDBACK_MISSING = "handback_missing"
    DELEGATE_INVALID = "delegate_invalid"
    UNKNOWN = "unknown"


@dataclass
class SkillTestResult:
    """Result of testing a single skill on a single harness."""
    skill_name: str
    harness: str
    status: TestStatus
    success_rate: float  # 0.0-1.0
    latency_ms: float
    failure_mode: Optional[FailureMode] = None
    error_message: Optional[str] = None
    delegate_path: Optional[str] = None
    handback_path: Optional[str] = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "skill_name": self.skill_name,
            "harness": self.harness,
            "status": self.status.value,
            "success_rate": self.success_rate,
            "latency_ms": self.latency_ms,
            "failure_mode": self.failure_mode.value if self.failure_mode else None,
            "error_message": self.error_message,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": self.cost_usd,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @property
    def is_success(self) -> bool:
        """Check if test passed."""
        return self.status == TestStatus.PASS

    @property
    def is_warning(self) -> bool:
        """Check if test is in warning state (80-95% success)."""
        return self.status == TestStatus.YELLOW

    @property
    def is_failure(self) -> bool:
        """Check if test failed."""
        return self.status == TestStatus.FAIL


@dataclass
class MatrixCell:
    """Single cell in the interoperability matrix."""
    skill_name: str
    harness: str
    result: Optional[SkillTestResult] = None
    
    @property
    def display_status(self) -> str:
        """Get display string for this cell."""
        if self.result is None:
            return "⊘"
        return self.result.status.value


@dataclass
class MatrixResult:
    """Overall interoperability matrix test result."""
    timestamp: datetime = field(default_factory=datetime.now)
    total_combinations: int = 0
    passed: int = 0
    warned: int = 0
    failed: int = 0
    skipped: int = 0
    cells: List[SkillTestResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def overall_success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_combinations == 0:
            return 0.0
        return self.passed / self.total_combinations

    @property
    def quality_score(self) -> float:
        """Calculate quality score (0-100)."""
        if self.total_combinations == 0:
            return 0.0
        # 95%+ = 100, 80-95% = 75-99, <80% = 0-75
        rate = self.overall_success_rate
        if rate >= 0.95:
            return 100.0
        elif rate >= 0.80:
            return 75.0 + (rate - 0.80) * 100
        else:
            return rate * 75

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "summary": {
                "total_combinations": self.total_combinations,
                "passed": self.passed,
                "warned": self.warned,
                "failed": self.failed,
                "skipped": self.skipped,
                "overall_success_rate": self.overall_success_rate,
                "quality_score": self.quality_score,
            },
            "cells": [cell.to_dict() for cell in self.cells],
            "metadata": self.metadata,
        }

    def add_result(self, result: SkillTestResult) -> None:
        """Add a test result to the matrix."""
        self.cells.append(result)
        self.total_combinations += 1
        
        if result.status == TestStatus.PASS:
            self.passed += 1
        elif result.status == TestStatus.YELLOW:
            self.warned += 1
        elif result.status == TestStatus.FAIL:
            self.failed += 1
        elif result.status == TestStatus.SKIPPED:
            self.skipped += 1


@dataclass
class SkillInvocationTest:
    """Test specification for skill invocation."""
    skill_name: str
    harness: str
    timeout_seconds: int = 30
    latency_threshold_ms: float = 5000.0  # 5 second threshold
    max_retries: int = 3
    expected_fields: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
