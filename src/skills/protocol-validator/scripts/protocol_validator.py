"""
Protocol Validator — Canonical DELEGATE/HANDBACK validator.

This module is the SINGLE SOURCE OF TRUTH for DELEGATE/HANDBACK schema
validation across agentic-engineers. Merged from protocol-validation skill.

Validates DELEGATE/HANDBACK against protocol spec (docs/specs/protocol-core-v1.0.yaml).

Key features:
- Load spec at runtime (supports schema evolution)
- Core validation: strict, <1ms
- Extension validation: loose, <2ms
- Unknown field handling: log as warning, don't fail
- Forward-compatible: can validate against new spec versions

Public API:
    validate_delegate(delegate: dict) -> (valid: bool, errors: list[str])
    validate_handback(handback: dict) -> (valid: bool, errors: list[str])
    ProtocolValidator (class)
    CoreProtocolValidator (class)
    ExtensionValidator (class)
"""

import yaml
import time
import re
from typing import Tuple, List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants and validation patterns
# ---------------------------------------------------------------------------

# Valid agents per Phase 3 spec (uses hyphenated names, unlike old underscore names)
VALID_AGENTS = {
    'orchestrator', 'engineer', 'senior-engineer', 'lead-engineer',
    'principal-engineer', 'security-engineer', 'quality-engineer', 'model-engineer'
}

# CANONICAL HANDBACK status enum — single source of truth.
# All other files in the repo that define their own status sets should
# match this exactly (or be registered as deliberate legacy aliases).
VALID_STATUSES = {'success', 'failure', 'partial', 'blocked', 'escalate'}

# Legacy aliases accepted during transition (map legacy -> canonical).
# Files that accept *only* these without the canonical equivalents are drifted.
LEGACY_STATUS_ALIASES = {'complete': 'success', 'failed': 'failure', 'escalated': 'escalate'}

VALID_EFFORTS = {'low', 'medium', 'high', 'max'}  # 'max' is Security Engineer's tier; 'epic' (seen in some legacy validators) is not canonical

# Forward-compatible additions accepted at runtime before the canonical spec
# update lands elsewhere in the repo.
KNOWN_DELEGATE_RUNTIME_FIELDS = {'token_quota'}
KNOWN_HANDBACK_RUNTIME_FIELDS = {'token_usage', 'skill_feedback'}

# ---------------------------------------------------------------------------
# Enum drift detection
# ---------------------------------------------------------------------------

# Registry of known status-enum definitions across the codebase.
# Each entry: (module_path, set_name, status_set, is_deliberate_superset)
# is_deliberate_superset=True means the set intentionally includes legacy
# aliases for back-compat and is not considered drifted.
_STATUS_REGISTRY: List[Dict[str, Any]] = [
    {
        "path": "src/skills/protocol-validator/scripts/protocol_validator.py",
        "name": "VALID_STATUSES",
        "expected": VALID_STATUSES,
        "allows_legacy": False,
    },
    {
        "path": "src/skills/queue-management/scripts/queue_ops.py",
        "name": "VALID_STATUSES",
        "expected": VALID_STATUSES,
        "allows_legacy": False,
    },
    {
        "path": "src/skills/queue-management/scripts/validators.py",
        "name": "CANONICAL_HANDBACK_STATUSES",
        "expected": VALID_STATUSES,
        "allows_legacy": True,  # deliberately adds legacy aliases
    },
    {
        "path": "src/orchestration/protocol/validation.py",
        "name": "valid_statuses (inline list)",
        "expected": VALID_STATUSES,
        "allows_legacy": False,
    },
    {
        "path": "src/orchestration/agents/quality_validator.py",
        "name": "VALID_HANDBACK_STATUSES",
        "expected": VALID_STATUSES,
        "allows_legacy": False,
    },
]


@dataclass
class EnumDriftFinding:
    """A single enum drift finding."""
    path: str
    name: str
    found: set
    expected: set
    missing: set   # in expected but not in found (canonical values absent)
    extra: set     # in found but not in expected or legacy aliases


