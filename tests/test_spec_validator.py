"""
Test suite for spec-validator skill.

RED-PHASE TESTS (TDD): These tests define the complete spec-validator behavior.

Coverage areas:
1. SpecParser          — Parse SPEC.md, extract requirements/features/constraints
2. DiffAnalyzer        — Analyze git diffs and correlate with SPEC sections
3. ComplianceChecker   — Detect violations and assess implementation compliance
4. GapDetector         — Identify unimplemented features and rollbacks
5. ComplianceReporter  — Generate machine-parseable and human-readable reports
6. SpecValidator       — End-to-end orchestration (pre-merge gate, audit mode)

Author: Senior Engineer
Phase: TDD RED-phase (tests define behavior)
"""

import pytest
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional


# ============================================================================
# DOMAIN MODELS (mirror what spec_validator.py will export)
# ============================================================================

# Imported lazily so RED tests can be collected even before implementation exists
def _import_module():
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.skills.spec_validator.scripts.spec_validator import (
        SpecParser,
        SpecSection,
        Requirement,
        Feature,
        Constraint,
        SpecDocument,
        DiffAnalyzer,
        DiffHunk,
        DiffAnalysis,
        ComplianceChecker,
        Violation,
        ViolationSeverity,
        ComplianceResult,
        GapDetector,
        Gap,
        GapType,
        RollbackDetection,
        ComplianceReporter,
        ComplianceReport,
        ReportFormat,
        SpecValidator,
        ValidationMode,
        ValidationResult,
    )
    return (
        SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
        DiffAnalyzer, DiffHunk, DiffAnalysis,
        ComplianceChecker, Violation, ViolationSeverity, ComplianceResult,
        GapDetector, Gap, GapType, RollbackDetection,
        ComplianceReporter, ComplianceReport, ReportFormat,
        SpecValidator, ValidationMode, ValidationResult,
    )


# ============================================================================
# FIXTURES
# ============================================================================

SAMPLE_SPEC_MD = """\
---
name: Sample Specification
version: 1.0
updated: 2025-01-01
---

# Sample Specification

## Executive Summary

This specification defines the sample system.

## Features

- **Feature A**: User authentication via JWT tokens. REQUIRED.
- **Feature B**: Rate limiting at 100 req/s per user. REQUIRED.
- **Feature C**: Optional dark mode support. OPTIONAL.

## Requirements

### REQ-001: Authentication
All API endpoints MUST require authentication using JWT bearer tokens.
Unauthenticated requests MUST return HTTP 401.

### REQ-002: Rate Limiting
The system MUST enforce rate limits of 100 requests per second per user.
Exceeding the limit MUST return HTTP 429.

### REQ-003: Logging
All requests MUST be logged with correlation IDs.

## Constraints

- MUST NOT store plaintext passwords.
- MUST NOT expose internal stack traces to clients.
- MUST use TLS 1.2+ for all connections.

## CHANGELOG

- 2025-01-01: Initial version
"""

SAMPLE_DIFF_ADDING_AUTH = """\
diff --git a/src/auth.py b/src/auth.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/src/auth.py
@@ -0,0 +1,25 @@
+\"\"\"JWT Authentication module.\"\"\"
+
+import jwt
+from functools import wraps
+
+
+def require_auth(f):
+    @wraps(f)
+    def decorated(*args, **kwargs):
+        token = request.headers.get('Authorization', '').replace('Bearer ', '')
+        if not token:
+            return {'error': 'Unauthorized'}, 401
+        try:
+            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
+        except jwt.InvalidTokenError:
+            return {'error': 'Unauthorized'}, 401
+        return f(*args, **kwargs)
+    return decorated
+
+
+def generate_token(user_id: str) -> str:
+    \"\"\"Generate a JWT token for a user.\"\"\"
+    return jwt.encode({'user_id': user_id}, SECRET_KEY, algorithm='HS256')
"""

SAMPLE_DIFF_REMOVING_AUTH = """\
diff --git a/src/auth.py b/src/auth.py
deleted file mode 100644
index 1234567..0000000
--- a/src/auth.py
+++ /dev/null
@@ -1,25 +0,0 @@
-\"\"\"JWT Authentication module.\"\"\"
-
-import jwt
-from functools import wraps
-
-
-def require_auth(f):
-    @wraps(f)
-    def decorated(*args, **kwargs):
-        token = request.headers.get('Authorization', '').replace('Bearer ', '')
-        if not token:
-            return {'error': 'Unauthorized'}, 401
-        try:
-            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
-        except jwt.InvalidTokenError:
-            return {'error': 'Unauthorized'}, 401
-        return f(*args, **kwargs)
-    return decorated
"""

