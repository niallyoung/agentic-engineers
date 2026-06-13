"""
Doc-Quality-Monitor — MONITORING-001.

Automated documentation-quality monitoring for the agentic-engineers repo.

Checks performed per markdown document:
  - Broken internal links     (relative file links + anchor fragments)
  - Missing required sections  (configurable list of heading names)
  - Staleness                  (mtime older than ``staleness_days``)
  - Placeholder leakage        (TODO / FIXME / TBD / XXX / lorem ipsum / ...)
  - Structure / readability    (presence of an H1 title, minimum word count)

Produces a structured :class:`DocQualityReport` that can be serialised to JSON
(machine-readable) and Markdown (human-readable). All thresholds are
configurable via :class:`MonitorConfig`.

Design goals:
  - Zero third-party dependencies (stdlib + optional PyYAML for --config).
  - No writes to ``~/.agentic-engineers`` or any global location; artifacts are
    written only to a caller-supplied path (defaults under the repo / cwd).
  - Deterministic, side-effect-free analysis (pure functions over file content).

CLI:
    python doc_quality_monitor.py --root docs \
        --report-json doc-quality.json --report-md doc-quality.md
Exit code is 0 when ``health_score >= fail_under``, else 1 (usable as a gate).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


# ===========================================================================
# Enums
# ===========================================================================
class Severity(str, Enum):
    """Issue severity (string-valued for trivial JSON serialisation)."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Category(str, Enum):
    """Categories of documentation-quality issues."""

    BROKEN_LINK = "BROKEN_LINK"
    MISSING_SECTION = "MISSING_SECTION"
    STALE_DOC = "STALE_DOC"
    PLACEHOLDER = "PLACEHOLDER"
    STRUCTURE = "STRUCTURE"
    PHANTOM_REFERENCE = "PHANTOM_REFERENCE"


# Penalty weight (points off the 100-point health score) per severity.
_SEVERITY_PENALTY = {
    Severity.ERROR: 5.0,
    Severity.WARNING: 2.0,
    Severity.INFO: 0.5,
}


# ===========================================================================
# Config
# ===========================================================================
DEFAULT_PLACEHOLDER_PATTERNS = [
    r"\bTODO\b",
    r"\bFIXME\b",
    r"\bTBD\b",
    r"\bXXX\b",
    r"\bWIP\b",
    r"lorem ipsum",
    r"coming soon",
    r"PLACEHOLDER",
]

# Known-dead classes/paths that should no longer appear in any documentation.
# Each entry is (pattern, human_label) where pattern is a regex.
DEFAULT_PHANTOM_PATTERNS: List[tuple] = [
    (r"\bAutomationController\b", "AutomationController (removed; use Orchestrator polling loop)"),
    (r"automation_controller\.py\b", "automation_controller.py (file deleted)"),
    (r"\bsrc/orchestration/agents/automation\b", "src/orchestration/agents/automation (removed path)"),
]


@dataclass
class MonitorConfig:
    """Configurable thresholds for the documentation-quality monitor."""

    # Staleness: a doc whose mtime is older than this many days is flagged.
    staleness_days: int = 30

    # Heading names that every doc must contain (case-insensitive). Empty
    # by default so the check is opt-in per-repo / per-run.
    required_sections: List[str] = field(default_factory=list)

    # Regex patterns considered placeholder/leakage markers.
    placeholder_patterns: List[str] = field(
        default_factory=lambda: list(DEFAULT_PLACEHOLDER_PATTERNS)
    )

    # Minimum word count for a doc before the structure check complains.
    min_word_count: int = 20

    # Toggle individual checks.
    check_broken_links: bool = True
    check_required_sections: bool = True
    check_staleness: bool = True
    check_placeholders: bool = True
    check_structure: bool = True
    check_phantom_references: bool = False  # opt-in; requires phantom_patterns

    # Phantom reference patterns: list of (regex_pattern, label) tuples.
    # Each match is reported as a PHANTOM_REFERENCE finding. Defaults to
    # DEFAULT_PHANTOM_PATTERNS when check_phantom_references is True and
    # phantom_patterns is not explicitly set.
    phantom_patterns: List[tuple] = field(
        default_factory=lambda: list(DEFAULT_PHANTOM_PATTERNS)
    )

    # Glob patterns (relative to root) to exclude from discovery.
    exclude_globs: List[str] = field(default_factory=list)

    # Markdown file extensions to discover.
    extensions: List[str] = field(default_factory=lambda: [".md", ".markdown"])

    # Health-score gate: report.passed is True when score >= fail_under.
    fail_under: float = 90.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MonitorConfig":
        """Build a config from a dict, ignoring unknown keys."""
        valid = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in (data or {}).items() if k in valid}
        return cls(**filtered)

    @classmethod
    def from_file(cls, path: Path) -> "MonitorConfig":
        """Load config from a JSON or YAML file."""
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        if path.suffix in (".yaml", ".yml"):
            import yaml  # local import — optional dependency

            data = yaml.safe_load(text) or {}
        else:
            data = json.loads(text)
        return cls.from_dict(data)