@dataclass
class EnumDriftReport:
    """Result of scanning the codebase for HANDBACK status enum drift."""
    canonical: set
    legacy_aliases: set
    findings: List[EnumDriftFinding]

    @property
    def has_drift(self) -> bool:
        return bool(self.findings)

    def to_text(self) -> str:
        if not self.has_drift:
            return "No HANDBACK status enum drift detected."
        lines = [f"HANDBACK status enum drift detected ({len(self.findings)} location(s)):"]
        for f in self.findings:
            lines.append(f"  [{f.path}] {f.name}")
            if f.missing:
                lines.append(f"    MISSING canonical: {sorted(f.missing)}")
            if f.extra:
                lines.append(f"    EXTRA (non-canonical, non-legacy): {sorted(f.extra)}")
        return "\n".join(lines)


def scan_status_enum_drift(repo_root: Optional[Path] = None) -> EnumDriftReport:
    """Scan Python source files for HANDBACK status enum drift.

    Reads each registered file, extracts its status set by grepping for the
    known variable name, and compares against VALID_STATUSES. Files that
    intentionally include legacy aliases (``allows_legacy=True``) are only
    flagged if they are missing canonical values.

    Returns an :class:`EnumDriftReport` listing all drifted locations.
    """
    if repo_root is None:
        repo_root = _repo_root()

    findings: List[EnumDriftFinding] = []

    for entry in _STATUS_REGISTRY:
        full_path = repo_root / entry["path"]
        if not full_path.exists():
            logger.warning("Status registry entry not found on disk: %s", full_path)
            continue

        source = full_path.read_text(encoding="utf-8", errors="replace")
        found_statuses = _extract_status_set(source, entry["name"])

        if found_statuses is None:
            # Could not parse — skip rather than false-positive
            logger.debug("Could not extract status set from %s (%s)", entry["path"], entry["name"])
            continue

        canonical = VALID_STATUSES
        all_allowed = canonical | set(LEGACY_STATUS_ALIASES.keys()) if entry["allows_legacy"] else canonical

        missing = canonical - found_statuses
        extra = found_statuses - all_allowed

        if missing or extra:
            findings.append(EnumDriftFinding(
                path=entry["path"],
                name=entry["name"],
                found=found_statuses,
                expected=canonical,
                missing=missing,
                extra=extra,
            ))

    return EnumDriftReport(
        canonical=VALID_STATUSES,
        legacy_aliases=set(LEGACY_STATUS_ALIASES.keys()),
        findings=findings,
    )


def _extract_status_set(source: str, var_name: str) -> Optional[set]:
    """Extract a Python set/list literal assigned to ``var_name`` from source text.

    Handles common patterns on a *single logical line*:
      VAR = {"a", "b", ...}
      VAR = ["a", "b", ...]
      VAR = {"a", "b"} | {"c"}

    Strategy: find lines containing ``var_name =`` or ``var_name:`` and then
    extract balanced bracket content from that line (plus continuation if the
    bracket is not closed on the same line). This avoids greedy DOTALL matches
    that pull in unrelated code.

    Returns the set of string values, or None if the variable cannot be found.
    """
    var_key = var_name.split(' ')[0]
    # Find the line containing the assignment
    line_pattern = re.compile(
        r'^[ \t]*' + re.escape(var_key) + r'\s*(?:=|:)',
        re.MULTILINE,
    )
    m = line_pattern.search(source)
    if not m:
        return None

    # Extract from the assignment position; collect until the bracket closes
    start = m.start()
    chunk = source[start:start + 2000]  # cap at 2 KB to avoid runaway

    # Find the opening bracket
    bracket_m = re.search(r'[\[\{]', chunk)
    if not bracket_m:
        return None

    opener = bracket_m.group(0)
    closer = ']' if opener == '[' else '}'
    depth = 0
    end_pos = 0
    for i, ch in enumerate(chunk[bracket_m.start():], start=bracket_m.start()):
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                end_pos = i + 1
                break

    if end_pos == 0:
        # Unclosed bracket — take the whole 2KB chunk
        end_pos = len(chunk)

    bracket_content = chunk[bracket_m.start():end_pos]
    # Extract only short lowercase-underscore strings (status tokens are <=15 chars)
    string_values = re.findall(r'["\']([a-z_]{1,15})["\']', bracket_content)
    return set(string_values) if string_values else None