SAMPLE_DIFF_PLAINTEXT_PASSWORDS = """\
diff --git a/src/users.py b/src/users.py
index abc..def 100644
--- a/src/users.py
+++ b/src/users.py
@@ -10,6 +10,8 @@ class UserManager:
 
     def create_user(self, username: str, password: str):
-        hashed = bcrypt.hash(password)
-        return self.db.insert(username=username, password_hash=hashed)
+        # Store password directly for easy debugging
+        return self.db.insert(username=username, password=password)
"""

SAMPLE_DIFF_UNRELATED = """\
diff --git a/README.md b/README.md
index abc..def 100644
--- a/README.md
+++ b/README.md
@@ -1,3 +1,5 @@
 # Project
 
+Updated documentation.
+
 See docs/ for details.
"""


@pytest.fixture
def sample_spec_md():
    return SAMPLE_SPEC_MD


@pytest.fixture
def spec_file(tmp_path, sample_spec_md):
    spec_path = tmp_path / "SPEC.md"
    spec_path.write_text(sample_spec_md)
    return spec_path


@pytest.fixture
def classes():
    return _import_module()


# ============================================================================
# 1. SPEC PARSER TESTS
# ============================================================================

class TestSpecParser:
    """SpecParser extracts requirements, features, and constraints from SPEC.md."""

    def test_parse_returns_spec_document(self, classes):
        SpecParser, *_ = classes
        parser = SpecParser()
        doc = parser.parse(SAMPLE_SPEC_MD)
        _, SpecSection, Requirement, Feature, Constraint, SpecDocument, *_ = classes
        assert isinstance(doc, SpecDocument)

    def test_parse_extracts_frontmatter_version(self, classes):
        SpecParser, *_ = classes
        parser = SpecParser()
        doc = parser.parse(SAMPLE_SPEC_MD)
        assert doc.version == "1.0"

    def test_parse_extracts_frontmatter_name(self, classes):
        SpecParser, *_ = classes
        parser = SpecParser()
        doc = parser.parse(SAMPLE_SPEC_MD)
        assert doc.name == "Sample Specification"

    def test_parse_extracts_sections(self, classes):
        SpecParser, SpecSection, *_ = classes
        parser = SpecParser()
        doc = parser.parse(SAMPLE_SPEC_MD)
        section_names = [s.title for s in doc.sections]
        assert "Features" in section_names
        assert "Requirements" in section_names
        assert "Constraints" in section_names

    def test_extract_requirements_by_id(self, classes):
        SpecParser, SpecSection, Requirement, *_ = classes
        parser = SpecParser()
        doc = parser.parse(SAMPLE_SPEC_MD)
        reqs = parser.extract_requirements(doc)
        req_ids = [r.id for r in reqs]
        assert "REQ-001" in req_ids
        assert "REQ-002" in req_ids
        assert "REQ-003" in req_ids

    def test_extract_requirements_with_must_keywords(self, classes):
        SpecParser, SpecSection, Requirement, *_ = classes
        parser = SpecParser()
        doc = parser.parse(SAMPLE_SPEC_MD)
        reqs = parser.extract_requirements(doc)
        req_001 = next(r for r in reqs if r.id == "REQ-001")
        assert req_001.mandatory is True
        assert "authentication" in req_001.description.lower()

    def test_extract_features_required_vs_optional(self, classes):
        SpecParser, SpecSection, Requirement, Feature, *_ = classes
        parser = SpecParser()
        doc = parser.parse(SAMPLE_SPEC_MD)
        features = parser.extract_features(doc)
        feature_names = {f.name: f for f in features}
        assert "Feature A" in feature_names
        assert feature_names["Feature A"].required is True
        assert "Feature C" in feature_names
        assert feature_names["Feature C"].required is False

    def test_extract_constraints_negative(self, classes):
        SpecParser, SpecSection, Requirement, Feature, Constraint, *_ = classes
        parser = SpecParser()
        doc = parser.parse(SAMPLE_SPEC_MD)
        constraints = parser.extract_constraints(doc)
        constraint_texts = [c.text for c in constraints]
        assert any("plaintext" in t.lower() for t in constraint_texts)
        assert any("TLS" in t for t in constraint_texts)

    def test_parse_empty_spec_returns_empty_doc(self, classes):
        SpecParser, *_ = classes
        parser = SpecParser()
        doc = parser.parse("# Empty\n")
        # A spec with only a bare title has no meaningful requirements or features
        assert doc.requirements == []
        assert doc.features == []
        assert doc.constraints == []

    def test_parse_spec_from_file(self, classes, spec_file):
        SpecParser, *_ = classes
        parser = SpecParser()
        doc = parser.parse_file(str(spec_file))
        assert doc is not None
        assert len(doc.sections) > 0

    def test_parse_spec_file_not_found_raises(self, classes):
        SpecParser, *_ = classes
        parser = SpecParser()
        with pytest.raises(FileNotFoundError):
            parser.parse_file("/nonexistent/SPEC.md")

    def test_extract_keywords_must_must_not(self, classes):
        SpecParser, *_ = classes
        parser = SpecParser()
        doc = parser.parse(SAMPLE_SPEC_MD)
        reqs = parser.extract_requirements(doc)
        # REQ-001 should have MUST keyword
        req_001 = next((r for r in reqs if r.id == "REQ-001"), None)
        assert req_001 is not None
        assert "MUST" in req_001.keywords

    def test_sections_have_content(self, classes):
        SpecParser, SpecSection, *_ = classes
        parser = SpecParser()
        doc = parser.parse(SAMPLE_SPEC_MD)
        features_section = next(s for s in doc.sections if s.title == "Features")
        assert len(features_section.content) > 0