# ===========================================================================
# Issue
# ===========================================================================
@dataclass
class Issue:
    """A single documentation-quality finding."""

    file: str
    line: int
    category: Category
    severity: Severity
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
        }


# ===========================================================================
# Report
# ===========================================================================
@dataclass
class DocQualityReport:
    """Aggregated documentation-quality report."""

    timestamp: str
    root: str
    total_docs: int
    issues: List[Issue]
    health_score: float
    fail_under: float
    by_category: Dict[str, int]
    by_severity: Dict[str, int]

    @property
    def total_issues(self) -> int:
        return len(self.issues)

    @property
    def passed(self) -> bool:
        return self.health_score >= self.fail_under

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "root": self.root,
            "total_docs": self.total_docs,
            "total_issues": self.total_issues,
            "health_score": round(self.health_score, 2),
            "fail_under": self.fail_under,
            "passed": self.passed,
            "by_category": self.by_category,
            "by_severity": self.by_severity,
            "issues": [i.to_dict() for i in self.issues],
        }

    def to_text(self) -> str:
        """Render a concise human-readable Markdown report."""
        status = "PASS" if self.passed else "FAIL"
        lines = [
            "# Documentation Quality Report",
            "",
            f"- Generated: {self.timestamp}",
            f"- Root: `{self.root}`",
            f"- Documents scanned: {self.total_docs}",
            f"- Health score: {self.health_score:.1f}/100 "
            f"(threshold {self.fail_under:.1f}) -> {status}",
            f"- Total issues: {self.total_issues}",
            "",
            "## Issues by category",
            "",
        ]
        if self.by_category:
            for cat, n in sorted(self.by_category.items()):
                lines.append(f"- {cat}: {n}")
        else:
            lines.append("- none")
        lines += ["", "## Findings", ""]
        if self.issues:
            for i in self.issues:
                lines.append(
                    f"- [{i.severity.value.upper()}] {i.file}:{i.line} "
                    f"({i.category.value}) — {i.message}"
                )
        else:
            lines.append("- No issues found. ✅")
        lines.append("")
        return "\n".join(lines)

    def write(
        self,
        json_path: Optional[Path] = None,
        text_path: Optional[Path] = None,
    ) -> None:
        """Write JSON and/or Markdown report to disk, creating parent dirs."""
        if json_path is not None:
            json_path = Path(json_path)
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(
                json.dumps(self.to_dict(), indent=2), encoding="utf-8"
            )
        if text_path is not None:
            text_path = Path(text_path)
            text_path.parent.mkdir(parents=True, exist_ok=True)
            text_path.write_text(self.to_text(), encoding="utf-8")


# ===========================================================================
# Monitor
# ===========================================================================
# Markdown inline link: [text](target)  — target captured, ignores images via
# a negative lookbehind on '!'.
_LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)]+)\)")
_H1_RE = re.compile(r"^#\s+\S", re.MULTILINE)
_HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
_EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "//")


