"""
JSON Schema validation for expanded DELEGATE/HANDBACK protocol.
"""

import json
from typing import Dict, List, Optional


# JSON Schema for expanded DELEGATE
DELEGATE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Expanded DELEGATE Schema",
    "type": "object",
    "required": ["task_id", "role", "model", "effort", "scope", "plan"],
    "properties": {
        # Core fields
        "task_id": {
            "type": "string",
            "minLength": 5,
            "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9-]+$",
            "description": "Task ID in format YYYY-MM-DD-kebab-case"
        },
        "role": {
            "type": "string",
            "enum": ["engineer", "senior-engineer", "lead-engineer", "principal-engineer", "security-engineer", "quality-engineer"],
            "description": "Agent role"
        },
        "model": {
            "type": "string",
            "enum": ["claude-haiku-4.5", "claude-sonnet-4.6", "claude-opus-4.6", "claude-opus-4.7"],
            "description": "Model to use"
        },
        "effort": {
            "type": "string",
            "enum": ["low", "medium", "high", "extra-high"],
            "description": "Effort level"
        },
        "scope": {
            "type": "string",
            "minLength": 50,
            "description": "Task description (≥15 words)"
        },
        # Quality fields
        "quality_baseline": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
            "description": "Expected quality score"
        },
        "acceptance_criteria": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Acceptance criteria"
        },
        "quality_thresholds": {
            "type": "object",
            "description": "Quality metric thresholds"
        },
        # Execution fields
        "plan": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "description": "Numbered list of steps"
        },
        "estimated_tokens": {
            "type": "integer",
            "minimum": 100,
            "description": "Estimated token budget"
        },
        "estimated_time_minutes": {
            "type": "integer",
            "minimum": 1,
            "description": "Estimated execution time"
        },
    }
}

# JSON Schema for expanded HANDBACK
HANDBACK_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Expanded HANDBACK Schema",
    "type": "object",
    "required": ["task_id", "status", "deliverables", "tests"],
    "properties": {
        # Core fields
        "task_id": {
            "type": "string",
            "minLength": 5,
            "description": "Task ID (matches DELEGATE)"
        },
        "status": {
            "type": "string",
            "enum": ["complete", "failed", "partial", "blocked"],
            "description": "Task status"
        },
        "deliverables": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of deliverables"
        },
        "tests": {
            "type": "object",
            "description": "Test results"
        },
        # Execution metrics
        "tokens_in": {
            "type": "integer",
            "minimum": 0,
            "description": "Input tokens used"
        },
        "tokens_out": {
            "type": "integer",
            "minimum": 0,
            "description": "Output tokens used"
        },
        "time_elapsed_minutes": {
            "type": "integer",
            "minimum": 0,
            "description": "Execution time"
        },
        "cost_actual": {
            "type": "number",
            "minimum": 0,
            "description": "Actual cost in dollars"
        },
        # Quality metrics
        "quality_score": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
            "description": "Quality score"
        },
        "test_coverage": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Test coverage (0-1)"
        },
        "regressions_detected": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of regressions"
        },
    }
}


def validate_delegate(data: Dict) -> List[str]:
    """Validate DELEGATE against schema. Returns list of errors."""
    errors = []
    
    # Check required fields
    required = ["task_id", "role", "model", "effort", "scope", "plan"]
    for field in required:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # Check field types and values
    if "task_id" in data:
        if not isinstance(data["task_id"], str) or len(data["task_id"]) < 5:
            errors.append("task_id must be a string with at least 5 characters")
    
    if "role" in data:
        valid_roles = ["engineer", "senior-engineer", "lead-engineer", "principal-engineer", "security-engineer", "quality-engineer"]
        if data["role"] not in valid_roles:
            errors.append(f"Invalid role: {data['role']}")
    
    if "effort" in data:
        valid_efforts = ["low", "medium", "high", "extra-high"]
        if data["effort"] not in valid_efforts:
            errors.append(f"Invalid effort: {data['effort']}")
    
    if "scope" in data:
        if not isinstance(data["scope"], str) or len(data["scope"].split()) < 15:
            errors.append("scope must be at least 15 words")
    
    if "plan" in data:
        if not isinstance(data["plan"], list) or len(data["plan"]) == 0:
            errors.append("plan must be a non-empty list")
    
    if "quality_baseline" in data:
        if not isinstance(data["quality_baseline"], int) or not 0 <= data["quality_baseline"] <= 100:
            errors.append("quality_baseline must be 0-100")
    
    return errors


def validate_handback(data: Dict) -> List[str]:
    """Validate HANDBACK against schema. Returns list of errors."""
    errors = []
    
    # Check required fields
    required = ["task_id", "status", "deliverables", "tests"]
    for field in required:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # Check field types and values
    if "task_id" in data:
        if not isinstance(data["task_id"], str) or len(data["task_id"]) < 5:
            errors.append("task_id must be a string with at least 5 characters")
    
    if "status" in data:
        valid_statuses = ["complete", "failed", "partial", "blocked"]
        if data["status"] not in valid_statuses:
            errors.append(f"Invalid status: {data['status']}")
    
    if "quality_score" in data:
        if not isinstance(data["quality_score"], int) or not 0 <= data["quality_score"] <= 100:
            errors.append("quality_score must be 0-100")
    
    if "test_coverage" in data:
        if not isinstance(data["test_coverage"], (int, float)) or not 0 <= data["test_coverage"] <= 1:
            errors.append("test_coverage must be 0-1")
    
    return errors


def validate_json_schema(data: Dict, schema: Dict) -> List[str]:
    """Validate data against JSON schema. Returns list of errors."""
    try:
        import jsonschema
        jsonschema.validate(instance=data, schema=schema)
        return []
    except ImportError:
        # jsonschema not available, skip validation
        return []
    except Exception as e:
        return [str(e)]