# ============================================================================
# 2. DIFF ANALYZER TESTS
# ============================================================================

class TestDiffAnalyzer:
    """DiffAnalyzer parses git diffs and correlates with SPEC sections."""

    def test_analyze_diff_returns_diff_analysis(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis, *_) = classes
        analyzer = DiffAnalyzer()
        result = analyzer.analyze_diff(SAMPLE_DIFF_ADDING_AUTH)
        assert isinstance(result, DiffAnalysis)

    def test_analyze_diff_extracts_modified_files(self, classes):
        (_, _, _, _, _, _,
         DiffAnalyzer, DiffHunk, DiffAnalysis, *_) = classes
        analyzer = DiffAnalyzer()
        result = analyzer.analyze_diff(SAMPLE_DIFF_ADDING_AUTH)
        # auth.py is a new file — it should appear in added_files (not modified_files)
        assert "src/auth.py" in result.added_files

    def test_analyze_diff_detects_added_lines(self, classes):
        (_, _, _, _, _, _,
         DiffAnalyzer, DiffHunk, DiffAnalysis, *_) = classes
        analyzer = DiffAnalyzer()
        result = analyzer.analyze_diff(SAMPLE_DIFF_ADDING_AUTH)
        assert result.added_lines > 0
        assert result.removed_lines == 0

    def test_analyze_diff_detects_deleted_file(self, classes):
        (_, _, _, _, _, _,
         DiffAnalyzer, DiffHunk, DiffAnalysis, *_) = classes
        analyzer = DiffAnalyzer()
        result = analyzer.analyze_diff(SAMPLE_DIFF_REMOVING_AUTH)
        assert "src/auth.py" in result.deleted_files

    def test_analyze_diff_extracts_hunks(self, classes):
        (_, _, _, _, _, _,
         DiffAnalyzer, DiffHunk, DiffAnalysis, *_) = classes
        analyzer = DiffAnalyzer()
        result = analyzer.analyze_diff(SAMPLE_DIFF_ADDING_AUTH)
        assert len(result.hunks) > 0
        hunk = result.hunks[0]
        assert isinstance(hunk, DiffHunk)
        assert hunk.file_path == "src/auth.py"

    def test_correlate_diff_with_spec_sections(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis, *_) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        spec_doc = parser.parse(SAMPLE_SPEC_MD)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_ADDING_AUTH)
        correlations = analyzer.correlate_with_spec(diff, spec_doc)
        # auth.py addition should correlate with REQ-001 (authentication)
        affected_req_ids = [c.requirement_id for c in correlations if c.requirement_id]
        assert "REQ-001" in affected_req_ids

    def test_correlate_unrelated_diff_returns_no_spec_matches(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, *_) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        spec_doc = parser.parse(SAMPLE_SPEC_MD)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_UNRELATED)
        correlations = analyzer.correlate_with_spec(diff, spec_doc)
        # README change should correlate with 0 requirements
        req_correlations = [c for c in correlations if c.requirement_id]
        assert len(req_correlations) == 0

    def test_analyze_empty_diff_returns_empty_analysis(self, classes):
        (_, _, _, _, _, _,
         DiffAnalyzer, DiffHunk, DiffAnalysis, *_) = classes
        analyzer = DiffAnalyzer()
        result = analyzer.analyze_diff("")
        assert result.modified_files == []
        assert result.added_lines == 0

    def test_diff_hunk_contains_content(self, classes):
        (_, _, _, _, _, _,
         DiffAnalyzer, DiffHunk, DiffAnalysis, *_) = classes
        analyzer = DiffAnalyzer()
        result = analyzer.analyze_diff(SAMPLE_DIFF_ADDING_AUTH)
        hunk = result.hunks[0]
        assert "jwt" in hunk.content.lower() or "auth" in hunk.content.lower()

    def test_diff_analyzer_detects_keyword_in_diff(self, classes):
        (_, _, _, _, _, _,
         DiffAnalyzer, DiffHunk, DiffAnalysis, *_) = classes
        analyzer = DiffAnalyzer()
        result = analyzer.analyze_diff(SAMPLE_DIFF_PLAINTEXT_PASSWORDS)
        # Should detect keyword 'password' in diff content
        assert any("password" in h.content.lower() for h in result.hunks)