# task_id: kebab-case, 3-50 chars total
TASK_ID_PATTERN = re.compile(r'^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$')


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _count_words(text: str) -> int:
    return len(text.split())


# ---------------------------------------------------------------------------
# Protocol-divergence detection
# ---------------------------------------------------------------------------

@dataclass
class ProtocolDivergence:
    """A single protocol-divergence finding."""
    location: str
    description: str
    severity: str  # error | warning


@dataclass
class ProtocolDivergenceReport:
    """Result of scanning for protocol-divergence issues."""
    findings: List[ProtocolDivergence]

    @property
    def has_issues(self) -> bool:
        return bool(self.findings)

    def to_text(self) -> str:
        if not self.has_issues:
            return "No protocol divergence detected."
        lines = [f"Protocol divergence detected ({len(self.findings)} issue(s)):"]
        for f in self.findings:
            lines.append(f"  [{f.severity.upper()}] {f.location}: {f.description}")
        return "\n".join(lines)


def scan_protocol_divergence(repo_root: Optional[Path] = None) -> ProtocolDivergenceReport:
    """Scan codebase for protocol-divergence issues.

    Detects multiple independent implementations of escalation/validation logic
    that should be unified. For example:
    - Multiple separate escalation handlers when one central handler should be used
    - Custom HANDBACK validators that duplicate the canonical protocol-validator
    - Conflicting queue-state enums across different modules

    Returns a :class:`ProtocolDivergenceReport` listing all divergence issues.
    """
    if repo_root is None:
        repo_root = _repo_root()

    findings: List[ProtocolDivergence] = []

    # Check 1: Look for custom escalation handlers (should use orchestrator polling)
    escalation_patterns = [
        (r"def.*escalate.*\(", "Custom escalation handler (should use orchestrator polling loop)"),
        (r"def.*handle_escalation.*\(", "Custom escalation handler (should use orchestrator)"),
        (r"class.*EscalationHandler", "Custom escalation handler class (should use orchestrator)"),
    ]

    orchestrator_paths = [
        repo_root / "src/orchestration",
        repo_root / "src/agents",
    ]

    for search_dir in orchestrator_paths:
        if not search_dir.exists():
            continue
        for py_file in search_dir.rglob("*.py"):
            if "test" in str(py_file):
                continue
            source = py_file.read_text(encoding="utf-8", errors="replace")
            for pattern, desc in escalation_patterns:
                if re.search(pattern, source):
                    findings.append(ProtocolDivergence(
                        location=str(py_file.relative_to(repo_root)),
                        description=desc,
                        severity="warning",
                    ))

    # Check 2: Look for custom HANDBACK validators (should use protocol-validator skill)
    handback_validator_patterns = [
        (r"def.*validate.*handback", "Custom HANDBACK validator (should use protocol-validator skill)"),
        (r"class.*HandbackValidator", "Custom HANDBACK validator class (should use protocol-validator)"),
    ]

    for search_dir in orchestrator_paths:
        if not search_dir.exists():
            continue
        for py_file in search_dir.rglob("*.py"):
            if "test" in str(py_file) or "protocol_validator" in str(py_file):
                continue
            source = py_file.read_text(encoding="utf-8", errors="replace")
            for pattern, desc in handback_validator_patterns:
                if re.search(pattern, source, re.IGNORECASE):
                    findings.append(ProtocolDivergence(
                        location=str(py_file.relative_to(repo_root)),
                        description=desc,
                        severity="warning",
                    ))

    return ProtocolDivergenceReport(findings=findings)


def _repo_root() -> Path:
    # src/skills/protocol-validator/scripts/protocol_validator.py -> repo root
    return Path(__file__).resolve().parents[4]


def _skill_exists(skill: str) -> bool:
    """Check if a skill exists in the repository's skills directories.

    Looks in both the canonical source layout (src/skills/) and the legacy
    top-level skills/ directory for forward/backward compatibility. If neither
    directory is present (e.g. running outside a checkout) the skill is allowed.
    """
    if not skill or not isinstance(skill, str):
        return False

    repo_root = _repo_root()
    candidate_dirs = [
        repo_root / "src" / "skills",
        repo_root / "skills",
    ]

    existing_dirs = [d for d in candidate_dirs if d.exists()]
    if not existing_dirs:
        return True  # Can't check, allow it

    for skills_dir in existing_dirs:
        if (skills_dir / skill).exists() or (skills_dir / f"{skill}.md").exists():
            return True
    return False


