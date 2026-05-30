"""Standard DELEGATE/HANDBACK protocol for skill invocation tests."""

from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
import yaml
import uuid


class DelegateGenerator:
    """Generate standard DELEGATE blocks for skill testing."""

    @staticmethod
    def create_skill_test_delegate(
        skill_name: str,
        harness: str,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a standard DELEGATE for testing a skill.
        
        Args:
            skill_name: Name of the skill to test
            harness: Target harness (copilot, claude, opencode, pi)
            task_id: Optional task ID (auto-generated if not provided)
            
        Returns:
            Dictionary representing the DELEGATE block
        """
        if task_id is None:
            timestamp = datetime.now().strftime("%Y-%m-%d")
            task_uuid = str(uuid.uuid4())[:8]
            task_id = f"{timestamp}-skill-test-{harness}-{skill_name}-{task_uuid}"
        
        delegate = {
            "handoff_type": "DELEGATE",
            "task_id": task_id,
            "type": "skill_test",
            "role": "quality_engineer",
            "model": "claude-sonnet-4.6",
            "effort": "low",
            "estimated_hours": 1,
            "harness": harness,
            "skill": skill_name,
            "scope": f"Test skill '{skill_name}' on harness '{harness}' for interoperability validation",
            "success_criteria": [
                f"Skill '{skill_name}' loads successfully on harness '{harness}'",
                "DELEGATE block is valid per spec-core-v1.0.yaml",
                "HANDBACK block is returned with proper schema",
                "Latency is within acceptable bounds (<5 seconds)",
                "No critical errors in skill execution",
            ],
            "context": f"""
This is a skill interoperability test. We are validating that the skill '{skill_name}' 
can be invoked successfully on the '{harness}' harness. This is part of the TASK-EVALS-003 
skill interoperability matrix evaluation.

Target: Ensure all 14+ skills work correctly across all 4 harnesses (56+ combinations).

Test includes:
- Skill availability check
- DELEGATE protocol validation
- Skill invocation on target harness
- HANDBACK protocol validation
- Latency measurement
- Failure mode detection
            """.strip(),
            "plan": [
                f"Step 1: Load skill metadata for '{skill_name}'",
                f"Step 2: Validate skill is available on harness '{harness}'",
                f"Step 3: Create standard DELEGATE block for skill test",
                f"Step 4: Invoke skill with test DELEGATE",
                f"Step 5: Capture HANDBACK response",
                f"Step 6: Validate HANDBACK schema compliance",
                f"Step 7: Measure latency and collect metrics",
                f"Step 8: Report success/failure with detailed diagnostics",
            ],
            "spec_version": "1.0",
            "created_at": datetime.now().isoformat(),
        }
        
        return delegate

    @staticmethod
    def save_delegate(
        delegate: Dict[str, Any],
        output_path: Path,
    ) -> Path:
        """Save DELEGATE to YAML file.
        
        Args:
            delegate: DELEGATE block dictionary
            output_path: Path to save the YAML file
            
        Returns:
            Path where file was saved
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            yaml.dump(delegate, f, default_flow_style=False, sort_keys=False)
        
        return output_path


class HandbackValidator:
    """Validate HANDBACK blocks conform to protocol."""

    REQUIRED_FIELDS = {
        "handoff_type",
        "task_id",
        "type",
        "status",
        "spec_version",
    }

    OPTIONAL_FIELDS = {
        "deliverables",
        "tests",
        "quality_score",
        "tokens_in",
        "tokens_out",
        "cost_usd",
        "effort_actual",
        "duration_minutes",
        "notes",
        "error_message",
    }

    STATUS_VALUES = {
        "complete",
        "failed",
        "partial",
        "blocked",
        "skipped",
    }

    @classmethod
    def validate_handback(cls, handback: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate HANDBACK schema compliance.
        
        Args:
            handback: HANDBACK block dictionary
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        for field in cls.REQUIRED_FIELDS:
            if field not in handback:
                errors.append(f"Missing required field: {field}")
        
        # Check handoff_type
        if handback.get("handoff_type") != "HANDBACK":
            errors.append(f"handoff_type must be 'HANDBACK', got '{handback.get('handoff_type')}'")
        
        # Check status
        status = handback.get("status")
        if status not in cls.STATUS_VALUES:
            errors.append(f"status must be one of {cls.STATUS_VALUES}, got '{status}'")
        
        # Check spec_version
        spec_version = handback.get("spec_version")
        if spec_version != "1.0":
            errors.append(f"spec_version must be '1.0', got '{spec_version}'")
        
        # Check task_id format
        task_id = handback.get("task_id")
        if task_id and not isinstance(task_id, str):
            errors.append(f"task_id must be a string, got {type(task_id)}")
        
        return len(errors) == 0, errors

    @classmethod
    def load_and_validate_handback(cls, handback_path: Path) -> Tuple[bool, Optional[Dict[str, Any]], List[str]]:
        """Load HANDBACK from YAML and validate.
        
        Args:
            handback_path: Path to HANDBACK YAML file
            
        Returns:
            Tuple of (is_valid, handback_dict, errors)
        """
        errors = []
        
        if not handback_path.exists():
            return False, None, [f"HANDBACK file not found: {handback_path}"]
        
        try:
            with open(handback_path, 'r') as f:
                handback = yaml.safe_load(f)
        except Exception as e:
            return False, None, [f"Failed to parse HANDBACK YAML: {str(e)}"]
        
        is_valid, validation_errors = cls.validate_handback(handback)
        
        return is_valid, handback, validation_errors
