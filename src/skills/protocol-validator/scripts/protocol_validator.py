"""
Protocol Validator — Phase 4 Self-Referential Protocol Implementation.

Validates DELEGATE/HANDBACK against protocol spec (docs/specs/protocol-core-v1.0.yaml).

Key features:
- Load spec at runtime (supports schema evolution)
- Core validation: strict, <1ms
- Extension validation: loose, <2ms
- Unknown field handling: log as warning, don't fail
- Forward-compatible: can validate against new spec versions
"""

import yaml
import time
from typing import Tuple, List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import logging

# Import Phase 3 core validator (reuse instead of rewrite)
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'queue-management' / 'scripts'))
from core_protocol_validator import CoreProtocolValidator, ExtensionValidator

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validation with performance metrics."""
    valid: bool
    errors: List[str]  # Core errors (failures)
    warnings: List[str]  # Extension warnings or unknown fields
    duration_ms: float
    field_types: Dict[str, str]  # Inferred types for debugging


class ProtocolValidator:
    """
    Runtime protocol validator for DELEGATE/HANDBACK messages.
    
    Loads specification from YAML, validates core and extension fields,
    handles unknown fields with forward-compatibility.
    
    Performance: <5ms total (core <1ms, extensions <2ms).
    """

    def __init__(self, spec_path: str = "docs/specs/protocol-core-v1.0.yaml"):
        """
        Initialize validator with spec file.
        
        Args:
            spec_path: Path to protocol spec YAML (relative to repo root)
        
        Raises:
            FileNotFoundError: If spec file not found
            yaml.YAMLError: If spec YAML is malformed
        """
        self.spec_path = Path(spec_path)
        
        # Find spec relative to repo root if path is relative
        if not self.spec_path.is_absolute():
            repo_root = Path(__file__).resolve().parents[4]  # src/skills/protocol-validator/scripts/script.py -> repo root
            self.spec_path = repo_root / spec_path
        
        if not self.spec_path.exists():
            raise FileNotFoundError(f"Protocol spec not found: {self.spec_path}")
        
        # Load and cache spec
        with open(self.spec_path, 'r') as f:
            self.spec = yaml.safe_load(f)
        
        if not self.spec:
            raise ValueError(f"Protocol spec is empty: {self.spec_path}")
        
        # Extract spec version
        self.version = self.spec.get('version', 'unknown')
        
        # Cache core validators
        self._core_validator = CoreProtocolValidator()
        self._extension_validator = ExtensionValidator()
        
        # Cache known extension field names for forward-compatibility check
        self._known_delegate_extensions = set(self.spec.get('delegate', {}).get('extensions', {}).keys())
        self._known_handback_extensions = set(self.spec.get('handback', {}).get('extensions', {}).keys())
        
        logger.info(f"ProtocolValidator initialized with spec v{self.version} from {self.spec_path}")

    def validate_delegate(self, delegate: Dict[str, Any]) -> ValidationResult:
        """
        Validate a DELEGATE against protocol spec.
        
        Args:
            delegate: DELEGATE dict to validate
        
        Returns:
            ValidationResult with valid/errors/warnings/duration
        """
        start_time = time.time()
        errors = []
        warnings = []
        field_types = {}
        
        # 1. Validate core fields (uses Phase 3 validator)
        core_valid, core_errors = self._core_validator.validate_delegate_core(delegate)
        errors.extend(core_errors)
        
        # 2. Validate extension fields
        ext_valid, ext_errors = self._extension_validator.validate_extensions(delegate)
        errors.extend(ext_errors)
        
        # 3. Check for unknown fields (forward-compatibility)
        known_fields = set(self.spec.get('delegate', {}).get('core_fields', {}).keys()) | self._known_delegate_extensions
        for key in delegate.keys():
            if key not in known_fields:
                warnings.append(f"Unknown field '{key}' in DELEGATE (will be ignored in current validator)")
        
        # 4. Infer field types (for debugging)
        for key, value in delegate.items():
            field_types[key] = type(value).__name__
        
        # 5. Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Valid if no core errors (extensions don't block validation)
        valid = len(errors) == 0
        
        return ValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            duration_ms=duration_ms,
            field_types=field_types,
        )

    def validate_handback(self, handback: Dict[str, Any]) -> ValidationResult:
        """
        Validate a HANDBACK against protocol spec.
        
        Args:
            handback: HANDBACK dict to validate
        
        Returns:
            ValidationResult with valid/errors/warnings/duration
        """
        start_time = time.time()
        errors = []
        warnings = []
        field_types = {}
        
        # 1. Validate core fields
        core_valid, core_errors = self._core_validator.validate_handback_core(handback)
        errors.extend(core_errors)
        
        # 2. Validate extension fields
        ext_valid, ext_errors = self._extension_validator.validate_handback_extensions(handback)
        errors.extend(ext_errors)
        
        # 3. Check for unknown fields
        known_fields = set(self.spec.get('handback', {}).get('core_fields', {}).keys()) | self._known_handback_extensions
        for key in handback.keys():
            if key not in known_fields:
                warnings.append(f"Unknown field '{key}' in HANDBACK (will be ignored)")
        
        # 4. Infer field types
        for key, value in handback.items():
            field_types[key] = type(value).__name__
        
        # 5. Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Valid if no core errors
        valid = len(errors) == 0
        
        return ValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            duration_ms=duration_ms,
            field_types=field_types,
        )

    def get_spec(self) -> Dict[str, Any]:
        """Get the currently loaded protocol spec."""
        return self.spec

    def get_version(self) -> str:
        """Get protocol spec version."""
        return self.version


def main():
    """CLI entry point for protocol validation."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(
        description="Validate DELEGATE/HANDBACK against protocol spec"
    )
    parser.add_argument(
        '--delegate',
        help='Path to DELEGATE YAML/JSON file to validate'
    )
    parser.add_argument(
        '--handback',
        help='Path to HANDBACK YAML/JSON file to validate'
    )
    parser.add_argument(
        '--spec',
        default='docs/specs/protocol-core-v1.0.yaml',
        help='Path to protocol spec YAML (default: docs/specs/protocol-core-v1.0.yaml)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output validation result as JSON'
    )
    
    args = parser.parse_args()
    
    if not args.delegate and not args.handback:
        parser.error("Must specify either --delegate or --handback")
    
    # Initialize validator
    try:
        validator = ProtocolValidator(spec_path=args.spec)
    except Exception as e:
        print(f"❌ Failed to initialize validator: {e}")
        return 1
    
    # Load and validate file
    try:
        if args.delegate:
            with open(args.delegate, 'r') as f:
                delegate = yaml.safe_load(f)
            result = validator.validate_delegate(delegate)
            task_id = delegate.get('task_id', 'unknown')
        else:
            with open(args.handback, 'r') as f:
                handback = yaml.safe_load(f)
            result = validator.validate_handback(handback)
            task_id = handback.get('task_id', 'unknown')
    except Exception as e:
        print(f"❌ Failed to load file: {e}")
        return 1
    
    # Output result
    if args.json:
        output = {
            'valid': result.valid,
            'task_id': task_id,
            'errors': result.errors,
            'warnings': result.warnings,
            'duration_ms': result.duration_ms,
        }
        print(json.dumps(output, indent=2))
    else:
        if result.valid:
            print(f"✅ Valid (task_id: {task_id}, duration: {result.duration_ms:.2f}ms)")
        else:
            print(f"❌ Invalid (task_id: {task_id})")
            for error in result.errors:
                print(f"   Error: {error}")
        
        if result.warnings:
            for warning in result.warnings:
                print(f"   ⚠️  {warning}")
    
    return 0 if result.valid else 1


if __name__ == '__main__':
    exit(main())