# ---------------------------------------------------------------------------
# Core validators (strict)
# ---------------------------------------------------------------------------

class CoreProtocolValidator:
    """Validate DELEGATE/HANDBACK core fields only (strict, fast <50ms)."""

    def validate_delegate_core(self, delegate: Dict) -> Tuple[bool, List[str]]:
        """Validate 7 required core fields of a DELEGATE."""
        errors: List[str] = []

        if not isinstance(delegate, dict):
            return (False, ["delegate: must be a mapping/object"])

        # 1. task_id: kebab-case, 3-50 chars
        task_id = delegate.get('task_id')
        if not task_id or not isinstance(task_id, str):
            errors.append("task_id: required, must be a string")
        elif not TASK_ID_PATTERN.match(task_id):
            errors.append(f"task_id: must be kebab-case, 3-50 chars (got '{task_id}')")

        # 2. skill: must exist in skills/
        skill = delegate.get('skill')
        if not skill or not isinstance(skill, str):
            errors.append("skill: required, must be a string")
        elif not _skill_exists(skill):
            errors.append(f"skill: unknown skill '{skill}' (not found in skills/)")

        # 3. agent: must be in VALID_AGENTS
        agent = delegate.get('agent')
        if not agent or not isinstance(agent, str):
            errors.append("agent: required, must be a string")
        elif agent not in VALID_AGENTS:
            errors.append(f"agent: invalid agent '{agent}' (must be one of {sorted(VALID_AGENTS)})")

        # 4. scope: >=15 words
        scope = delegate.get('scope', '')
        if not scope or not isinstance(scope, str):
            errors.append("scope: required, must be a string")
        elif _count_words(scope) < 15:
            errors.append(f"scope: must be >=15 words ({_count_words(scope)} provided)")

        # 5. success_criteria: non-empty array
        sc = delegate.get('success_criteria')
        if sc is None:
            errors.append("success_criteria: required")
        elif not isinstance(sc, list) or len(sc) == 0:
            errors.append("success_criteria: must be a non-empty array")

        # 6. plan: >=2 steps, each >=3 words
        plan = delegate.get('plan')
        if plan is None:
            errors.append("plan: required")
        elif not isinstance(plan, list) or len(plan) < 2:
            errors.append(f"plan: must have >=2 steps ({len(plan) if isinstance(plan, list) else 0} provided)")
        else:
            for i, step in enumerate(plan):
                if isinstance(step, str) and _count_words(step) < 3:
                    errors.append(f"plan[{i}]: each step must be >=3 words (got '{step}')")

        # 7. context: >=20 words (string) or non-empty list of strings
        context = delegate.get('context')
        if context is None:
            errors.append("context: required")
        elif isinstance(context, str):
            if _count_words(context) < 20:
                errors.append(f"context: must be >=20 words ({_count_words(context)} provided)")
        elif isinstance(context, list):
            if len(context) == 0:
                errors.append("context: must be non-empty when provided as array")
        else:
            errors.append("context: must be a string or array of strings")

        return (len(errors) == 0, errors)

    def validate_handback_core(self, handback: Dict) -> Tuple[bool, List[str]]:
        """Validate 4 required core fields of a HANDBACK."""
        errors: List[str] = []

        if not isinstance(handback, dict):
            return (False, ["handback: must be a mapping/object"])

        # 1. task_id
        task_id = handback.get('task_id')
        if not task_id or not isinstance(task_id, str):
            errors.append("task_id: required, must be a string")

        # 2. status
        status = handback.get('status')
        if not status:
            errors.append("status: required")
        elif status not in VALID_STATUSES:
            errors.append(f"status: invalid value '{status}' (must be one of {sorted(VALID_STATUSES)})")

        # 3. output: required (any value acceptable, but key must be present)
        if 'output' not in handback:
            errors.append("output: required")

        # 4. metrics: required object with quality, tokens, cost, duration_seconds
        metrics = handback.get('metrics')
        if metrics is None:
            errors.append("metrics: required")
        elif not isinstance(metrics, dict):
            errors.append("metrics: must be an object")
        else:
            q = metrics.get('quality')
            if q is None:
                errors.append("metrics.quality: required")
            elif not isinstance(q, (int, float)) or isinstance(q, bool) or not (0.0 <= q <= 1.0):
                errors.append(f"metrics.quality: must be 0.0-1.0 (got {q})")

            tokens = metrics.get('tokens')
            if tokens is None:
                errors.append("metrics.tokens: required")
            elif not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 0:
                errors.append(f"metrics.tokens: must be non-negative integer (got {tokens})")

            cost = metrics.get('cost')
            if cost is None:
                errors.append("metrics.cost: required")
            elif not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
                errors.append(f"metrics.cost: must be non-negative number (got {cost})")

            dur = metrics.get('duration_seconds')
            if dur is None:
                errors.append("metrics.duration_seconds: required")
            elif not isinstance(dur, (int, float)) or isinstance(dur, bool) or dur < 0:
                errors.append(f"metrics.duration_seconds: must be non-negative number (got {dur})")

        return (len(errors) == 0, errors)


