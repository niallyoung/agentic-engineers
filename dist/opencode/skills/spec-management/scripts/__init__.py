"""
spec-management skill modules.

Core modules:
- spec_manager: Main orchestrator
- change_validator: Proposal validation
- authorizer: Role-based access control
- impact_analyzer: Impact analysis
- audit_logger: Immutable audit trail
- changelog_generator: CHANGELOG updates
- rollback_manager: Version tracking & rollback
"""

from .spec_manager import SpecManager, ChangeProposal, SubmissionResult
from .change_validator import ChangeValidator, ValidationResult
from .authorizer import Authorizer
from .impact_analyzer import ImpactAnalyzer, ImpactAnalysis
from .audit_logger import AuditLogger, AuditEntry, ApprovalEntry, ImmutableError
from .changelog_generator import ChangelogGenerator
from .rollback_manager import RollbackManager, SpecVersion

__all__ = [
    "SpecManager",
    "ChangeProposal",
    "SubmissionResult",
    "ChangeValidator",
    "ValidationResult",
    "Authorizer",
    "ImpactAnalyzer",
    "ImpactAnalysis",
    "AuditLogger",
    "AuditEntry",
    "ApprovalEntry",
    "ImmutableError",
    "ChangelogGenerator",
    "RollbackManager",
    "SpecVersion",
]
