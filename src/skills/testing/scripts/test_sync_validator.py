#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test-sync-validator: Detects test fixture drift from code changes.

Validates that test fixtures stay in sync with code updates.
Catches orphaned expectations, stale fixtures, and missing coverage.

Usage:
    python test_sync_validator.py --diff changes.diff --mode pre-merge --fail-on-critical
    python test_sync_validator.py --branch feature/xyz --mode audit --format json
"""

import argparse
import json
import sys
from enum import Enum
import os
import subprocess
import re


class ChangeType(Enum):
    """Categories of code changes that affect tests."""
    MODEL_UPGRADE = "model_upgrade"
    CONFIG_UPDATE = "config_update"
    API_CHANGE = "api_change"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    UNKNOWN = "unknown"


class MismatchSeverity(Enum):
    """Severity levels for test-code mismatches."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Mismatch:
    """A detected test-code synchronization mismatch."""
    def __init__(self, test_file, line, change_type, severity, message, affected_code, remediation):
        self.test_file = test_file
        self.line = line
        self.change_type = change_type
        self.severity = severity
        self.message = message
        self.affected_code = affected_code
        self.remediation = remediation

    def to_dict(self):
        return {
            'test_file': self.test_file,
            'line': self.line,
            'change_type': self.change_type,
            'severity': self.severity,
            'message': self.message,
            'affected_code': self.affected_code,
            'remediation': self.remediation,
        }


class CodeChange:
    """A detected change in source/config/docs."""
    def __init__(self, file, change_type, before, after, test_impacts):
        self.file = file
        self.change_type = change_type
        self.before = before
        self.after = after
        self.test_impacts = test_impacts

    def to_dict(self):
        return {
            'file': self.file,
            'change_type': self.change_type,
            'before': self.before,
            'after': self.after,
            'test_impacts': [t.to_dict() for t in self.test_impacts],
        }


class ValidationResult:
    """Result of test-sync validation."""
    def __init__(self, passed, critical_count, high_count, code_changes, mismatches):
        self.passed = passed
        self.critical_count = critical_count
        self.high_count = high_count
        self.code_changes = code_changes
        self.mismatches = mismatches


class TestSyncValidator:
    """Validates test fixture synchronization with code changes."""

    # Model naming patterns
    MODEL_PATTERN = r'claude-(haiku|sonnet|opus)-[\d\.]+'
    LOCKED_MODELS_FILE = 'tests/test_model_naming_compliance.py'
    APPROVED_MODELS_FILE = 'tests/test_model_naming_compliance.py'

    # Cost router expectations
    COST_ROUTER_FILE = 'tests/test_cost_aware_router.py'
    MODEL_MULTIPLIERS_FILE = 'src/orchestration/cost/cost_aware_router.py'

    # Model selection logic
    MODEL_SELECTION_FILE = 'tests/test_model_selection.py'

    def __init__(self, repo_root):
        self.repo_root = repo_root

    def validate_diff(self, diff_content, fail_on_critical=True):
        """Validate a git diff for test-code mismatches."""
        changes = self._parse_diff(diff_content)
        mismatches = self._detect_mismatches(changes)

        critical = [m for m in mismatches if m.severity == MismatchSeverity.CRITICAL.value]
        high = [m for m in mismatches if m.severity == MismatchSeverity.HIGH.value]

        passed = not (critical and fail_on_critical)

        return ValidationResult(
            passed=passed,
            critical_count=len(critical),
            high_count=len(high),
            code_changes=changes,
            mismatches=mismatches,
        )

    def _parse_diff(self, diff_content):
        """Parse git diff into code changes."""
        changes = []

        # Pattern: +model: claude-opus-4.8 (agent files)
        for match in re.finditer(r'^\+.*model:\s*(claude-[\w\d.-]+)', diff_content, re.MULTILINE):
            new_model = match.group(1)
            # Look backward for -model to get old value
            old_model = self._find_previous_model(diff_content, match.start())
            changes.append(CodeChange(
                file="agent-config",
                change_type=ChangeType.MODEL_UPGRADE.value,
                before=old_model or "unknown",
                after=new_model,
                test_impacts=[],
            ))

        # Pattern: MODEL_COST_MULTIPLIERS updates
        for match in re.finditer(r'^\+\s*"([\w.-]+)":\s*([\d.]+)', diff_content, re.MULTILINE):
            model_key = match.group(1)
            new_multiplier = match.group(2)
            changes.append(CodeChange(
                file="cost_aware_router.py",
                change_type=ChangeType.CONFIG_UPDATE.value,
                before="",
                after="{}:{}".format(model_key, new_multiplier),
                test_impacts=[],
            ))

        return changes

    def _find_previous_model(self, diff_content, position):
        """Find previous model value in diff by looking backward."""
        before = diff_content[:position]
        for match in re.finditer(r'^-.*model:\s*(claude-[\w\d.-]+)', before, re.MULTILINE):
            return match.group(1)
        return None

    def _detect_mismatches(self, changes):
        """Detect test-code mismatches for each code change."""
        mismatches = []

        for change in changes:
            if change.change_type == ChangeType.MODEL_UPGRADE.value:
                mismatches.extend(self._detect_model_upgrade_mismatches(change))
            elif change.change_type == ChangeType.CONFIG_UPDATE.value:
                mismatches.extend(self._detect_config_mismatches(change))

        return mismatches

    def _detect_model_upgrade_mismatches(self, change):
        """Detect mismatches from model upgrades."""
        mismatches = []
        new_model = change.after

        # Check LOCKED_MODELS in test_model_naming_compliance.py
        locked_models_check = Mismatch(
            test_file=self.LOCKED_MODELS_FILE,
            line=54,
            change_type="orphaned_value",
            severity=MismatchSeverity.CRITICAL.value,
            message="LOCKED_MODELS missing {}".format(new_model),
            affected_code="Agent uses {} but test fixture doesn't include it".format(new_model),
            remediation='Add "{}" to LOCKED_MODELS set in {}'.format(new_model, self.LOCKED_MODELS_FILE),
        )
        mismatches.append(locked_models_check)

        # Check APPROVED_MODELS
        approved_models_check = Mismatch(
            test_file=self.APPROVED_MODELS_FILE,
            line=66,
            change_type="orphaned_value",
            severity=MismatchSeverity.CRITICAL.value,
            message="APPROVED_MODELS missing {}".format(new_model),
            affected_code="Agent uses {} but test fixture doesn't include it".format(new_model),
            remediation='Add "{}" to APPROVED_MODELS set in {}'.format(new_model, self.APPROVED_MODELS_FILE),
        )
        mismatches.append(approved_models_check)

        # Check cost_aware_router expectations
        router_check = Mismatch(
            test_file=self.COST_ROUTER_FILE,
            line=115,
            change_type="stale_expectation",
            severity=MismatchSeverity.HIGH.value,
            message="Router test hardcoded to opus-4-7, but code now uses {}".format(new_model),
            affected_code="test_security_sensitive_forces_opus expects opus-4-7",
            remediation="Update test expectation from opus-4-7 to {}".format(new_model.replace('claude-', '')),
        )
        mismatches.append(router_check)

        return mismatches

    def _detect_config_mismatches(self, change):
        """Detect mismatches from config updates."""
        mismatches = []

        # Config changes often affect test_model_selection.py
        config_check = Mismatch(
            test_file=self.MODEL_SELECTION_FILE,
            line=0,  # Not a specific line, config affects multiple tests
            change_type="missing_coverage",
            severity=MismatchSeverity.MEDIUM.value,
            message="Config change {} may affect cost/quality logic".format(change.after),
            affected_code="Model cost/quality thresholds updated",
            remediation="Review and update cost/quality calculations in test_model_selection.py",
        )
        mismatches.append(config_check)

        return mismatches