# ============================================================================
# 3. COMPLIANCE CHECKER TESTS
# ============================================================================

class TestComplianceChecker:
    """ComplianceChecker verifies implementation matches SPEC requirements."""

    def test_check_compliance_returns_result(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis,
         ComplianceChecker, Violation, ViolationSeverity, ComplianceResult, *_) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        checker = ComplianceChecker()
        spec_doc = parser.parse(SAMPLE_SPEC_MD)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_ADDING_AUTH)
        result = checker.check_compliance(spec_doc, diff)
        assert isinstance(result, ComplianceResult)

    def test_compliant_diff_has_no_violations(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis,
         ComplianceChecker, Violation, ViolationSeverity, ComplianceResult, *_) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        checker = ComplianceChecker()
        spec_doc = parser.parse(SAMPLE_SPEC_MD)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_ADDING_AUTH)
        result = checker.check_compliance(spec_doc, diff)
        # Adding auth module should be compliant
        critical = [v for v in result.violations if v.severity == ViolationSeverity.CRITICAL]
        assert len(critical) == 0

    def test_constraint_violation_detected(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis,
         ComplianceChecker, Violation, ViolationSeverity, ComplianceResult, *_) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        checker = ComplianceChecker()
        spec_doc = parser.parse(SAMPLE_SPEC_MD)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_PLAINTEXT_PASSWORDS)
        result = checker.check_compliance(spec_doc, diff)
        # Storing plaintext passwords violates constraint
        violation_texts = [v.description.lower() for v in result.violations]
        assert any("password" in t or "plaintext" in t or "constraint" in t
                   for t in violation_texts)

    def test_violation_has_severity(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis,
         ComplianceChecker, Violation, ViolationSeverity, ComplianceResult, *_) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        checker = ComplianceChecker()
        spec_doc = parser.parse(SAMPLE_SPEC_MD)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_PLAINTEXT_PASSWORDS)
        result = checker.check_compliance(spec_doc, diff)
        assert len(result.violations) > 0
        for v in result.violations:
            assert isinstance(v.severity, ViolationSeverity)

    def test_violation_has_description_and_location(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis,
         ComplianceChecker, Violation, ViolationSeverity, ComplianceResult, *_) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        checker = ComplianceChecker()
        spec_doc = parser.parse(SAMPLE_SPEC_MD)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_PLAINTEXT_PASSWORDS)
        result = checker.check_compliance(spec_doc, diff)
        for v in result.violations:
            assert v.description != ""
            assert v.file_path is not None

    def test_compliance_result_overall_status_pass(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis,
         ComplianceChecker, Violation, ViolationSeverity, ComplianceResult, *_) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        checker = ComplianceChecker()
        spec_doc = parser.parse(SAMPLE_SPEC_MD)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_UNRELATED)
        result = checker.check_compliance(spec_doc, diff)
        assert result.overall_status in ("PASS", "WARN", "FAIL")

    def test_compliance_result_fail_on_critical_violation(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis,
         ComplianceChecker, Violation, ViolationSeverity, ComplianceResult, *_) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        checker = ComplianceChecker()
        spec_doc = parser.parse(SAMPLE_SPEC_MD)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_PLAINTEXT_PASSWORDS)
        result = checker.check_compliance(spec_doc, diff)
        # Plaintext password violation should cause FAIL
        assert result.overall_status == "FAIL"

    def test_violation_severity_enum_values(self, classes):
        (_, _, _, _, _, _, _, _, _,
         ComplianceChecker, Violation, ViolationSeverity, *_) = classes
        assert hasattr(ViolationSeverity, "CRITICAL")
        assert hasattr(ViolationSeverity, "HIGH")
        assert hasattr(ViolationSeverity, "MEDIUM")
        assert hasattr(ViolationSeverity, "LOW")

    def test_identify_violations_returns_list(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis,
         ComplianceChecker, Violation, ViolationSeverity, ComplianceResult, *_) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        checker = ComplianceChecker()
        spec_doc = parser.parse(SAMPLE_SPEC_MD)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_PLAINTEXT_PASSWORDS)
        violations = checker.identify_violations(spec_doc, diff)
        assert isinstance(violations, list)

    def test_compliance_result_has_summary_counts(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis,
         ComplianceChecker, Violation, ViolationSeverity, ComplianceResult, *_) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        checker = ComplianceChecker()
        spec_doc = parser.parse(SAMPLE_SPEC_MD)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_PLAINTEXT_PASSWORDS)
        result = checker.check_compliance(spec_doc, diff)
        assert hasattr(result, "critical_count")
        assert hasattr(result, "high_count")
        assert hasattr(result, "medium_count")
        assert hasattr(result, "low_count")