class DocQualityMonitor:
    """Scans a documentation tree and produces a :class:`DocQualityReport`."""

    def __init__(
        self,
        root: Path,
        config: Optional[MonitorConfig] = None,
        now: Optional[float] = None,
    ):
        self.root = Path(root)
        self.config = config or MonitorConfig()
        # Injectable clock for deterministic staleness tests.
        self._now = now if now is not None else time.time()
        self._placeholder_res = [
            re.compile(p, re.IGNORECASE) for p in self.config.placeholder_patterns
        ]
        # Compile phantom reference patterns: list of (compiled_re, label)
        self._phantom_res = [
            (re.compile(pat, re.IGNORECASE), label)
            for pat, label in (self.config.phantom_patterns or [])
        ]

    # ------------------------------------------------------------------ #
    # Discovery
    # ------------------------------------------------------------------ #
    def discover_docs(self) -> List[Path]:
        """Return all markdown docs under root, honouring exclude globs."""
        docs: List[Path] = []
        for ext in self.config.extensions:
            docs.extend(self.root.rglob(f"*{ext}"))
        # De-dupe + stable order.
        docs = sorted({p.resolve() for p in docs if p.is_file()})
        if self.config.exclude_globs:
            kept = []
            for p in docs:
                rel = p.relative_to(self.root.resolve()) if self._under_root(p) else p
                if any(
                    p.match(g) or Path(rel).match(g) for g in self.config.exclude_globs
                ):
                    continue
                kept.append(p)
            docs = kept
        return docs

    def _under_root(self, p: Path) -> bool:
        try:
            p.resolve().relative_to(self.root.resolve())
            return True
        except ValueError:
            return False

    def _rel(self, path: Path) -> str:
        try:
            return str(Path(path).resolve().relative_to(self.root.resolve()))
        except ValueError:
            return str(path)

    # ------------------------------------------------------------------ #
    # Individual checks
    # ------------------------------------------------------------------ #
    def check_broken_links(self, path: Path) -> List[Issue]:
        path = Path(path)
        if not self.config.check_broken_links:
            return []
        issues: List[Issue] = []
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for match in _LINK_RE.finditer(line):
                target = match.group(1).strip()
                if not target:
                    continue
                # Pure anchor — in-document reference, not a file link.
                if target.startswith("#"):
                    continue
                if target.lower().startswith(_EXTERNAL_PREFIXES):
                    continue
                # Strip anchor fragment and any query.
                file_part = target.split("#", 1)[0].split("?", 1)[0].strip()
                if not file_part:
                    continue
                resolved = (path.parent / file_part).resolve()
                if not resolved.exists():
                    issues.append(
                        Issue(
                            file=self._rel(path),
                            line=lineno,
                            category=Category.BROKEN_LINK,
                            severity=Severity.ERROR,
                            message=f"Broken internal link: {target}",
                        )
                    )
        return issues

    def check_required_sections(self, path: Path) -> List[Issue]:
        path = Path(path)
        if not self.config.check_required_sections or not self.config.required_sections:
            return []
        text = path.read_text(encoding="utf-8", errors="replace")
        headings = set()
        for line in text.splitlines():
            mh = _HEADING_RE.match(line)
            if mh:
                headings.add(mh.group(1).strip().lower())
        issues: List[Issue] = []
        for section in self.config.required_sections:
            if section.strip().lower() not in headings:
                issues.append(
                    Issue(
                        file=self._rel(path),
                        line=0,
                        category=Category.MISSING_SECTION,
                        severity=Severity.WARNING,
                        message=f"Missing required section heading: '{section}'",
                    )
                )
        return issues

    def check_staleness(self, path: Path) -> List[Issue]:
        path = Path(path)
        if not self.config.check_staleness:
            return []
        age_days = (self._now - path.stat().st_mtime) / 86400.0
        if age_days > self.config.staleness_days:
            return [
                Issue(
                    file=self._rel(path),
                    line=0,
                    category=Category.STALE_DOC,
                    severity=Severity.INFO,
                    message=(
                        f"Document is stale: last modified {age_days:.0f} days ago "
                        f"(threshold {self.config.staleness_days})"
                    ),
                )
            ]
        return []

    def check_placeholders(self, path: Path) -> List[Issue]:
        path = Path(path)
        if not self.config.check_placeholders:
            return []
        issues: List[Issue] = []
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for rx in self._placeholder_res:
                if rx.search(line):
                    issues.append(
                        Issue(
                            file=self._rel(path),
                            line=lineno,
                            category=Category.PLACEHOLDER,
                            severity=Severity.WARNING,
                            message=f"Placeholder/leakage marker: '{rx.pattern}'",
                        )
                    )
                    break  # one finding per line is enough
        return issues

    def check_structure(self, path: Path) -> List[Issue]:
        path = Path(path)
        if not self.config.check_structure:
            return []
        issues: List[Issue] = []
        text = path.read_text(encoding="utf-8", errors="replace")
        if not _H1_RE.search(text):
            issues.append(
                Issue(
                    file=self._rel(path),
                    line=1,
                    category=Category.STRUCTURE,
                    severity=Severity.WARNING,
                    message="Missing top-level H1 title (e.g. '# Title')",
                )
            )
        word_count = len(text.split())
        if word_count < self.config.min_word_count:
            issues.append(
                Issue(
                    file=self._rel(path),
                    line=1,
                    category=Category.STRUCTURE,
                    severity=Severity.INFO,
                    message=(
                        f"Document is very short: {word_count} words "
                        f"(minimum {self.config.min_word_count})"
                    ),
                )
            )
        return issues

    def check_phantom_references(self, path: Path) -> List[Issue]:
        """Detect references to known-dead classes, files, or modules.

        A 'phantom reference' is any mention of a symbol that no longer exists
        in the codebase but whose name still appears in documentation, creating
        misleading guidance or broken import examples. Patterns are defined in
        ``MonitorConfig.phantom_patterns`` and compiled to regexes.

        The check is opt-in (``check_phantom_references=False`` by default).
        """
        path = Path(path)
        if not self.config.check_phantom_references or not self._phantom_res:
            return []
        issues: List[Issue] = []
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for rx, label in self._phantom_res:
                if rx.search(line):
                    issues.append(
                        Issue(
                            file=self._rel(path),
                            line=lineno,
                            category=Category.PHANTOM_REFERENCE,
                            severity=Severity.WARNING,
                            message=f"Phantom reference to removed symbol: {label}",
                        )
                    )
                    break  # one finding per line per file is enough
        return issues

    def analyze_file(self, path: Path) -> List[Issue]:
        """Run all enabled checks against a single file."""
        path = Path(path)
        issues: List[Issue] = []
        issues += self.check_broken_links(path)
        issues += self.check_required_sections(path)
        issues += self.check_staleness(path)
        issues += self.check_placeholders(path)
        issues += self.check_structure(path)
        issues += self.check_phantom_references(path)
        return issues

    # ------------------------------------------------------------------ #
    # Orchestration
    # ------------------------------------------------------------------ #
    def run(self) -> DocQualityReport:
        docs = self.discover_docs()
        all_issues: List[Issue] = []
        for doc in docs:
            all_issues.extend(self.analyze_file(doc))

        by_category: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        penalty = 0.0
        for iss in all_issues:
            by_category[iss.category.value] = by_category.get(iss.category.value, 0) + 1
            by_severity[iss.severity.value] = by_severity.get(iss.severity.value, 0) + 1
            penalty += _SEVERITY_PENALTY.get(iss.severity, 1.0)

        health = max(0.0, 100.0 - penalty)

        return DocQualityReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            root=str(self.root),
            total_docs=len(docs),
            issues=all_issues,
            health_score=health,
            fail_under=self.config.fail_under,
            by_category=by_category,
            by_severity=by_severity,
        )