# ---------------------------------------------------------------------------
# Extension validators (loose)
# ---------------------------------------------------------------------------

class ExtensionValidator:
    """Validate optional extension fields (loose, fast <10ms)."""

    def validate_extensions(self, delegate: Dict) -> Tuple[bool, List[str]]:
        """Validate only DELEGATE extension fields with loose validation."""
        errors: List[str] = []

        if 'effort' in delegate:
            if delegate['effort'] not in VALID_EFFORTS:
                errors.append(f"effort: invalid value '{delegate['effort']}' (must be low|medium|high|max)")

        if 'model' in delegate and not isinstance(delegate['model'], str):
            errors.append("model: must be a string")

        if 'budget' in delegate:
            if not isinstance(delegate['budget'], (int, float)) or delegate['budget'] < 0:
                errors.append("budget: must be a non-negative number")

        if 'priority' in delegate:
            p = delegate['priority']
            if not isinstance(p, int) or isinstance(p, bool) or p < 1 or p > 10:
                errors.append(f"priority: must be integer 1-10 (got {p})")

        if 'deadline' in delegate and not isinstance(delegate['deadline'], str):
            errors.append("deadline: must be a string (ISO 8601 format)")

        if 'dependencies' in delegate:
            if not isinstance(delegate['dependencies'], list):
                errors.append("dependencies: must be an array")

        if 'parent_task_id' in delegate and not isinstance(delegate['parent_task_id'], str):
            errors.append("parent_task_id: must be a string")

        if 'retry_context' in delegate and not isinstance(delegate['retry_context'], dict):
            errors.append("retry_context: must be an object")

        return (len(errors) == 0, errors)

    def validate_handback_extensions(self, handback: Dict) -> Tuple[bool, List[str]]:
        """Validate HANDBACK extension fields with loose validation."""
        errors: List[str] = []

        if 'retry_count' in handback:
            if not isinstance(handback['retry_count'], int) or isinstance(handback['retry_count'], bool) or handback['retry_count'] < 0:
                errors.append("retry_count: must be a non-negative integer")

        if 'model_used' in handback and not isinstance(handback['model_used'], str):
            errors.append("model_used: must be a string")

        if 'effort_actual' in handback:
            if handback['effort_actual'] not in VALID_EFFORTS:
                errors.append("effort_actual: invalid value (must be low|medium|high|max)")

        if 'flags' in handback:
            if not isinstance(handback['flags'], list):
                errors.append("flags: must be an array")

        if 'error' in handback and not isinstance(handback['error'], str):
            errors.append("error: must be a string")

        if 'children_created' in handback:
            if not isinstance(handback['children_created'], list):
                errors.append("children_created: must be an array")

        if 'children_results' in handback and not isinstance(handback['children_results'], dict):
            errors.append("children_results: must be an object")

        # Note: skill_feedback validation is deliberately loose (non-blocking).
        # Malformed feedback will not cause HANDBACK validation to fail, allowing
        # agents to include partial/incomplete feedback without breaking the protocol.
        # The feedback loop handles structural issues gracefully.
        if 'skill_feedback' in handback:
            feedback = handback['skill_feedback']
            # Only validate structure if present; don't fail on missing/invalid fields
            if isinstance(feedback, list):
                # Feedback is present and is an array - acceptable regardless of contents
                pass
            # If not a list, we silently accept it anyway (loose validation)

        return (len(errors) == 0, errors)


