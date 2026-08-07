#!/usr/bin/env python3
"""
ModelResolver wrapper: Re-exports canonical implementation for backward compatibility.

DEPRECATED: This module is a thin wrapper re-exporting src.orchestration.models.canonical_resolver.
All new code should import directly from src.orchestration.models.

This wrapper preserves backward compatibility for code that imports from this path.
"""

from src.orchestration.models.canonical_resolver import (
    ModelResolver,
    ModelNotFoundError,
    ValidationError,
    FABLE_5_MODEL,
)

__all__ = [
    "ModelResolver",
    "ModelNotFoundError",
    "ValidationError",
    "FABLE_5_MODEL",
]
