# -*- coding: utf-8 -*-
"""
spec_validator.py — Spec-validator skill: enforce implementation compliance with SPEC.md.

Validates that code changes comply with the framework specification. Works alongside
spec-management (which protects SPEC.md itself). This skill validates the implementation
against the specification, not the spec itself.

Components:
    SpecParser       — Parse SPEC.md, extract requirements/features/constraints
    DiffAnalyzer     — Parse git diffs and correlate with SPEC sections
    ComplianceChecker — Verify implementation matches SPEC requirements
    GapDetector      — Identify unimplemented features, rollbacks, and drift
    ComplianceReporter — Generate machine-parseable and human-readable reports
    SpecValidator    — End-to-end orchestration (pre-merge gate, audit mode)

Usage (CLI):
    python spec_validator.py --spec docs/SPEC.md --diff changes.diff --mode pre-merge
    python spec_validator.py --spec docs/SPEC.md --diff changes.diff --mode audit --format json

Author: Senior Engineer
Phase: TDD GREEN-phase (implements RED-phase test spec)
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================================
# DOMAIN MODELS — SpecParser
# ============================================================================

@dataclass
class SpecSection:
    """A top-level or nested section parsed from SPEC.md."""
    title: str
    level: int          # Heading level: 1 = #, 2 = ##, etc.
    content: str        # Raw text content of the section (excluding sub-sections)
    subsections: List["SpecSection"] = field(default_factory=list)
    start_line: int = 0


@dataclass
class Requirement:
    """An explicit requirement extracted from a SPEC.md section."""
    id: str                         # e.g. "REQ-001"
    title: str                      # Section / bullet title
    description: str                # Full requirement text
    mandatory: bool = True          # True if MUST / REQUIRED, False if SHOULD / OPTIONAL
    keywords: List[str] = field(default_factory=list)  # e.g. ["MUST", "MUST NOT"]
    section: str = ""               # Section title where this requirement lives
    line_hint: int = 0


@dataclass
class Feature:
    """A feature entry extracted from the Features section of SPEC.md."""
    name: str           # e.g. "Feature A"
    description: str    # Full description text
    required: bool = True  # True if marked REQUIRED; False if OPTIONAL


@dataclass
class Constraint:
    """A constraint extracted from the Constraints section of SPEC.md."""
    text: str           # Full constraint text
    is_prohibition: bool = False    # True if "MUST NOT"
    section: str = ""


@dataclass
class SpecDocument:
    """Parsed representation of a SPEC.md file."""
    name: str = ""
    version: str = ""
    updated: str = ""
    raw_content: str = ""
    sections: List[SpecSection] = field(default_factory=list)
    requirements: List[Requirement] = field(default_factory=list)
    features: List[Feature] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)


# ============================================================================
# DOMAIN MODELS — DiffAnalyzer
# ============================================================================

@dataclass
class DiffHunk:
    """A single diff hunk (block of changes) within a file."""
    file_path: str
    content: str          # Raw hunk content (added + removed lines + context)
    added_lines: List[str] = field(default_factory=list)
    removed_lines: List[str] = field(default_factory=list)


@dataclass
class SpecCorrelation:
    """Correlation between a diff hunk and a SPEC requirement/section."""
    hunk: DiffHunk
    requirement_id: Optional[str]   # e.g. "REQ-001", or None if no match
    section_title: Optional[str]
    keyword_matches: List[str] = field(default_factory=list)


@dataclass
class DiffAnalysis:
    """Parsed and analyzed git diff."""
    modified_files: List[str] = field(default_factory=list)
    added_files: List[str] = field(default_factory=list)
    deleted_files: List[str] = field(default_factory=list)
    hunks: List[DiffHunk] = field(default_factory=list)
    added_lines: int = 0
    removed_lines: int = 0


# ============================================================================
# DOMAIN MODELS — ComplianceChecker
# ============================================================================

class ViolationSeverity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Violation:
    """A compliance violation detected by the checker."""
    rule: str                   # Short rule identifier (e.g. "CONSTRAINT-PLAINTEXT-PW")
    description: str            # Human-readable description
    severity: ViolationSeverity
    file_path: Optional[str]    # Affected file
    evidence: str = ""          # Excerpt from diff that triggered violation
    constraint_text: str = ""   # The SPEC constraint that was violated
    requirement_id: Optional[str] = None


@dataclass
class ComplianceResult:
    """Result of a compliance check."""
    overall_status: str         # "PASS", "WARN", "FAIL"
    violations: List[Violation] = field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    def __post_init__(self):
        self._recount()

    def _recount(self):
        self.critical_count = sum(
            1 for v in self.violations if v.severity == ViolationSeverity.CRITICAL)
        self.high_count = sum(
            1 for v in self.violations if v.severity == ViolationSeverity.HIGH)
        self.medium_count = sum(
            1 for v in self.violations if v.severity == ViolationSeverity.MEDIUM)
        self.low_count = sum(
            1 for v in self.violations if v.severity == ViolationSeverity.LOW)


# ============================================================================
# DOMAIN MODELS — GapDetector
# ============================================================================

class GapType(Enum):
    UNIMPLEMENTED_FEATURE = "UNIMPLEMENTED_FEATURE"
    REMOVED_FEATURE = "REMOVED_FEATURE"
    UNDOCUMENTED_CHANGE = "UNDOCUMENTED_CHANGE"
    SPEC_DRIFT = "SPEC_DRIFT"


@dataclass
class Gap:
    """A gap between the SPEC and the implementation."""
    gap_type: GapType
    description: str
    spec_reference: Optional[str] = None   # Section or requirement ID
    file_path: Optional[str] = None
    evidence: str = ""


@dataclass
class RollbackDetection:
    """Detection of a feature rollback (file deletion violating a SPEC requirement)."""
    deleted_file: str
    spec_requirement_id: Optional[str]
    spec_section: Optional[str]
    description: str = ""
    keyword_matches: List[str] = field(default_factory=list)


# ============================================================================
# DOMAIN MODELS — ComplianceReporter
# ============================================================================

class ReportFormat(Enum):
    JSON = "json"
    MARKDOWN = "markdown"


@dataclass
class ComplianceReport:
    """Full compliance report combining checker and detector results."""
    overall_status: str
    violations: List[Violation] = field(default_factory=list)
    gaps: List[Gap] = field(default_factory=list)
    rollbacks: List[RollbackDetection] = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())
    summary: str = ""


# ============================================================================
# DOMAIN MODELS — SpecValidator
# ============================================================================

class ValidationMode(Enum):
    PRE_MERGE = "pre-merge"   # Strict: any FAIL blocks the merge
    AUDIT = "audit"           # Lenient: always produces a report, never blocks


@dataclass
class ValidationResult:
    """End-to-end validation result."""
    passed: bool
    compliance_result: ComplianceResult
    gaps: List[Gap] = field(default_factory=list)
    rollbacks: List[RollbackDetection] = field(default_factory=list)
    report: Optional[ComplianceReport] = None
    mode: str = ""


# ============================================================================
# SPEC PARSER
# ============================================================================

class SpecParser:
    """
    Parse a SPEC.md document and extract structured requirements, features,
    and constraints.

    Recognises:
    - YAML frontmatter (---  ... --- block at the top)
    - Heading-delimited sections (##, ###)
    - Requirement blocks: "### REQ-NNN: Title" patterns
    - Feature bullet lists: "- **Name**: description. REQUIRED/OPTIONAL."
    - Constraint bullet lists: "- MUST NOT / MUST / SHOULD"
    """

    # Patterns
    _FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    _HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    _REQ_ID_RE = re.compile(r"###\s+(REQ-\d+):\s*(.+)")
    _FEATURE_RE = re.compile(
        r"-\s+\*\*([^*]+)\*\*:\s*(.+?)(?:\s+(REQUIRED|OPTIONAL)\.?)?$",
        re.IGNORECASE
    )
    _CONSTRAINT_RE = re.compile(
        r"-\s+(MUST NOT|MUST|SHOULD NOT|SHOULD)\b.+", re.IGNORECASE
    )
    _MUST_KEYWORDS_RE = re.compile(r"\b(MUST NOT|MUST|SHOULD NOT|SHOULD|REQUIRED|OPTIONAL)\b")

    # ------------------------------------------------------------------ public

    def parse(self, spec_content: str) -> SpecDocument:
        """Parse a SPEC.md string into a SpecDocument."""
        doc = SpecDocument(raw_content=spec_content)

        # Extract frontmatter
        fm = self._parse_frontmatter(spec_content)
        doc.name = fm.get("name", "")
        doc.version = str(fm.get("version", ""))
        doc.updated = fm.get("updated", "")

        # Strip frontmatter for section parsing
        body = self._FRONTMATTER_RE.sub("", spec_content).strip()

        doc.sections = self._parse_sections(body)
        doc.requirements = self.extract_requirements(doc)
        doc.features = self.extract_features(doc)
        doc.constraints = self.extract_constraints(doc)

        return doc

    def parse_file(self, spec_path: str) -> SpecDocument:
        """Parse a SPEC.md from a filesystem path."""
        path = Path(spec_path)
        if not path.exists():
            raise FileNotFoundError(f"SPEC.md not found: {spec_path}")
        return self.parse(path.read_text(encoding="utf-8"))

    def extract_requirements(self, doc: SpecDocument) -> List[Requirement]:
        """Extract all REQ-NNN requirements from the parsed document."""
        requirements: List[Requirement] = []
        seen_ids: set = set()

        for section in doc.sections:
            reqs = self._extract_requirements_from_section(section)
            for req in reqs:
                if req.id not in seen_ids:
                    requirements.append(req)
                    seen_ids.add(req.id)
            # Recurse into subsections
            for sub in section.subsections:
                for req in self._extract_requirements_from_section(sub):
                    if req.id not in seen_ids:
                        requirements.append(req)
                        seen_ids.add(req.id)

        # Also scan raw content for requirements not inside a known section
        for m in self._REQ_ID_RE.finditer(doc.raw_content):
            req_id = m.group(1)
            if req_id not in seen_ids:
                # Find the text after this heading
                start = m.end()
                # Find next heading
                next_heading = re.search(r"\n#{1,6} ", doc.raw_content[start:])
                end = start + next_heading.start() if next_heading else len(doc.raw_content)
                description = doc.raw_content[start:end].strip()
                keywords = self._MUST_KEYWORDS_RE.findall(description)
                req = Requirement(
                    id=req_id,
                    title=m.group(2).strip(),
                    description=description,
                    mandatory=bool(re.search(r"\bMUST\b", description)),
                    keywords=keywords,
                    section="",
                )
                requirements.append(req)
                seen_ids.add(req_id)

        return requirements

    def extract_features(self, doc: SpecDocument) -> List[Feature]:
        """Extract feature entries from the Features section."""
        features: List[Feature] = []
        features_section = next(
            (s for s in doc.sections if s.title.lower() == "features"), None
        )
        if features_section is None:
            return features

        for line in features_section.content.splitlines():
            m = self._FEATURE_RE.match(line.strip())
            if m:
                name = m.group(1).strip()
                description = m.group(2).strip()
                qualifier = (m.group(3) or "REQUIRED").upper()
                features.append(Feature(
                    name=name,
                    description=description,
                    required=(qualifier == "REQUIRED"),
                ))

        return features

    def extract_constraints(self, doc: SpecDocument) -> List[Constraint]:
        """Extract MUST/MUST NOT constraint bullets from the Constraints section."""
        constraints: List[Constraint] = []
        constraints_section = next(
            (s for s in doc.sections if "constraint" in s.title.lower()), None
        )
        if constraints_section is None:
            return constraints

        for line in constraints_section.content.splitlines():
            stripped = line.strip()
            if stripped.startswith("-"):
                text = stripped.lstrip("- ").strip()
                if text:
                    is_prohibition = bool(
                        re.search(r"\bMUST NOT\b", text, re.IGNORECASE)
                    )
                    constraints.append(Constraint(
                        text=text,
                        is_prohibition=is_prohibition,
                        section=constraints_section.title,
                    ))

        return constraints

    # ----------------------------------------------------------------- private

    def _parse_frontmatter(self, content: str) -> Dict:
        """Extract YAML frontmatter as a dict (simple key: value parsing)."""
        m = self._FRONTMATTER_RE.match(content)
        if not m:
            return {}
        result: Dict = {}
        for line in m.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                result[k.strip()] = v.strip().strip('"')
        return result

    def _parse_sections(self, content: str) -> List[SpecSection]:
        """Parse heading-delimited sections from markdown body.

        Returns a *flat* list of all sections at every heading level so that
        callers can search by title without traversing a tree.  The
        ``subsections`` relationship is also populated for callers that need
        the hierarchy.
        """
        lines = content.splitlines()
        all_sections: List[SpecSection] = []   # flat — every section returned
        stack: List[Tuple[int, SpecSection]] = []  # (level, section) for hierarchy

        i = 0
        while i < len(lines):
            line = lines[i]
            m = re.match(r"^(#{1,6})\s+(.+)$", line)
            if m:
                level = len(m.group(1))
                title = m.group(2).strip()

                # Collect direct content lines until the next heading of any level
                content_lines = []
                j = i + 1
                while j < len(lines):
                    next_m = re.match(r"^(#{1,6})\s+", lines[j])
                    if next_m:
                        break
                    content_lines.append(lines[j])
                    j += 1

                section = SpecSection(
                    title=title,
                    level=level,
                    content="\n".join(content_lines),
                    start_line=i,
                )

                all_sections.append(section)  # always add to flat list

                # Build hierarchy for subsections relationship
                while stack and stack[-1][0] >= level:
                    stack.pop()
                if stack:
                    stack[-1][1].subsections.append(section)

                stack.append((level, section))
                i = j
            else:
                i += 1

        return all_sections

    def _extract_requirements_from_section(
        self, section: SpecSection
    ) -> List[Requirement]:
        """Extract REQ-NNN requirements from a section's content."""
        requirements = []
        # Check if this section itself is a REQ-NNN section
        m = re.match(r"^(REQ-\d+):\s*(.+)$", section.title)
        if m:
            req_id = m.group(1)
            description = section.content.strip()
            keywords = self._MUST_KEYWORDS_RE.findall(description)
            requirements.append(Requirement(
                id=req_id,
                title=m.group(2).strip(),
                description=description,
                mandatory=bool(re.search(r"\bMUST\b", description)),
                keywords=keywords,
                section=section.title,
            ))

        # Also look for inline REQ patterns in the content
        for line in section.content.splitlines():
            m2 = re.match(r".*\b(REQ-\d+)\b.*", line)
            if m2:
                pass  # only top-level IDs for now

        return requirements


# ============================================================================
# DIFF ANALYZER
# ============================================================================

class DiffAnalyzer:
    """
    Parse unified git diffs and correlate hunks with SPEC sections.

    Uses keyword matching to find which SPEC requirements are affected by
    each diff hunk (e.g., a diff touching auth.py correlates with REQ-001
    if REQ-001 describes authentication requirements).
    """

    _FILE_HEADER_RE = re.compile(
        r"^diff --git a/(.+?) b/(.+?)$", re.MULTILINE
    )
    _NEW_FILE_RE = re.compile(r"^new file mode", re.MULTILINE)
    _DEL_FILE_RE = re.compile(r"^deleted file mode", re.MULTILINE)
    _HUNK_RE = re.compile(r"^@@[^@]*@@", re.MULTILINE)

    # Keyword maps: spec domain words -> list of code keywords to search for
    _DOMAIN_KEYWORDS: Dict[str, List[str]] = {
        "authentication": ["auth", "jwt", "token", "login", "logout", "bearer",
                           "credentials", "session", "oauth"],
        "rate limiting": ["rate", "limit", "throttle", "429", "quota", "ratelimit"],
        "logging": ["log", "logging", "logger", "trace", "correlation", "audit"],
        "password": ["password", "passwd", "pwd", "bcrypt", "hash", "plaintext"],
        "tls": ["tls", "ssl", "https", "certificate", "cert"],
        "authorization": ["authorize", "rbac", "role", "permission", "access",
                          "acl", "privilege"],
        "stack trace": ["traceback", "stacktrace", "stack_trace", "exception",
                        "internal error"],
    }

    # ------------------------------------------------------------------ public

    def analyze_diff(self, diff_content: str) -> DiffAnalysis:
        """Parse a unified diff string into a DiffAnalysis."""
        if not diff_content.strip():
            return DiffAnalysis()

        analysis = DiffAnalysis()

        # Split into per-file blocks
        file_blocks = self._split_into_file_blocks(diff_content)

        for block in file_blocks:
            file_path = self._extract_file_path(block)
            if not file_path:
                continue

            is_new = bool(self._NEW_FILE_RE.search(block))
            is_del = bool(self._DEL_FILE_RE.search(block))

            if is_del:
                analysis.deleted_files.append(file_path)
            elif is_new:
                analysis.added_files.append(file_path)
            else:
                analysis.modified_files.append(file_path)

            # Parse hunks
            hunks = self._parse_hunks(block, file_path)
            analysis.hunks.extend(hunks)

            for hunk in hunks:
                analysis.added_lines += len(hunk.added_lines)
                analysis.removed_lines += len(hunk.removed_lines)

        return analysis

    def correlate_with_spec(
        self, diff: DiffAnalysis, spec_doc: SpecDocument
    ) -> List[SpecCorrelation]:
        """Correlate each diff hunk with relevant SPEC requirements."""
        correlations: List[SpecCorrelation] = []

        for hunk in diff.hunks:
            hunk_text = hunk.content.lower()
            matched_req_id: Optional[str] = None
            matched_section: Optional[str] = None
            keyword_matches: List[str] = []

            # Collect all tokens from the hunk
            hunk_tokens = set(re.findall(r"\b\w+\b", hunk_text))

            # Try to match against each requirement
            for req in spec_doc.requirements:
                req_tokens = set(re.findall(r"\b\w+\b", req.description.lower()))
                # Find meaningful overlap (excluding stop words)
                stop_words = {
                    "the", "a", "an", "is", "are", "be", "to", "of", "and",
                    "or", "in", "for", "with", "that", "this", "by", "on",
                    "at", "it", "its", "as", "all", "from", "not", "must",
                    "should", "will", "may", "can", "shall", "have", "has",
                    "via", "per", "any", "each", "using", "when", "if",
                    "than", "more", "less", "return", "returns", "request",
                    "requests", "http", "api", "endpoint",
                }
                req_meaningful = req_tokens - stop_words
                overlap = hunk_tokens & req_meaningful
                if len(overlap) >= 2:
                    matched_req_id = req.id
                    matched_section = req.section
                    keyword_matches = list(overlap)
                    break

            # Also check domain keyword mapping
            if not matched_req_id:
                for domain, code_kws in self._DOMAIN_KEYWORDS.items():
                    if any(kw in hunk_text for kw in code_kws):
                        # Find requirement whose description mentions this domain
                        for req in spec_doc.requirements:
                            if domain.lower() in req.description.lower():
                                matched_req_id = req.id
                                matched_section = req.section
                                keyword_matches = [
                                    kw for kw in code_kws if kw in hunk_text
                                ]
                                break
                    if matched_req_id:
                        break

            correlations.append(SpecCorrelation(
                hunk=hunk,
                requirement_id=matched_req_id,
                section_title=matched_section,
                keyword_matches=keyword_matches,
            ))

        return correlations

    # ----------------------------------------------------------------- private

    def _split_into_file_blocks(self, diff: str) -> List[str]:
        """Split a multi-file diff into per-file blocks."""
        blocks = []
        current: List[str] = []
        for line in diff.splitlines(keepends=True):
            if line.startswith("diff --git ") and current:
                blocks.append("".join(current))
                current = []
            current.append(line)
        if current:
            blocks.append("".join(current))
        return blocks

    def _extract_file_path(self, block: str) -> Optional[str]:
        """Extract the file path from a diff block header."""
        m = self._FILE_HEADER_RE.search(block)
        if m:
            return m.group(2)  # 'b' path (new path)
        return None

    def _parse_hunks(self, block: str, file_path: str) -> List[DiffHunk]:
        """Parse hunks from a diff file block."""
        hunks: List[DiffHunk] = []
        hunk_positions = [m.start() for m in self._HUNK_RE.finditer(block)]

        for idx, start in enumerate(hunk_positions):
            end = hunk_positions[idx + 1] if idx + 1 < len(hunk_positions) else len(block)
            hunk_text = block[start:end]

            added: List[str] = []
            removed: List[str] = []
            for line in hunk_text.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    added.append(line[1:])
                elif line.startswith("-") and not line.startswith("---"):
                    removed.append(line[1:])

            hunks.append(DiffHunk(
                file_path=file_path,
                content=hunk_text,
                added_lines=added,
                removed_lines=removed,
            ))

        # If no @@ hunks found but there is content after headers, treat as one hunk
        if not hunks and file_path:
            lines = block.splitlines()
            # Skip file headers
            content_lines = [l for l in lines if not l.startswith(
                ("diff --git", "index ", "--- ", "+++ ", "new file", "deleted file",
                 "old mode", "new mode", "similarity", "rename")
            )]
            if content_lines:
                added = [l[1:] for l in content_lines
                         if l.startswith("+") and not l.startswith("+++")]
                removed = [l[1:] for l in content_lines
                           if l.startswith("-") and not l.startswith("---")]
                hunks.append(DiffHunk(
                    file_path=file_path,
                    content="\n".join(content_lines),
                    added_lines=added,
                    removed_lines=removed,
                ))

        return hunks


# ============================================================================
# COMPLIANCE CHECKER
# ============================================================================

class ComplianceChecker:
    """
    Verify that a diff does not violate SPEC.md constraints and requirements.

    Detection strategies:
    1. Constraint matching: Diff content directly violates a "MUST NOT" constraint
    2. Requirement regression: A MUST requirement is being removed/broken
    3. Keyword-based heuristics for common violation patterns
    """

    # Hard-coded security heuristics (supplements SPEC constraints)
    _SECURITY_PATTERNS: List[Tuple[str, str, ViolationSeverity]] = [
        # (pattern_regex, violation_description, severity)
        (
            r"\bpassword\s*=\s*(?:password|plaintext|raw|clear)",
            "Possible plaintext password storage detected",
            ViolationSeverity.CRITICAL,
        ),
        (
            r"db\.insert\([^)]*password\s*=\s*password[^)]*\)",
            "Database insert with raw password field detected",
            ViolationSeverity.CRITICAL,
        ),
        (
            r"subprocess\.(run|call|Popen|check_output)",
            "subprocess usage detected — violates NO EXTERNAL SCRIPTS constraint",
            ViolationSeverity.HIGH,
        ),
        (
            r"os\.system\(",
            "os.system() usage detected — violates NO EXTERNAL SCRIPTS constraint",
            ViolationSeverity.HIGH,
        ),
        (
            r"traceback\.print_exc|traceback\.format_exc",
            "Stack trace exposure to output — may violate internal error constraint",
            ViolationSeverity.MEDIUM,
        ),
    ]

    # ------------------------------------------------------------------ public

    def check_compliance(
        self, spec_doc: SpecDocument, diff: DiffAnalysis
    ) -> ComplianceResult:
        """Check diff compliance against spec and return a ComplianceResult."""
        violations = self.identify_violations(spec_doc, diff)
        overall = self._compute_status(violations)
        result = ComplianceResult(overall_status=overall, violations=violations)
        return result

    def identify_violations(
        self, spec_doc: SpecDocument, diff: DiffAnalysis
    ) -> List[Violation]:
        """Identify all violations in a diff against the spec."""
        violations: List[Violation] = []

        all_added_content = self._collect_added_content(diff)

        # 1. Check against SPEC constraints
        violations.extend(
            self._check_constraints(spec_doc.constraints, diff, all_added_content)
        )

        # 2. Check against hard-coded security heuristics
        violations.extend(
            self._check_security_heuristics(diff, all_added_content)
        )

        # 3. Check for requirement regressions (deleting required implementations)
        violations.extend(
            self._check_requirement_regressions(spec_doc, diff)
        )

        # Deduplicate by (rule, file_path)
        seen = set()
        unique: List[Violation] = []
        for v in violations:
            key = (v.rule, v.file_path)
            if key not in seen:
                unique.append(v)
                seen.add(key)

        return unique

    # ----------------------------------------------------------------- private

    def _collect_added_content(self, diff: DiffAnalysis) -> str:
        """Collect all added lines from the diff into one searchable string."""
        lines = []
        for hunk in diff.hunks:
            lines.extend(hunk.added_lines)
        return "\n".join(lines)

    def _check_constraints(
        self,
        constraints: List[Constraint],
        diff: DiffAnalysis,
        added_content: str,
    ) -> List[Violation]:
        """Check diff against SPEC constraints."""
        violations: List[Violation] = []

        for constraint in constraints:
            if not constraint.is_prohibition:
                continue  # Only check MUST NOT constraints for now

            # Extract key nouns from constraint text
            constraint_lower = constraint.text.lower()
            if self._constraint_violated(constraint_lower, added_content):
                # Find which file caused the violation
                file_path = self._find_violating_file(
                    constraint_lower, diff
                )
                violations.append(Violation(
                    rule=f"CONSTRAINT-{self._slugify(constraint.text[:40])}",
                    description=f"Constraint violated: {constraint.text}",
                    severity=ViolationSeverity.CRITICAL,
                    file_path=file_path,
                    evidence=self._find_evidence(constraint_lower, added_content),
                    constraint_text=constraint.text,
                ))

        return violations

    def _constraint_violated(self, constraint_lower: str, added_content: str) -> bool:
        """Determine if a constraint is violated by the added content."""
        content_lower = added_content.lower()

        # "must not store plaintext passwords"
        if "plaintext" in constraint_lower and "password" in constraint_lower:
            # Look for direct password assignment without hashing
            return bool(re.search(
                r"password\s*=\s*(?:password|plaintext|raw|clear|user_password|\w*pass\w*)",
                content_lower,
            ))

        # "must not expose internal stack traces"
        if "stack trace" in constraint_lower or "traceback" in constraint_lower:
            return bool(re.search(
                r"traceback\.(print_exc|format_exc)|print.*traceback",
                content_lower,
            ))

        # Generic: check if constraint keywords appear in added content
        # Extract nouns from constraint, check presence in content
        words = re.findall(r"\b[a-z]{4,}\b", constraint_lower)
        stop_words = {"must", "not", "use", "have", "that", "with", "this",
                      "from", "into", "all", "only", "also", "will", "when",
                      "than", "more", "less", "over", "under", "store", "keep",
                      "hold", "send", "data"}
        keywords = [w for w in words if w not in stop_words]
        if len(keywords) >= 2:
            matches = sum(1 for kw in keywords if kw in content_lower)
            return matches >= 2

        return False

    # Paths excluded from active-source security heuristics. The SPEC scopes
    # the "NO EXTERNAL SCRIPTS / subprocess" prohibition to *agent code* and
    # explicitly EXEMPTS build/installation and CI/dev tooling (see docs/SPEC.md
    # §"EXEMPTIONS (Build & Installation Only)" and line 109 "in agent code").
    # Archived, deprecated, and test files are historical/quoted, not runtime.
    _HEURISTIC_EXCLUDE_SUBSTRINGS: Tuple[str, ...] = (
        "docs/archive/",
        "deprecated",
        "/tests/",
        "/test_",
        "/fixtures/",
        "/examples/",
        # Build & installation tooling (SPEC-exempt)
        "renderer/",
        "setup/",
        # CI/dev tooling that runs external dev tools (linters, pytest, git) —
        # not agent-runtime queue/span/routing operations
        "src/standardization/",
        "src/audit/",
        "src/skills/testing/",
    )
    # Only executable source files are scanned by the security heuristics.
    _HEURISTIC_SOURCE_EXTENSIONS: Tuple[str, ...] = (
        ".py", ".sh", ".bash", ".js", ".jsx", ".ts", ".tsx", ".go", ".rb",
    )

    def _is_scannable_source(self, file_path: Optional[str]) -> bool:
        """Return True if a file should be scanned by active-source heuristics."""
        if not file_path:
            return True  # Unknown path — scan to be safe
        fp = file_path.replace("\\", "/").lower()
        if fp.startswith("tests/"):
            return False
        if any(sub in fp for sub in self._HEURISTIC_EXCLUDE_SUBSTRINGS):
            return False
        return fp.endswith(self._HEURISTIC_SOURCE_EXTENSIONS)

    def _check_security_heuristics(
        self, diff: DiffAnalysis, added_content: str
    ) -> List[Violation]:
        """Check diff against hard-coded security heuristic patterns.

        Scans per-file so that exclusions (archived/deprecated/test/non-source
        paths) and accurate file attribution apply to each match.
        """
        violations: List[Violation] = []
        seen: set = set()

        for hunk in diff.hunks:
            if not self._is_scannable_source(hunk.file_path):
                continue
            hunk_content = "\n".join(hunk.added_lines)
            if not hunk_content:
                continue
            for pattern, description, severity in self._SECURITY_PATTERNS:
                if re.search(pattern, hunk_content, re.IGNORECASE):
                    key = (description, hunk.file_path)
                    if key in seen:
                        continue
                    seen.add(key)
                    violations.append(Violation(
                        rule=f"SECURITY-{self._slugify(description[:40])}",
                        description=description,
                        severity=severity,
                        file_path=hunk.file_path,
                        evidence=self._find_evidence_by_pattern(
                            pattern, hunk_content
                        ),
                    ))

        return violations

    def _check_requirement_regressions(
        self, spec_doc: SpecDocument, diff: DiffAnalysis
    ) -> List[Violation]:
        """Check if required functionality is being deleted."""
        violations: List[Violation] = []

        if not diff.deleted_files:
            return violations

        for req in spec_doc.requirements:
            if not req.mandatory:
                continue
            req_lower = req.description.lower()
            req_keywords = set(re.findall(r"\b[a-z]{4,}\b", req_lower)) - {
                "must", "require", "should", "will", "this", "that", "with",
                "from", "have", "been", "return", "all", "each",
            }
            for deleted in diff.deleted_files:
                file_kws = set(re.findall(r"\b[a-z]{3,}\b", deleted.lower()))
                if len(file_kws & req_keywords) >= 1:
                    violations.append(Violation(
                        rule=f"REGRESSION-{req.id}",
                        description=(
                            f"Deletion of '{deleted}' may regress {req.id}: "
                            f"{req.title}"
                        ),
                        severity=ViolationSeverity.HIGH,
                        file_path=deleted,
                        evidence=f"Deleted: {deleted}",
                        requirement_id=req.id,
                    ))

        return violations

    def _find_violating_file(self, constraint_lower: str, diff: DiffAnalysis) -> Optional[str]:
        """Find which file in the diff is most likely responsible for a constraint violation."""
        keywords = re.findall(r"\b[a-z]{4,}\b", constraint_lower)
        for hunk in diff.hunks:
            content = "\n".join(hunk.added_lines).lower()
            if sum(1 for kw in keywords if kw in content) >= 2:
                return hunk.file_path
        return diff.hunks[0].file_path if diff.hunks else None

    def _find_violating_file_by_pattern(self, pattern: str, diff: DiffAnalysis) -> Optional[str]:
        """Find which file triggered a security pattern match."""
        for hunk in diff.hunks:
            content = "\n".join(hunk.added_lines)
            if re.search(pattern, content, re.IGNORECASE):
                return hunk.file_path
        return None

    def _find_evidence(self, constraint_lower: str, added_content: str) -> str:
        """Find the most relevant line in added content for a constraint violation."""
        keywords = re.findall(r"\b[a-z]{4,}\b", constraint_lower)
        for line in added_content.splitlines():
            if sum(1 for kw in keywords if kw in line.lower()) >= 2:
                return line.strip()[:200]
        return ""

    def _find_evidence_by_pattern(self, pattern: str, added_content: str) -> str:
        """Find the line matching a security pattern."""
        m = re.search(pattern, added_content, re.IGNORECASE)
        if m:
            start = added_content.rfind("\n", 0, m.start()) + 1
            end = added_content.find("\n", m.end())
            end = end if end != -1 else len(added_content)
            return added_content[start:end].strip()[:200]
        return ""

    @staticmethod
    def _compute_status(violations: List[Violation]) -> str:
        """Compute overall status from violation list."""
        if any(v.severity in (ViolationSeverity.CRITICAL, ViolationSeverity.HIGH)
               for v in violations):
            return "FAIL"
        if violations:
            return "WARN"
        return "PASS"

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to an uppercase slug for use as a rule ID."""
        return re.sub(r"[^A-Z0-9]+", "-", text.upper()).strip("-")


# ============================================================================
# GAP DETECTOR
# ============================================================================

class GapDetector:
    """
    Identify gaps between the SPEC and the implementation diff.

    Gap types:
    - UNIMPLEMENTED_FEATURE: A required SPEC feature has no code evidence
    - REMOVED_FEATURE: A file implementing a spec feature was deleted
    - UNDOCUMENTED_CHANGE: Code was changed for a domain not mentioned in SPEC
    - SPEC_DRIFT: Detected inconsistency between SPEC wording and code
    """

    # Domain keyword sets for gap detection
    _DOMAIN_KEYWORDS: Dict[str, List[str]] = {
        "authentication": ["auth", "jwt", "token", "login", "bearer"],
        "rate limiting": ["rate", "limit", "throttle", "ratelimit"],
        "logging": ["logger", "logging", "log.info", "log.error"],
        "tls": ["tls", "ssl", "https"],
        "password": ["password", "bcrypt", "hash"],
    }

    # ------------------------------------------------------------------ public

    def detect_gaps(
        self, spec_doc: SpecDocument, diff: DiffAnalysis
    ) -> List[Gap]:
        """Detect all gap types from a diff against the spec."""
        gaps: List[Gap] = []
        gaps.extend(self._detect_undocumented_changes(spec_doc, diff))
        gaps.extend(self._detect_spec_drift(spec_doc, diff))
        return gaps

    def detect_rollbacks(
        self, spec_doc: SpecDocument, diff: DiffAnalysis
    ) -> List[RollbackDetection]:
        """Detect when a mandatory feature was removed without a SPEC update."""
        rollbacks: List[RollbackDetection] = []

        if not diff.deleted_files:
            return rollbacks

        for deleted_file in diff.deleted_files:
            file_lower = deleted_file.lower()
            # Tokenise the file path: split on / . _ - to get meaningful words
            file_tokens = set(
                t for t in re.split(r"[/._\-]", file_lower) if len(t) >= 3
            )

            # Check each requirement
            for req in spec_doc.requirements:
                if not req.mandatory:
                    continue
                req_lower = req.description.lower() + " " + req.title.lower()
                req_tokens = set(re.findall(r"\b[a-z]{3,}\b", req_lower))
                # Remove stop words
                stop_words = {
                    "the", "all", "for", "are", "not", "must", "with",
                    "this", "that", "via", "any", "each", "using", "when",
                    "require", "requests", "return", "returns", "http",
                }
                req_meaningful = req_tokens - stop_words

                # Direct overlap
                overlap = file_tokens & req_meaningful

                # Substring match: file token is prefix/stem of a req token
                # e.g.  "auth" (file) → "authentication" (req)
                if not overlap:
                    for ft in file_tokens:
                        for rt in req_meaningful:
                            if rt.startswith(ft) or ft.startswith(rt):
                                overlap.add(ft)
                                break
                        if overlap:
                            break

                if overlap:
                    rollbacks.append(RollbackDetection(
                        deleted_file=deleted_file,
                        spec_requirement_id=req.id,
                        spec_section=req.section,
                        description=(
                            f"Deletion of '{deleted_file}' may roll back "
                            f"{req.id} ({req.title}). "
                            f"SPEC.md was not updated."
                        ),
                        keyword_matches=list(overlap),
                    ))
                    break  # One rollback per file

        return rollbacks

    # ----------------------------------------------------------------- private

    def _detect_undocumented_changes(
        self, spec_doc: SpecDocument, diff: DiffAnalysis
    ) -> List[Gap]:
        """Detect code changes in domains not mentioned in the SPEC."""
        gaps: List[Gap] = []

        # Collect all domain keywords that the SPEC mentions
        spec_lower = spec_doc.raw_content.lower()
        spec_has: Dict[str, bool] = {
            domain: any(kw in spec_lower for kw in kws)
            for domain, kws in self._DOMAIN_KEYWORDS.items()
        }

        for hunk in diff.hunks:
            hunk_text = hunk.content.lower()
            for domain, kws in self._DOMAIN_KEYWORDS.items():
                if any(kw in hunk_text for kw in kws):
                    if not spec_has.get(domain, True):
                        # Code touches a domain not in SPEC
                        gaps.append(Gap(
                            gap_type=GapType.UNDOCUMENTED_CHANGE,
                            description=(
                                f"Code in '{hunk.file_path}' touches the "
                                f"'{domain}' domain, which is not documented in SPEC.md"
                            ),
                            spec_reference=None,
                            file_path=hunk.file_path,
                            evidence=hunk_text[:200],
                        ))
                        break  # One gap per hunk per domain

        return gaps

    def _detect_spec_drift(
        self, spec_doc: SpecDocument, diff: DiffAnalysis
    ) -> List[Gap]:
        """Detect when a code change contradicts a SPEC requirement."""
        # Placeholder for more advanced NLP-based drift detection
        return []


# ============================================================================
# COMPLIANCE REPORTER
# ============================================================================

class ComplianceReporter:
    """
    Generate compliance reports in JSON and Markdown formats.

    Designed to be both machine-parseable (JSON) and human-readable (Markdown).
    """

    # ------------------------------------------------------------------ public

    def generate_report(
        self,
        compliance_result: ComplianceResult,
        gaps: List[Gap],
        rollbacks: List[RollbackDetection],
    ) -> ComplianceReport:
        """Assemble a ComplianceReport from checker and detector results."""
        report = ComplianceReport(
            overall_status=compliance_result.overall_status,
            violations=compliance_result.violations,
            gaps=gaps,
            rollbacks=rollbacks,
        )
        report.summary = self._build_summary(compliance_result, gaps, rollbacks)
        return report

    def to_json(self, report: ComplianceReport) -> str:
        """Serialise a ComplianceReport to JSON."""
        return json.dumps(self._report_to_dict(report), indent=2, default=str)

    def to_markdown(self, report: ComplianceReport) -> str:
        """Serialise a ComplianceReport to a human-readable Markdown document."""
        lines: List[str] = []

        status_emoji = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(
            report.overall_status, "❓"
        )
        lines.append(f"# Spec-Validator Compliance Report")
        lines.append(f"")
        lines.append(f"**Status:** {status_emoji} **{report.overall_status}**  ")
        lines.append(f"**Generated:** {report.generated_at}  ")
        lines.append(f"")

        if report.summary:
            lines.append(f"## Summary")
            lines.append(f"")
            lines.append(report.summary)
            lines.append(f"")

        # Violations
        lines.append(f"## Violations ({len(report.violations)})")
        lines.append(f"")
        if report.violations:
            for v in report.violations:
                icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡",
                        "LOW": "🟢"}.get(v.severity.value, "⚪")
                lines.append(f"### {icon} [{v.severity.value}] {v.rule}")
                lines.append(f"")
                lines.append(f"**Description:** {v.description}  ")
                if v.file_path:
                    lines.append(f"**File:** `{v.file_path}`  ")
                if v.evidence:
                    lines.append(f"**Evidence:**")
                    lines.append(f"```")
                    lines.append(v.evidence)
                    lines.append(f"```")
                if v.constraint_text:
                    lines.append(f"**Spec Constraint:** {v.constraint_text}  ")
                lines.append(f"")
        else:
            lines.append(f"_No violations detected._")
            lines.append(f"")

        # Gaps
        lines.append(f"## Gaps ({len(report.gaps)})")
        lines.append(f"")
        if report.gaps:
            for g in report.gaps:
                lines.append(f"- **[{g.gap_type.value}]** {g.description}")
                if g.file_path:
                    lines.append(f"  - File: `{g.file_path}`")
            lines.append(f"")
        else:
            lines.append(f"_No gaps detected._")
            lines.append(f"")

        # Rollbacks
        lines.append(f"## Rollback Detections ({len(report.rollbacks)})")
        lines.append(f"")
        if report.rollbacks:
            for rb in report.rollbacks:
                lines.append(f"- **{rb.deleted_file}** — {rb.description}")
                if rb.spec_requirement_id:
                    lines.append(f"  - Spec Requirement: `{rb.spec_requirement_id}`")
            lines.append(f"")
        else:
            lines.append(f"_No rollbacks detected._")
            lines.append(f"")

        return "\n".join(lines)

    def render(self, report: ComplianceReport, fmt: ReportFormat) -> str:
        """Render a report in the specified format."""
        if fmt == ReportFormat.JSON:
            return self.to_json(report)
        elif fmt == ReportFormat.MARKDOWN:
            return self.to_markdown(report)
        else:
            raise ValueError(f"Unknown report format: {fmt}")

    # ----------------------------------------------------------------- private

    def _report_to_dict(self, report: ComplianceReport) -> Dict:
        """Convert report to a JSON-serialisable dict."""
        return {
            "overall_status": report.overall_status,
            "generated_at": report.generated_at,
            "summary": report.summary,
            "violations": [
                {
                    "rule": v.rule,
                    "description": v.description,
                    "severity": v.severity.value,
                    "file_path": v.file_path,
                    "evidence": v.evidence,
                    "constraint_text": v.constraint_text,
                    "requirement_id": v.requirement_id,
                }
                for v in report.violations
            ],
            "gaps": [
                {
                    "gap_type": g.gap_type.value,
                    "description": g.description,
                    "spec_reference": g.spec_reference,
                    "file_path": g.file_path,
                    "evidence": g.evidence,
                }
                for g in report.gaps
            ],
            "rollbacks": [
                {
                    "deleted_file": rb.deleted_file,
                    "spec_requirement_id": rb.spec_requirement_id,
                    "spec_section": rb.spec_section,
                    "description": rb.description,
                    "keyword_matches": rb.keyword_matches,
                }
                for rb in report.rollbacks
            ],
            "counts": {
                "violations_total": len(report.violations),
                "gaps_total": len(report.gaps),
                "rollbacks_total": len(report.rollbacks),
            },
        }

    def _build_summary(
        self,
        compliance_result: ComplianceResult,
        gaps: List[Gap],
        rollbacks: List[RollbackDetection],
    ) -> str:
        parts = [
            f"Violations: {len(compliance_result.violations)} "
            f"(CRITICAL={compliance_result.critical_count}, "
            f"HIGH={compliance_result.high_count}, "
            f"MEDIUM={compliance_result.medium_count}, "
            f"LOW={compliance_result.low_count})",
            f"Gaps: {len(gaps)}",
            f"Rollbacks: {len(rollbacks)}",
        ]
        return " | ".join(parts)


# ============================================================================
# SPEC VALIDATOR (ORCHESTRATOR)
# ============================================================================

class SpecValidator:
    """
    End-to-end spec compliance validator.

    Orchestrates SpecParser → DiffAnalyzer → ComplianceChecker → GapDetector
    → ComplianceReporter and returns a ValidationResult.

    Modes:
    - PRE_MERGE: Fail fast — any FAIL status prevents merging
    - AUDIT:     Always complete — produce report regardless of outcome
    """

    def __init__(self):
        self._parser = SpecParser()
        self._analyzer = DiffAnalyzer()
        self._checker = ComplianceChecker()
        self._detector = GapDetector()
        self._reporter = ComplianceReporter()

    # ------------------------------------------------------------------ public

    def validate(
        self,
        spec_content: str,
        diff_content: str,
        mode: ValidationMode = ValidationMode.AUDIT,
    ) -> ValidationResult:
        """
        Run the full validation pipeline.

        Args:
            spec_content: Raw SPEC.md text.
            diff_content: Unified diff text (e.g. from `git diff`).
            mode: PRE_MERGE (strict) or AUDIT (always complete).

        Returns:
            ValidationResult with compliance report, gaps, and rollbacks.
        """
        spec_doc = self._parser.parse(spec_content)
        diff = self._analyzer.analyze_diff(diff_content)
        compliance_result = self._checker.check_compliance(spec_doc, diff)
        gaps = self._detector.detect_gaps(spec_doc, diff)
        rollbacks = self._detector.detect_rollbacks(spec_doc, diff)
        report = self._reporter.generate_report(compliance_result, gaps, rollbacks)

        passed = compliance_result.overall_status in ("PASS", "WARN")
        if mode == ValidationMode.PRE_MERGE:
            passed = compliance_result.overall_status == "PASS"

        return ValidationResult(
            passed=passed,
            compliance_result=compliance_result,
            gaps=gaps,
            rollbacks=rollbacks,
            report=report,
            mode=mode.value,
        )

    def validate_files(
        self,
        spec_path: str,
        diff_path: str,
        mode: ValidationMode = ValidationMode.AUDIT,
    ) -> ValidationResult:
        """
        Validate using file paths.

        Raises FileNotFoundError if either file does not exist.
        """
        spec_p = Path(spec_path)
        diff_p = Path(diff_path)

        if not spec_p.exists():
            raise FileNotFoundError(f"SPEC file not found: {spec_path}")
        if not diff_p.exists():
            raise FileNotFoundError(f"Diff file not found: {diff_path}")

        return self.validate(
            spec_content=spec_p.read_text(encoding="utf-8"),
            diff_content=diff_p.read_text(encoding="utf-8"),
            mode=mode,
        )


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

def _cli_main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for spec-validator."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate implementation compliance with SPEC.md",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Pre-merge gate (fails with exit code 1 on violations)
  python spec_validator.py --spec docs/SPEC.md --diff changes.diff --mode pre-merge

  # Audit mode (always exits 0, produces JSON report)
  python spec_validator.py --spec docs/SPEC.md --diff changes.diff --mode audit --format json

  # Use git diff directly
  git diff HEAD~1 | python spec_validator.py --spec docs/SPEC.md --stdin --mode pre-merge
        """,
    )
    parser.add_argument("--spec", required=True, help="Path to SPEC.md")
    parser.add_argument("--diff", help="Path to diff file")
    parser.add_argument("--stdin", action="store_true", help="Read diff from stdin")
    parser.add_argument(
        "--mode",
        choices=["pre-merge", "audit"],
        default="audit",
        help="Validation mode (default: audit)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--output", help="Write report to file (default: stdout)"
    )

    args = parser.parse_args(argv)

    # Read spec
    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"Error: SPEC file not found: {args.spec}", file=sys.stderr)
        return 2

    spec_content = spec_path.read_text(encoding="utf-8")

    # Read diff
    diff_content = ""
    if args.stdin:
        diff_content = sys.stdin.read()
    elif args.diff:
        diff_p = Path(args.diff)
        if not diff_p.exists():
            print(f"Error: Diff file not found: {args.diff}", file=sys.stderr)
            return 2
        diff_content = diff_p.read_text(encoding="utf-8")

    # Run validation
    mode = ValidationMode.PRE_MERGE if args.mode == "pre-merge" else ValidationMode.AUDIT
    validator = SpecValidator()
    result = validator.validate(
        spec_content=spec_content,
        diff_content=diff_content,
        mode=mode,
    )

    # Render report
    reporter = ComplianceReporter()
    fmt = ReportFormat.JSON if args.format == "json" else ReportFormat.MARKDOWN
    rendered = reporter.render(result.report, fmt)

    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(rendered)

    # Exit code: 0 = pass, 1 = fail, 2 = error
    if mode == ValidationMode.PRE_MERGE and not result.passed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_cli_main())