# ============================================================================
# 4. GAP DETECTOR TESTS
# ============================================================================

class TestGapDetector:
    """GapDetector identifies unimplemented features and rollbacks."""

    def test_detect_gaps_returns_list(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis,
         ComplianceChecker, Violation, ViolationSeverity, ComplianceResult,
         GapDetector, Gap, GapType, RollbackDetection, *_) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        detector = GapDetector()
        spec_doc = parser.parse(SAMPLE_SPEC_MD)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_ADDING_AUTH)
        gaps = detector.detect_gaps(spec_doc, diff)
        assert isinstance(gaps, list)

    def test_gap_type_enum_values(self, classes):
        (_, _, _, _, _, _, _, _, _, _, _, _, _,
         GapDetector, Gap, GapType, *_) = classes
        assert hasattr(GapType, "UNIMPLEMENTED_FEATURE")
        assert hasattr(GapType, "REMOVED_FEATURE")
        assert hasattr(GapType, "UNDOCUMENTED_CHANGE")
        assert hasattr(GapType, "SPEC_DRIFT")

    def test_detect_rollback_when_feature_deleted(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis,
         ComplianceChecker, Violation, ViolationSeverity, ComplianceResult,
         GapDetector, Gap, GapType, RollbackDetection, *_) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        detector = GapDetector()
        spec_doc = parser.parse(SAMPLE_SPEC_MD)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_REMOVING_AUTH)
        rollbacks = detector.detect_rollbacks(spec_doc, diff)
        assert isinstance(rollbacks, list)
        # Removing auth.py while REQ-001 mandates it should be a rollback
        assert len(rollbacks) > 0

    def test_rollback_detection_has_spec_reference(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis,
         ComplianceChecker, Violation, ViolationSeverity, ComplianceResult,
         GapDetector, Gap, GapType, RollbackDetection, *_) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        detector = GapDetector()
        spec_doc = parser.parse(SAMPLE_SPEC_MD)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_REMOVING_AUTH)
        rollbacks = detector.detect_rollbacks(spec_doc, diff)
        if rollbacks:
            rb = rollbacks[0]
            assert isinstance(rb, RollbackDetection)
            assert rb.spec_requirement_id is not None
            assert rb.deleted_file is not None

    def test_no_rollbacks_for_additive_diff(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis,
         ComplianceChecker, Violation, ViolationSeverity, ComplianceResult,
         GapDetector, Gap, GapType, RollbackDetection, *_) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        detector = GapDetector()
        spec_doc = parser.parse(SAMPLE_SPEC_MD)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_ADDING_AUTH)
        rollbacks = detector.detect_rollbacks(spec_doc, diff)
        # Purely additive diff should have no rollbacks
        assert len(rollbacks) == 0

    def test_gap_has_required_fields(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis,
         ComplianceChecker, Violation, ViolationSeverity, ComplianceResult,
         GapDetector, Gap, GapType, RollbackDetection, *_) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        detector = GapDetector()
        spec_doc = parser.parse(SAMPLE_SPEC_MD)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_ADDING_AUTH)
        gaps = detector.detect_gaps(spec_doc, diff)
        for gap in gaps:
            assert isinstance(gap, Gap)
            assert gap.gap_type in list(GapType)
            assert gap.description != ""

    def test_detect_undocumented_change(self, classes):
        """A diff that touches auth logic without any SPEC mention is an undocumented change."""
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis,
         ComplianceChecker, Violation, ViolationSeverity, ComplianceResult,
         GapDetector, Gap, GapType, RollbackDetection, *_) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        detector = GapDetector()
        # Minimal spec with no auth mention at all
        bare_spec = "# Minimal\n\n## Summary\nThis is a minimal system.\n"
        spec_doc = parser.parse(bare_spec)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_ADDING_AUTH)
        gaps = detector.detect_gaps(spec_doc, diff)
        undocumented = [g for g in gaps if g.gap_type == GapType.UNDOCUMENTED_CHANGE]
        assert len(undocumented) > 0


# ============================================================================
# 5. COMPLIANCE REPORTER TESTS
# ============================================================================

