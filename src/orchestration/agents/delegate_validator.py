"""
Pre-flight validation for DELEGATE blocks.

Implements three validation groups (A/B/C) from the Quality Engineer's design:
- Group A: Structure (hard gates)
- Group B: Content Quality (refine before sending)
- Group C: Routing Sanity (re-route if fails)

Source: orchestration/DELEGATE-HANDBACK-QUALITY-GATES.md (Section 1)
        orchestration/delegate-schema.yaml
"""

import re
from typing import Tuple, List, Dict
from pathlib import Path


class RoleRoutingError(Exception):
    """
    Raised when a DELEGATE's explicit role is invalid or conflicts with the
    routing-sanity requirements for its scope/effort.

    Used by the orchestrator's TaskRouter to *reject* role mismatches at
    routing time instead of silently honouring a mis-tagged role.
    """

    def __init__(self, message: str, failures: List[str] = None):
        super().__init__(message)
        self.failures = failures or []


class DelegateValidator:
    """Validates DELEGATE blocks against protocol requirements."""
    
    # Valid roles from AGENTS.md
    VALID_ROLES = {
        'engineer', 'senior_engineer', 'lead_engineer', 'principal_engineer',
        'security_engineer', 'quality_engineer', 'model_engineer'
    }
    
    # Default models per role
    DEFAULT_MODELS = {
         'engineer': 'claude-haiku-4.5',
         'senior_engineer': 'claude-sonnet-4.6',
         'lead_engineer': 'claude-sonnet-4.6',
         'principal_engineer': 'claude-opus-4.6',
         'security_engineer': 'claude-opus-4.8',
         'quality_engineer': 'claude-sonnet-4.6',
         'model_engineer': 'claude-sonnet-4.6'
     }
    
    # Effort bands
    EFFORT_BANDS = {
        'low': (1, 4),
        'medium': (5, 16),
        'high': (17, 48),
        'max': (49, 120),
        'epic': (121, 999)
    }
    
    # Minimum role for each effort level
    EFFORT_ROLE_REQUIREMENTS = {
        'low': 'engineer',
        'medium': 'engineer',
        'high': 'senior_engineer',
        'max': 'lead_engineer',
        'epic': 'principal_engineer'
    }
    
    # Role hierarchy for role comparisons
    ROLE_HIERARCHY = {
        'engineer': 1,
        'senior_engineer': 2,
        'lead_engineer': 3,
        'principal_engineer': 4,
        'security_engineer': 2.5,
        'quality_engineer': 2.5,
        'model_engineer': 2.5
    }
    
    # Red-flag patterns in scope/plan
    RED_FLAGS = {
        'scope': [
            'Fix the bug',
            'Implement something',
            'Make it work',
            'Do the thing',
            'Fix this'
        ],
        'plan': [
            'Implement everything',
            'Do the work',
            'Handle stuff',
            'Make it good'
        ],
        'criteria': [
            'Works well',
            'Good code',
            'Looks nice',
            'Feels right',
            'Seems fine'
        ]
    }
    
    # Secrets to detect
    SECRET_PATTERNS = [
        'password', 'secret', 'token', 'api_key', 'apikey',
        'private_key', 'private-key', 'aws_secret', 'db_password'
    ]

    # Fable-5 defensive-only gate (SPEC.md > Security Engineer: Multi-Model
    # Strategy). Fable-5 is approved only for security_engineer, only for
    # defensive analysis, at effort <= medium, and the DELEGATE must carry an
    # explicit `model_constraint: defensive-only` field.
    FABLE5_MODEL_MARKER = 'fable'
    FABLE5_ALLOWED_ROLE = 'security_engineer'
    FABLE5_ALLOWED_EFFORTS = {'low', 'medium'}
    OFFENSIVE_SCOPE_PATTERNS = [
        'exploit', 'attack automation', 'offensive', 'red team',
        'proof-of-concept attack', 'jailbreak', 'prompt injection',
    ]
    
    @staticmethod
    def validate_delegate_pre_flight(delegate: Dict) -> Tuple[bool, List[str]]:
        """
        Validate DELEGATE block against Groups A/B/C checks.
        
        Args:
            delegate: DELEGATE block dictionary
            
        Returns:
            (True, []) if all checks pass
            (False, ['A1: error', 'B3: error', ...]) if failures exist
        """
        failures = []
        validator = DelegateValidator()
        
        # GROUP A: Structure (Hard gates)
        failures.extend(validator._check_group_a(delegate))
        
        # GROUP B: Content Quality (Refine before sending)
        failures.extend(validator._check_group_b(delegate))
        
        # GROUP C: Routing Sanity (Re-route if fails)
        failures.extend(validator._check_group_c(delegate))
        
        return (len(failures) == 0, failures)

    @staticmethod
    def validate_routing_role(delegate: Dict) -> Tuple[bool, List[str]]:
        """
        Validate ONLY the role/routing-sanity aspects of a DELEGATE.

        This is the subset of the pre-flight checks that the orchestrator's
        TaskRouter must enforce at dispatch time: that an explicitly-tagged
        role is a recognised role (A3) and that it does not conflict with the
        task's scope/effort routing requirements (Group C: C1–C4).

        Unlike ``validate_delegate_pre_flight`` it deliberately skips the
        content-quality gates (Group A1/A2/A6/A7 and all of Group B) so that
        routing can enforce role correctness without requiring a fully-formed,
        content-complete DELEGATE.

        Args:
            delegate: DELEGATE block dictionary

        Returns:
            (True, []) if the role is valid and consistent with routing rules
            (False, ['A3: ...', 'C2: ...']) otherwise
        """
        validator = DelegateValidator()
        failures: List[str] = []

        # A3: role must be a recognised agent role.
        role = delegate.get('role', '')
        if role not in validator.VALID_ROLES:
            failures.append(
                f'A3: role must be one of {sorted(validator.VALID_ROLES)}, got "{role}"'
            )

        # Group C: routing sanity (role vs effort/scope).
        failures.extend(validator._check_group_c(delegate))

        return (len(failures) == 0, failures)

    def _check_group_a(self, delegate: Dict) -> List[str]:
        """Check Group A: Structure (hard gates)."""
        failures = []
        
        # A1: task_id format
        task_id = delegate.get('task_id', '')
        if not self._valid_task_id(task_id):
            failures.append('A1: task_id must be YYYY-MM-DD-kebab-case format')
        
        # A2: task_id uniqueness (check in artifacts dir)
        if task_id and not self._is_task_id_unique(task_id):
            failures.append('A2: task_id already used elsewhere in this session')
        
        # A3: Valid role
        role = delegate.get('role', '')
        if role not in self.VALID_ROLES:
            failures.append(f'A3: role must be one of {self.VALID_ROLES}, got "{role}"')
        
        # A4: Model matches role default or has justification
        model = delegate.get('model', '')
        if role in self.DEFAULT_MODELS:
            default_model = self.DEFAULT_MODELS[role]
            if model != default_model and 'model_justification' not in delegate:
                failures.append(
                    f'A4: model "{model}" differs from default "{default_model}" '
                    'but no model_justification provided'
                )
        
        # A5: Effort matches role minimum
        effort = delegate.get('effort', '')
        if role and effort:
            required_role = self.EFFORT_ROLE_REQUIREMENTS.get(effort)
            if required_role and self.ROLE_HIERARCHY.get(role, 0) < self.ROLE_HIERARCHY.get(required_role, 0):
                failures.append(
                    f'A5: effort "{effort}" requires role ≥{required_role}, got "{role}"'
                )
        
        # A6: Scope quality (≥15 words, action verb, concrete subject)
        scope = delegate.get('scope', '')
        if not self._valid_scope(scope):
            failures.append(
                'A6: scope must be ≥15 words, contain action verb, and name subject'
            )
        
        # A7: No secrets in DELEGATE text
        delegate_text = str(delegate)
        if self._contains_secrets(delegate_text):
            failures.append(
                'A7: DELEGATE contains potential secrets (password, token, api_key, etc)'
            )
        
        return failures
    
    def _check_group_b(self, delegate: Dict) -> List[str]:
        """Check Group B: Content Quality."""
        failures = []
        
        # B1: success_criteria are measurable
        success_criteria = delegate.get('success_criteria', [])
        if success_criteria:
            for i, criterion in enumerate(success_criteria):
                if not self._is_measurable(criterion):
                    failures.append(
                        f'B1: success_criteria[{i}] is not measurable: "{criterion}"'
                    )
                    break  # Report only first failure per group
        
        # B2: success_criteria count ≥ ceil(estimated_hours / 4)
        estimated_hours = delegate.get('estimated_hours', 0)
        min_criteria = (estimated_hours + 3) // 4  # ceil division
        if len(success_criteria) < min_criteria:
            failures.append(
                f'B2: need ≥{min_criteria} success_criteria for {estimated_hours} hours, '
                f'got {len(success_criteria)}'
            )
        
        # B3: Plan steps are concrete (reference files/commands)
        plan = delegate.get('plan', [])
        if plan:
            for i, step in enumerate(plan):
                if isinstance(step, dict):
                    action = step.get('action', '')
                else:
                    action = str(step)
                if not self._is_concrete_action(action):
                    failures.append(
                        f'B3: plan[{i}] is not concrete: "{action[:50]}..."'
                    )
                    break
        
        # B4: At least one plan step mentions testing
        has_testing_step = any(
            'test' in (step.get('action', '') if isinstance(step, dict) else str(step)).lower()
            for step in plan
        )
        if plan and not has_testing_step:
            failures.append('B4: plan must include at least one step covering testing')
        
        # B5: Context ≥100 words
        context = delegate.get('context', '')
        word_count = len(context.split())
        if word_count < 100:
            failures.append(
                f'B5: context must be ≥100 words, got {word_count} words'
            )
        
        # B6: Bounded scope with out-of-scope for medium+ effort
        effort = delegate.get('effort', '')
        if effort in ['medium', 'high', 'max', 'epic']:
            if 'out_of_scope' not in delegate:
                failures.append(
                    f'B6: effort "{effort}" requires explicit out_of_scope list'
                )
        
        # B7: Effort realistic for scope size
        # Simple heuristic: if scope description suggests 500+ lines, effort should be high+
        scope = delegate.get('scope', '')
        if self._estimate_scope_lines(scope) > 500:
            if effort not in ['high', 'max', 'epic']:
                failures.append(
                    'B7: scope appears large (500+ lines), effort should be high/max/epic'
                )
        
        return failures
    
    def _check_group_c(self, delegate: Dict) -> List[str]:
        """Check Group C: Routing Sanity."""
        failures = []
        
        effort = delegate.get('effort', '')
        role = delegate.get('role', '')
        scope = delegate.get('scope', '')
        
        # C1: effort=high/max → role is senior_engineer or above
        if effort in ['high', 'max', 'epic']:
            required_level = self.ROLE_HIERARCHY.get('senior_engineer', 0)
            actual_level = self.ROLE_HIERARCHY.get(role, 0)
            if actual_level < required_level:
                failures.append(
                    f'C1: effort "{effort}" requires role ≥senior_engineer, got "{role}"'
                )
        
        # C2: Security-scoped → security_engineer
        if scope:
            if any(word in scope.lower() for word in ['security ', ' security', 'secure ', ' secure', 'vulnerability', 'ssl', 'tls', 'encryption']):
                if role != 'security_engineer':
                    failures.append(
                        'C2: security-scoped task must be routed to security_engineer'
                    )
        
        # C3: Cross-service architecture → principal_engineer
        if scope:
            if any(word in scope.lower() for word in ['cross-service', 'architecture ', ' architecture', 'orchestration']):
                if role != 'principal_engineer':
                    failures.append(
                        'C3: cross-service architecture task must route to principal_engineer'
                    )
        
        # C4: Code review / validation → lead_engineer or quality_engineer
        # Be more specific: check for "code review" or "audit" but not "testing"
        if scope:
            scope_lower = scope.lower()
            is_review_task = ('code review' in scope_lower or 'audit' in scope_lower) and 'test' not in scope_lower
            if is_review_task:
                if role not in ['lead_engineer', 'quality_engineer']:
                    failures.append(
                        'C4: review/audit task must route to lead_engineer or quality_engineer'
                    )

        # C5: fable-5 defensive-only gate (SPEC.md > Security Engineer:
        # Multi-Model Strategy). Offensive-scoped work must route to
        # claude-opus-4.8 — never fable-5.
        failures.extend(self._check_fable5_gate(delegate))

        return failures

    def _check_fable5_gate(self, delegate: Dict) -> List[str]:
        """Enforce the fable-5 defensive-only constraint on a DELEGATE.

        Returns C5 failures when the DELEGATE requests a fable-5 model but:
        - the role is not security_engineer, or
        - the scope matches an offensive-work pattern, or
        - effort exceeds medium, or
        - the explicit ``model_constraint: defensive-only`` field is missing.
        """
        model = str(delegate.get('model', '')).lower()
        if self.FABLE5_MODEL_MARKER not in model:
            return []

        failures = []
        role = delegate.get('role', '')
        if role != self.FABLE5_ALLOWED_ROLE:
            failures.append(
                f'C5: model "{delegate.get("model")}" is approved only for '
                f'{self.FABLE5_ALLOWED_ROLE} (defensive-only), got role "{role}"'
            )

        scope = str(delegate.get('scope', '')).lower()
        offensive_hits = [p for p in self.OFFENSIVE_SCOPE_PATTERNS if p in scope]
        if offensive_hits:
            failures.append(
                'C5: offensive-scoped task must route to claude-opus-4.8, '
                f'never fable-5 (matched: {", ".join(sorted(offensive_hits))})'
            )

        effort = delegate.get('effort', '')
        if effort and effort not in self.FABLE5_ALLOWED_EFFORTS:
            failures.append(
                f'C5: fable-5 is approved at effort <= medium, got "{effort}"'
            )

        if delegate.get('model_constraint') != 'defensive-only':
            failures.append(
                'C5: fable-5 DELEGATE must carry explicit '
                '`model_constraint: defensive-only` field'
            )

        return failures
    
    @staticmethod
    def _valid_task_id(task_id: str) -> bool:
        """Check if task_id matches YYYY-MM-DD-kebab-case pattern."""
        pattern = r'^[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9][a-z0-9\-]*[a-z0-9]$|^[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9]$'
        return bool(re.match(pattern, task_id))
    
    @staticmethod
    def _is_task_id_unique(task_id: str) -> bool:
        """Check if task_id is unique in artifacts directory."""
        artifacts_dir = Path('/home/user/agentic-engineers/artifacts')
        if not artifacts_dir.exists():
            return True  # No artifacts dir yet, assume unique
        
        for file in artifacts_dir.rglob('*.yaml'):
            if task_id in file.name:
                return False
        return True
    
    @staticmethod
    def _valid_scope(scope: str) -> bool:
        """Validate scope: ≥15 words, has action verb, names subject."""
        if not scope:
            return False
        
        words = scope.split()
        if len(words) < 15:
            return False
        
        # Check for action verbs
        action_verbs = [
            'implement', 'create', 'fix', 'refactor', 'validate', 'test',
            'design', 'optimize', 'review', 'audit', 'integrate', 'migrate',
            'add', 'remove', 'update', 'build', 'deploy', 'configure'
        ]
        
        scope_lower = scope.lower()
        has_verb = any(verb in scope_lower for verb in action_verbs)
        return has_verb
    
    @staticmethod
    def _contains_secrets(text: str) -> bool:
        """Check if text contains secret patterns."""
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in DelegateValidator.SECRET_PATTERNS)
    
    @staticmethod
    def _is_measurable(criterion: str) -> bool:
        """Check if criterion is measurable (not aspirational)."""
        aspirational = ['good', 'nice', 'well', 'fine', 'right', 'seems']
        
        criterion_lower = criterion.lower()
        if any(word in criterion_lower for word in aspirational):
            # Check if it's just "works well" style (no numbers/thresholds)
            if not any(char.isdigit() for char in criterion):
                return False
        
        # Measurable criteria usually have percentages, counts, or specific tests
        return bool(re.search(r'test|pass|fail|%|\d+|count|coverage|error', criterion_lower))
    
    @staticmethod
    def _is_concrete_action(action: str) -> bool:
        """Check if action is concrete (references files, commands, outputs)."""
        if not action or len(action.strip()) < 10:
            return False
        
        # Concrete actions mention files, commands, or specific outputs
        concrete_patterns = [
            '.yaml', '.py', '.js', '.ts', 'file', 'directory', 'function',
            'pytest', 'npm', 'make', 'curl', 'git', 'command', 'script',
            'create', 'run', 'execute', 'implement', 'add', 'write',
            'src/', 'test/', 'tests'
        ]
        
        action_lower = action.lower()
        # Must have at least one concrete pattern
        return any(pattern in action_lower for pattern in concrete_patterns)
    
    @staticmethod
    def _estimate_scope_lines(scope: str) -> int:
        """Rough estimate of code lines from scope description."""
        # Heuristic: count certain keywords
        indicators = {
            'comprehensive': 300,
            'complex': 250,
            'multiple': 200,
            'integration': 400,
            'validation': 150,
            'refactor': 200,
            'system': 500,
            'architecture': 600
        }
        
        score = 0
        scope_lower = scope.lower()
        for word, points in indicators.items():
            if word in scope_lower:
                score += points
        
        return max(score, 0)


# Module-level function for backwards compatibility
def validate_delegate_pre_flight(delegate: Dict) -> Tuple[bool, List[str]]:
    """
    Validate DELEGATE block against protocol requirements (Groups A/B/C).
    
    See DelegateValidator.validate_delegate_pre_flight for details.
    """
    return DelegateValidator.validate_delegate_pre_flight(delegate)