# ===========================================================================
# CLI
# ===========================================================================
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Automated documentation-quality monitor (MONITORING-001)."
    )
    parser.add_argument("--root", default="docs", help="Root directory to scan")
    parser.add_argument("--config", help="Path to JSON/YAML config file")
    parser.add_argument("--report-json", help="Write machine-readable JSON report here")
    parser.add_argument("--report-md", help="Write human-readable Markdown report here")
    parser.add_argument(
        "--staleness-days", type=int, help="Override staleness threshold (days)"
    )
    parser.add_argument(
        "--required-section",
        action="append",
        dest="required_sections",
        help="Required section heading (repeatable)",
    )
    parser.add_argument(
        "--fail-under",
        type=float,
        help="Minimum health score to pass (exit 0)",
    )
    parser.add_argument(
        "--check-phantom-references",
        action="store_true",
        dest="check_phantom_references",
        help="Enable phantom-reference scan (known-dead classes/paths)",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress stdout summary")
    args = parser.parse_args(argv)

    if args.config:
        config = MonitorConfig.from_file(Path(args.config))
    else:
        config = MonitorConfig()
    if args.staleness_days is not None:
        config.staleness_days = args.staleness_days
    if args.required_sections:
        config.required_sections = args.required_sections
    if args.fail_under is not None:
        config.fail_under = args.fail_under
    if args.check_phantom_references:
        config.check_phantom_references = True

    root = Path(args.root)
    if not root.exists():
        print(f"❌ Root path does not exist: {root}", file=sys.stderr)
        return 2

    monitor = DocQualityMonitor(root=root, config=config)
    report = monitor.run()

    if args.report_json or args.report_md:
        report.write(
            json_path=Path(args.report_json) if args.report_json else None,
            text_path=Path(args.report_md) if args.report_md else None,
        )

    if not args.quiet:
        status = "✅ PASS" if report.passed else "❌ FAIL"
        print(
            f"{status}  health={report.health_score:.1f}/100  "
            f"docs={report.total_docs}  issues={report.total_issues}"
        )
        for cat, n in sorted(report.by_category.items()):
            print(f"  - {cat}: {n}")

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