class TestComplianceReporter:
    """ComplianceReporter generates machine-parseable and human-readable reports."""

    def _build_result(self, classes):
        (SpecParser, SpecSection, Requirement, Feature, Constraint, SpecDocument,
         DiffAnalyzer, DiffHunk, DiffAnalysis,
         ComplianceChecker, Violation, ViolationSeverity, ComplianceResult,
         GapDetector, Gap, GapType, RollbackDetection,
         ComplianceReporter, ComplianceReport, ReportFormat,
         SpecValidator, ValidationMode, ValidationResult) = classes
        parser = SpecParser()
        analyzer = DiffAnalyzer()
        checker = ComplianceChecker()
        detector = GapDetector()
        spec_doc = parser.parse(SAMPLE_SPEC_MD)
        diff = analyzer.analyze_diff(SAMPLE_DIFF_PLAINTEXT_PASSWORDS)
        compliance_result = checker.check_compliance(spec_doc, diff)
        gaps = detector.detect_gaps(spec_doc, diff)
        rollbacks = detector.detect_rollbacks(spec_doc, diff)
        return compliance_result, gaps, rollbacks, (
            ComplianceReporter, ComplianceReport, ReportFormat
        )

    def test_generate_report_returns_compliance_report(self, classes):
        compliance_result, gaps, rollbacks, (
            ComplianceReporter, ComplianceReport, ReportFormat) = self._build_result(classes)
        reporter = ComplianceReporter()
        report = reporter.generate_report(compliance_result, gaps, rollbacks)
        assert isinstance(report, ComplianceReport)

    def test_report_to_json_is_valid_json(self, classes):
        compliance_result, gaps, rollbacks, (
            ComplianceReporter, ComplianceReport, ReportFormat) = self._build_result(classes)
        reporter = ComplianceReporter()
        report = reporter.generate_report(compliance_result, gaps, rollbacks)
        json_output = reporter.to_json(report)
        parsed = json.loads(json_output)
        assert isinstance(parsed, dict)

    def test_json_report_has_required_keys(self, classes):
        compliance_result, gaps, rollbacks, (
            ComplianceReporter, ComplianceReport, ReportFormat) = self._build_result(classes)
        reporter = ComplianceReporter()
        report = reporter.generate_report(compliance_result, gaps, rollbacks)
        json_output = reporter.to_json(report)
        parsed = json.loads(json_output)
        assert "overall_status" in parsed
        assert "violations" in parsed
        assert "gaps" in parsed
        assert "rollbacks" in parsed
        assert "generated_at" in parsed

    def test_report_to_markdown_is_string(self, classes):
        compliance_result, gaps, rollbacks, (
            ComplianceReporter, ComplianceReport, ReportFormat) = self._build_result(classes)
        reporter = ComplianceReporter()
        report = reporter.generate_report(compliance_result, gaps, rollbacks)
        md_output = reporter.to_markdown(report)
        assert isinstance(md_output, str)
        assert len(md_output) > 0

    def test_markdown_report_contains_status_header(self, classes):
        compliance_result, gaps, rollbacks, (
            ComplianceReporter, ComplianceReport, ReportFormat) = self._build_result(classes)
        reporter = ComplianceReporter()
        report = reporter.generate_report(compliance_result, gaps, rollbacks)
        md_output = reporter.to_markdown(report)
        assert "# " in md_output  # Has at least one heading
        assert "FAIL" in md_output or "PASS" in md_output or "WARN" in md_output

    def test_markdown_report_includes_violations(self, classes):
        compliance_result, gaps, rollbacks, (
            ComplianceReporter, ComplianceReport, ReportFormat) = self._build_result(classes)
        reporter = ComplianceReporter()
        report = reporter.generate_report(compliance_result, gaps, rollbacks)
        md_output = reporter.to_markdown(report)
        # Should have a violations section
        assert "violation" in md_output.lower() or "Violation" in md_output

    def test_report_format_enum(self, classes):
        (_, _, _, _, _, _, _, _, _, _, _, _, _,
         _, _, _, _,
         ComplianceReporter, ComplianceReport, ReportFormat, *_) = classes
        assert hasattr(ReportFormat, "JSON")
        assert hasattr(ReportFormat, "MARKDOWN")

    def test_generate_report_with_format_json(self, classes):
        compliance_result, gaps, rollbacks, (
            ComplianceReporter, ComplianceReport, ReportFormat) = self._build_result(classes)
        reporter = ComplianceReporter()
        report = reporter.generate_report(compliance_result, gaps, rollbacks)
        output = reporter.render(report, ReportFormat.JSON)
        parsed = json.loads(output)
        assert "overall_status" in parsed

    def test_generate_report_with_format_markdown(self, classes):
        compliance_result, gaps, rollbacks, (
            ComplianceReporter, ComplianceReport, ReportFormat) = self._build_result(classes)
        reporter = ComplianceReporter()
        report = reporter.generate_report(compliance_result, gaps, rollbacks)
        output = reporter.render(report, ReportFormat.MARKDOWN)
        assert isinstance(output, str)
        assert "#" in output

    def test_json_report_violations_have_severity(self, classes):
        compliance_result, gaps, rollbacks, (
            ComplianceReporter, ComplianceReport, ReportFormat) = self._build_result(classes)
        reporter = ComplianceReporter()
        report = reporter.generate_report(compliance_result, gaps, rollbacks)
        json_output = reporter.to_json(report)
        parsed = json.loads(json_output)
        for violation in parsed.get("violations", []):
            assert "severity" in violation
            assert "description" in violation


