"""
Protocol expansion module for DELEGATE/HANDBACK with quality evaluation, feedback, and optimization.

This module implements the expanded DELEGATE/HANDBACK protocol with:
- Expanded DELEGATE schema (20+ fields)
- Expanded HANDBACK schema (25+ fields)
- Quality Evaluation schema
- Feedback/Outcome schema
- Optimization schema
- Event model with 10+ event types
- Artifact linking and traceability
- JSON Schema validation

See docs/PROTOCOL-EXPANSION-INITIATIVE.md for design details.
"""

from .expanded_delegate import ExpandedDelegate
from .expanded_handback import ExpandedHandback
from .quality_evaluation import QualityEvaluation
from .feedback_outcome import FeedbackOutcome
from .optimization import Optimization
from .event_model import Event, EventType
from .artifact_linking import ArtifactLink
from .validation import validate_delegate, validate_handback

__all__ = [
    "ExpandedDelegate",
    "ExpandedHandback",
    "QualityEvaluation",
    "FeedbackOutcome",
    "Optimization",
    "Event",
    "EventType",
    "ArtifactLink",
    "validate_delegate",
    "validate_handback",
]