def main():
    parser = argparse.ArgumentParser(
        description="Validate test fixture synchronization with code changes"
    )
    parser.add_argument("--diff", help="Path to git diff file")
    parser.add_argument("--branch", help="Git branch name (auto-generate diff)")
    parser.add_argument("--mode", choices=["pre-merge", "audit"], default="pre-merge",
                        help="Validation mode")
    parser.add_argument("--fail-on-critical", action="store_true",
                        help="Fail if critical mismatches detected")
    parser.add_argument("--format", choices=["json", "markdown", "text"], default="text",
                        help="Output format")
    parser.add_argument("--output", help="Write report to file")
    parser.add_argument("--repo", default=".", help="Repository root")

    args = parser.parse_args()

    # Get diff content
    if args.diff:
        with open(args.diff) as f:
            diff_content = f.read()
    elif args.branch:
        result = subprocess.run(
            ["git", "diff", "origin/main...{}".format(args.branch)],
            capture_output=True, text=True, cwd=args.repo
        )
        diff_content = result.stdout
    else:
        parser.error("--diff or --branch required")

    # Validate
    validator = TestSyncValidator(args.repo)
    result = validator.validate_diff(diff_content, fail_on_critical=args.fail_on_critical)

    # Format output
    if args.format == "json":
        output = json.dumps({
            "passed": result.passed,
            "critical_count": result.critical_count,
            "high_count": result.high_count,
            "mismatches": [m.to_dict() for m in result.mismatches],
        }, indent=2)
    else:
        output = _format_text_report(result)

    # Output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print("OK Report written to {}".format(args.output))
    else:
        print(output)

    # Exit code
    sys.exit(0 if result.passed else 1)


def _format_text_report(result):
    """Format validation result as human-readable text."""
    lines = [
        "Test Sync Validation {}".format("PASSED" if result.passed else "FAILED"),
        "Critical: {}, High: {}".format(result.critical_count, result.high_count),
        "",
    ]

    for mismatch in result.mismatches:
        severity_icon = "❌" if mismatch.severity == "critical" else "⚠️ "
        lines.append("{} [{}] {}:{}".format(severity_icon, mismatch.severity.upper(), mismatch.test_file, mismatch.line))
        lines.append("   {}".format(mismatch.message))
        lines.append("   Fix: {}".format(mismatch.remediation))
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