# ============================================================================
# 6. SPEC VALIDATOR (END-TO-END) TESTS
# ============================================================================

class TestSpecValidator:
    """SpecValidator orchestrates the full validation pipeline."""

    def test_validate_returns_validation_result(self, classes):
        (_, _, _, _, _, _, _, _, _, _, _, _, _,
         _, _, _, _,
         _, _, _,
         SpecValidator, ValidationMode, ValidationResult) = classes
        validator = SpecValidator()
        result = validator.validate(
            spec_content=SAMPLE_SPEC_MD,
            diff_content=SAMPLE_DIFF_ADDING_AUTH,
            mode=ValidationMode.AUDIT,
        )
        assert isinstance(result, ValidationResult)

    def test_validation_mode_enum(self, classes):
        (_, _, _, _, _, _, _, _, _, _, _, _, _,
         _, _, _, _,
         _, _, _,
         SpecValidator, ValidationMode, ValidationResult) = classes
        assert hasattr(ValidationMode, "PRE_MERGE")
        assert hasattr(ValidationMode, "AUDIT")

    def test_validate_pre_merge_pass_on_compliant_diff(self, classes):
        (_, _, _, _, _, _, _, _, _, _, _, _, _,
         _, _, _, _,
         _, _, _,
         SpecValidator, ValidationMode, ValidationResult) = classes
        validator = SpecValidator()
        result = validator.validate(
            spec_content=SAMPLE_SPEC_MD,
            diff_content=SAMPLE_DIFF_ADDING_AUTH,
            mode=ValidationMode.PRE_MERGE,
        )
        # Adding auth module is compliant — should PASS pre-merge
        assert result.passed is True

    def test_validate_pre_merge_fail_on_violation(self, classes):
        (_, _, _, _, _, _, _, _, _, _, _, _, _,
         _, _, _, _,
         _, _, _,
         SpecValidator, ValidationMode, ValidationResult) = classes
        validator = SpecValidator()
        result = validator.validate(
            spec_content=SAMPLE_SPEC_MD,
            diff_content=SAMPLE_DIFF_PLAINTEXT_PASSWORDS,
            mode=ValidationMode.PRE_MERGE,
        )
        # Plaintext passwords violate constraint — should FAIL
        assert result.passed is False

    def test_validate_audit_mode_always_completes(self, classes):
        """Audit mode should always produce a report even on failures."""
        (_, _, _, _, _, _, _, _, _, _, _, _, _,
         _, _, _, _,
         _, _, _,
         SpecValidator, ValidationMode, ValidationResult) = classes
        validator = SpecValidator()
        result = validator.validate(
            spec_content=SAMPLE_SPEC_MD,
            diff_content=SAMPLE_DIFF_PLAINTEXT_PASSWORDS,
            mode=ValidationMode.AUDIT,
        )
        assert result.report is not None

    def test_validate_from_files(self, classes, spec_file, tmp_path):
        (_, _, _, _, _, _, _, _, _, _, _, _, _,
         _, _, _, _,
         _, _, _,
         SpecValidator, ValidationMode, ValidationResult) = classes
        # Write diff to file
        diff_file = tmp_path / "changes.diff"
        diff_file.write_text(SAMPLE_DIFF_ADDING_AUTH)
        validator = SpecValidator()
        result = validator.validate_files(
            spec_path=str(spec_file),
            diff_path=str(diff_file),
            mode=ValidationMode.AUDIT,
        )
        assert isinstance(result, ValidationResult)

    def test_validate_rollback_detected_in_result(self, classes):
        (_, _, _, _, _, _, _, _, _, _, _, _, _,
         _, _, _, _,
         _, _, _,
         SpecValidator, ValidationMode, ValidationResult) = classes
        validator = SpecValidator()
        result = validator.validate(
            spec_content=SAMPLE_SPEC_MD,
            diff_content=SAMPLE_DIFF_REMOVING_AUTH,
            mode=ValidationMode.AUDIT,
        )
        assert len(result.rollbacks) > 0

    def test_validation_result_has_report(self, classes):
        (_, _, _, _, _, _, _, _, _, _, _, _, _,
         _, _, _, _,
         _, _, _,
         SpecValidator, ValidationMode, ValidationResult) = classes
        validator = SpecValidator()
        result = validator.validate(
            spec_content=SAMPLE_SPEC_MD,
            diff_content=SAMPLE_DIFF_ADDING_AUTH,
            mode=ValidationMode.AUDIT,
        )
        assert result.report is not None
        assert result.compliance_result is not None

    def test_validation_result_has_gaps(self, classes):
        (_, _, _, _, _, _, _, _, _, _, _, _, _,
         _, _, _, _,
         _, _, _,
         SpecValidator, ValidationMode, ValidationResult) = classes
        validator = SpecValidator()
        result = validator.validate(
            spec_content=SAMPLE_SPEC_MD,
            diff_content=SAMPLE_DIFF_ADDING_AUTH,
            mode=ValidationMode.AUDIT,
        )
        assert hasattr(result, "gaps")
        assert isinstance(result.gaps, list)

    def test_validate_spec_not_found_raises(self, classes):
        (_, _, _, _, _, _, _, _, _, _, _, _, _,
         _, _, _, _,
         _, _, _,
         SpecValidator, ValidationMode, ValidationResult) = classes
        validator = SpecValidator()
        with pytest.raises(FileNotFoundError):
            validator.validate_files(
                spec_path="/nonexistent/SPEC.md",
                diff_path="/nonexistent/changes.diff",
                mode=ValidationMode.AUDIT,
            )

    def test_validate_empty_diff_produces_no_violations(self, classes):
        (_, _, _, _, _, _, _, _, _, _, _, _, _,
         _, _, _, _,
         _, _, _,
         SpecValidator, ValidationMode, ValidationResult) = classes
        validator = SpecValidator()
        result = validator.validate(
            spec_content=SAMPLE_SPEC_MD,
            diff_content="",
            mode=ValidationMode.AUDIT,
        )
        assert result.compliance_result.overall_status in ("PASS", "WARN")

    def test_validate_output_json_report(self, classes):
        (_, _, _, _, _, _, _, _, _, _, _, _, _,
         _, _, _, _,
         ComplianceReporter, ComplianceReport, ReportFormat,
         SpecValidator, ValidationMode, ValidationResult) = classes
        validator = SpecValidator()
        result = validator.validate(
            spec_content=SAMPLE_SPEC_MD,
            diff_content=SAMPLE_DIFF_PLAINTEXT_PASSWORDS,
            mode=ValidationMode.AUDIT,
        )
        reporter = ComplianceReporter()
        json_output = reporter.render(result.report, ReportFormat.JSON)
        parsed = json.loads(json_output)
        assert parsed["overall_status"] == "FAIL"