# ---------------------------------------------------------------------------
# ValidationResult dataclass for ProtocolValidator class
# ---------------------------------------------------------------------------


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
        known_fields |= KNOWN_DELEGATE_RUNTIME_FIELDS
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

        token_usage = handback.get('token_usage')
        if token_usage is not None:
            if not isinstance(token_usage, dict):
                errors.append("token_usage: must be an object")
            else:
                for key in ('input', 'output', 'cached', 'total', 'billable_total'):
                    if key in token_usage:
                        value = token_usage[key]
                        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                            errors.append(f"token_usage.{key}: must be a non-negative integer (got {value})")

        # 3. Check for unknown fields
        known_fields = set(self.spec.get('handback', {}).get('core_fields', {}).keys()) | self._known_handback_extensions
        known_fields |= KNOWN_HANDBACK_RUNTIME_FIELDS
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
    parser.add_argument(
        '--check-enum-drift',
        action='store_true',
        dest='check_enum_drift',
        help='Scan repo for HANDBACK status enum drift across all known locations',
    )
    parser.add_argument(
        '--repo-root',
        default=None,
        help='Repo root for enum drift scan (default: auto-detected)',
    )

    args = parser.parse_args()

    if args.check_enum_drift:
        repo_root = Path(args.repo_root) if args.repo_root else None
        report = scan_status_enum_drift(repo_root=repo_root)
        if args.json:
            import json as _json
            print(_json.dumps({
                "has_drift": report.has_drift,
                "canonical": sorted(report.canonical),
                "legacy_aliases": sorted(report.legacy_aliases),
                "findings": [
                    {
                        "path": f.path,
                        "name": f.name,
                        "found": sorted(f.found),
                        "missing": sorted(f.missing),
                        "extra": sorted(f.extra),
                    }
                    for f in report.findings
                ],
            }, indent=2))
        else:
            print(report.to_text())
        return 1 if report.has_drift else 0

    if not args.delegate and not args.handback:
        parser.error("Must specify --delegate, --handback, or --check-enum-drift")
    
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


# Module-level convenience functions for backward compatibility
# These match the protocol-validation API for drop-in replacement
_core = CoreProtocolValidator()
_ext = ExtensionValidator()


def validate_delegate(delegate: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a DELEGATE block (core + extension fields).
    
    This is a convenience function that provides the same API as the legacy
    protocol-validation skill. For more detailed validation results with
    warnings and performance metrics, use ProtocolValidator class directly.
    
    Args:
        delegate: DELEGATE dict to validate.
    
    Returns:
        (valid, errors) where valid is True only when there are no core or
        extension errors, and errors is the combined list of error messages.
    """
    core_valid, core_errors = _core.validate_delegate_core(delegate)
    ext_valid, ext_errors = _ext.validate_extensions(delegate) if isinstance(delegate, dict) else (True, [])
    errors = list(core_errors) + list(ext_errors)
    return (len(errors) == 0, errors)


def validate_handback(handback: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a HANDBACK block (core + extension fields).
    
    This is a convenience function that provides the same API as the legacy
    protocol-validation skill. For more detailed validation results with
    warnings and performance metrics, use ProtocolValidator class directly.
    
    Args:
        handback: HANDBACK dict to validate.
    
    Returns:
        (valid, errors) where valid is True only when there are no core or
        extension errors, and errors is the combined list of error messages.
    """
    core_valid, core_errors = _core.validate_handback_core(handback)
    ext_valid, ext_errors = _ext.validate_handback_extensions(handback) if isinstance(handback, dict) else (True, [])
    errors = list(core_errors) + list(ext_errors)
    return (len(errors) == 0, errors)


if __name__ == '__main__':
    exit(main())