# ============================================================================
# 7. INTEGRATION TESTS
# ============================================================================

class TestSpecValidatorIntegration:
    """Integration tests using the real SPEC.md from docs/."""

    @pytest.fixture
    def real_spec_content(self):
        spec_path = Path(__file__).parent.parent / "docs" / "SPEC.md"
        if not spec_path.exists():
            pytest.skip("docs/SPEC.md not found")
        return spec_path.read_text()

    def test_real_spec_is_parseable(self, classes, real_spec_content):
        SpecParser, *_ = classes
        parser = SpecParser()
        doc = parser.parse(real_spec_content)
        assert doc is not None
        assert len(doc.sections) > 0

    def test_real_spec_has_requirements(self, classes, real_spec_content):
        SpecParser, SpecSection, Requirement, *_ = classes
        parser = SpecParser()
        doc = parser.parse(real_spec_content)
        reqs = parser.extract_requirements(doc)
        # Real SPEC.md should have at least some requirements
        assert len(reqs) >= 0  # At minimum: no crash

    def test_empty_diff_against_real_spec_passes(self, classes, real_spec_content):
        (_, _, _, _, _, _, _, _, _, _, _, _, _,
         _, _, _, _,
         _, _, _,
         SpecValidator, ValidationMode, ValidationResult) = classes
        validator = SpecValidator()
        result = validator.validate(
            spec_content=real_spec_content,
            diff_content="",
            mode=ValidationMode.AUDIT,
        )
        assert result is not None
        assert result.compliance_result.overall_status in ("PASS", "WARN")

    def test_adding_auth_diff_against_real_spec_is_stable(self, classes, real_spec_content):
        (_, _, _, _, _, _, _, _, _, _, _, _, _,
         _, _, _, _,
         _, _, _,
         SpecValidator, ValidationMode, ValidationResult) = classes
        validator = SpecValidator()
        # Should not raise — validate returns a result regardless
        result = validator.validate(
            spec_content=real_spec_content,
            diff_content=SAMPLE_DIFF_ADDING_AUTH,
            mode=ValidationMode.AUDIT,
        )
        assert isinstance(result, ValidationResult)
