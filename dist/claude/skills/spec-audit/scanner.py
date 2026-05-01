#!/usr/bin/env python3
"""
spec-audit scanner
Validates services against canonical ERS patterns and reports compliance gaps.
Inverse of spec-extract: validates rather than discovers.
"""

import os
import sys
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# ANSI colors
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[0;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


class SpecAuditScanner:
    def __init__(self, service_path: str, output_dir: str = "audit",
                 patterns_filter: Optional[List[str]] = None,
                 fail_on_critical: bool = False,
                 output_format: str = "markdown", dry_run: bool = False):
        self.service_path = Path(service_path).absolute()
        self.output_dir = Path(output_dir)
        if not self.output_dir.is_absolute():
            self.output_dir = self.service_path / self.output_dir
        self.patterns_filter = patterns_filter
        self.fail_on_critical = fail_on_critical
        self.output_format = output_format
        self.dry_run = dry_run
        self.service_name = self.get_service_name()
        self.results = []
        self.has_critical = False

        # All patterns and their heuristics (canonical patterns from PATTERN-HEURISTICS.md)
        self.patterns = self._define_canonical_patterns()

    def get_service_name(self) -> str:
        """Extract service name from path"""
        name = self.service_path.name
        if name.startswith("ers-"):
            name = name[4:]
        return name

    def log_info(self, msg: str):
        print(f"{BLUE}[INFO]{NC} {msg}", file=sys.stderr)

    def log_warn(self, msg: str):
        print(f"{YELLOW}[WARN]{NC} {msg}", file=sys.stderr)

    def log_success(self, msg: str):
        print(f"{GREEN}[OK]{NC} {msg}", file=sys.stderr)

    def log_error(self, msg: str):
        print(f"{RED}[ERROR]{NC} {msg}", file=sys.stderr)

    def _define_canonical_patterns(self) -> Dict:
        """Define canonical patterns from PATTERN-HEURISTICS.md"""
        return {
            "P-001": {
                "name": "Makefile 3-Phase",
                "heuristics": [
                    {"id": "H1", "desc": "Makefile exists at service root", "check": lambda: self._file_exists("Makefile"), "required": True, "severity": "CRITICAL"},
                    {"id": "H2", "desc": "Targets: lint, test, build, deploy", "check": lambda: self._all_targets_exist("Makefile", ["lint", "test", "build", "deploy"]), "required": True, "severity": "MAJOR"},
                    {"id": "H3", "desc": ".PHONY declaration present", "check": lambda: self._grep_pattern(r"^\\.PHONY:", "Makefile"), "required": True, "severity": "MAJOR"},
                    {"id": "H4", "desc": "Error propagation with &&", "check": lambda: self._grep_pattern(r"&&", "Makefile"), "required": True, "severity": "MAJOR"},
                    {"id": "H5", "desc": "Environment sourcing via -include env/", "check": lambda: self._grep_pattern(r"\-include env/", "Makefile"), "required": True, "severity": "MAJOR"},
                ]
            },
            "P-002": {
                "name": "Environment Sourcing",
                "heuristics": [
                    {"id": "H1", "desc": "env/ directory exists", "check": lambda: self._dir_exists("env"), "required": True, "severity": "CRITICAL"},
                    {"id": "H2", "desc": "env/.env.dev file exists", "check": lambda: self._file_exists("env/.env.dev"), "required": True, "severity": "MAJOR"},
                    {"id": "H3", "desc": "env/.env.prod file exists", "check": lambda: self._file_exists("env/.env.prod"), "required": True, "severity": "MAJOR"},
                    {"id": "H4", "desc": "Makefile sources -include env/", "check": lambda: self._grep_pattern(r"\-include env/", "Makefile"), "required": True, "severity": "MAJOR"},
                    {"id": "H5", "desc": "No shell quotes in env files", "check": lambda: not self._grep_pattern(r'=\\"', "env/.env.dev"), "required": False, "severity": "MINOR"},
                ]
            },
            "P-003": {
                "name": "GitHub Actions",
                "heuristics": [
                    {"id": "H1", "desc": ".github/workflows/ directory exists", "check": lambda: self._dir_exists(".github/workflows"), "required": True, "severity": "CRITICAL"},
                    {"id": "H2", "desc": "branch.yaml workflow exists", "check": lambda: self._file_exists(".github/workflows/branch.yaml"), "required": True, "severity": "MAJOR"},
                    {"id": "H3", "desc": "main.yaml workflow exists", "check": lambda: self._file_exists(".github/workflows/main.yaml"), "required": True, "severity": "MAJOR"},
                    {"id": "H4", "desc": "Workflows invoke make targets", "check": lambda: self._grep_pattern(r"run: make", ".github/workflows/main.yaml"), "required": True, "severity": "MAJOR"},
                    {"id": "H5", "desc": "Deploy depends on lint and test", "check": lambda: self._grep_pattern(r"needs: \[lint, test\]", ".github/workflows/main.yaml"), "required": False, "severity": "MINOR"},
                ]
            },
            "P-004": {
                "name": "CDK Stack",
                "heuristics": [
                    {"id": "H1", "desc": "cdk/ directory exists", "check": lambda: self._dir_exists("cdk"), "required": True, "severity": "CRITICAL"},
                    {"id": "H2", "desc": "cdk/main.go or cdk/cdk.go exists", "check": lambda: self._file_exists("cdk/main.go") or self._file_exists("cdk/cdk.go"), "required": True, "severity": "CRITICAL"},
                    {"id": "H3", "desc": "ENV_NAME read from environment", "check": lambda: self._grep_pattern(r'Getenv\("ENV_NAME"\)', "cdk/main.go") or self._grep_pattern(r'Getenv\("ENV_NAME"\)', "cdk/cdk.go"), "required": True, "severity": "MAJOR"},
                    {"id": "H4", "desc": "aws-cdk-go v2 imported", "check": lambda: self._grep_pattern(r"aws-cdk-go.*v2", "go.mod"), "required": True, "severity": "MAJOR"},
                    {"id": "H5", "desc": "Stack constructor follows pattern", "check": lambda: self._grep_pattern(r"func New.*Stack", "cdk/stack.go") or self._grep_pattern(r"func New.*Stack", "cdk/main.go"), "required": False, "severity": "MINOR"},
                ]
            },
            "P-005": {
                "name": "Go Modules",
                "heuristics": [
                    {"id": "H1", "desc": "go.mod file exists", "check": lambda: self._file_exists("go.mod"), "required": True, "severity": "CRITICAL"},
                    {"id": "H2", "desc": "Module path: github.com/{your-org}/ers-*", "check": lambda: self._grep_pattern(r"^module github\.com/{your-org}/ers-", "go.mod"), "required": True, "severity": "MAJOR"},
                    {"id": "H3", "desc": "Go 1.20 or later", "check": lambda: self._grep_pattern(r"^go 1\.(2[0-9]|3[0-9])", "go.mod"), "required": True, "severity": "MAJOR"},
                    {"id": "H4", "desc": "AWS SDK v2 dependencies present", "check": lambda: self._grep_pattern(r"aws-sdk-go-v2", "go.mod"), "required": False, "severity": "MINOR"},
                    {"id": "H5", "desc": "GOPRIVATE set for {service-name}", "check": lambda: self._grep_pattern(r"GOPRIVATE.*{service-name}", "Makefile"), "required": False, "severity": "MINOR"},
                ]
            },
            "P-006": {
                "name": "Lambda Handler",
                "heuristics": [
                    {"id": "H1", "desc": "Lambda handler main.go exists", "check": lambda: self._file_exists("lambda/*/main.go") or self._file_exists("main.go"), "required": True, "severity": "CRITICAL"},
                    {"id": "H2", "desc": "aws-lambda-go imported", "check": lambda: self._grep_pattern(r"aws-lambda-go", "go.mod"), "required": True, "severity": "MAJOR"},
                    {"id": "H3", "desc": "lambda.Start() invoked", "check": lambda: self._grep_handler_start(), "required": True, "severity": "MAJOR"},
                    {"id": "H4", "desc": "Proper handler signature", "check": lambda: self._grep_pattern(r"func handle.*context\.Context", "lambda/*/main.go") or self._grep_pattern(r"func handle.*context\.Context", "main.go"), "required": False, "severity": "MINOR"},
                    {"id": "H5", "desc": "Error handling present", "check": lambda: self._grep_pattern(r"if err != nil", "lambda/*/main.go") or self._grep_pattern(r"if err != nil", "main.go"), "required": False, "severity": "MINOR"},
                ]
            },
            "P-007": {
                "name": "Table-Driven Testing",
                "heuristics": [
                    {"id": "H1", "desc": "*_test.go files exist", "check": lambda: self._test_files_exist(), "required": True, "severity": "MAJOR"},
                    {"id": "H2", "desc": "Table-driven pattern used", "check": lambda: self._grep_pattern(r"tests := \[\]struct", "**/*_test.go"), "required": True, "severity": "MAJOR"},
                    {"id": "H3", "desc": "Coverage target in Makefile", "check": lambda: self._grep_pattern(r"coverage", "Makefile"), "required": False, "severity": "MINOR"},
                    {"id": "H4", "desc": ">5 test files", "check": lambda: len(list(self.service_path.rglob("*_test.go"))) >= 5, "required": False, "severity": "MINOR"},
                ]
            },
            "P-008": {
                "name": "Security Patterns",
                "heuristics": [
                    {"id": "H1", "desc": "JWT validation or JWKS handling", "check": lambda: self._grep_pattern(r"JWT|JWKS|jwt|jwks", "lambda/*/main.go") or self._grep_pattern(r"JWT|JWKS|jwt|jwks", "main.go"), "required": False, "severity": "MAJOR"},
                    {"id": "H2", "desc": "OAuth2 or Cognito handling", "check": lambda: self._grep_pattern(r"oauth|Cognito|authorization", "lambda/*/main.go") or self._grep_pattern(r"oauth|Cognito|authorization", "main.go"), "required": False, "severity": "MAJOR"},
                    {"id": "H3", "desc": "SigV4 signing or IAM credentials", "check": lambda: self._grep_pattern(r"SigV4|aws.*sign|credentials", "lambda/*/main.go") or self._grep_pattern(r"SigV4|aws.*sign|credentials", "main.go"), "required": False, "severity": "MINOR"},
                    {"id": "H4", "desc": "CORS headers or security headers", "check": lambda: self._grep_pattern(r"Access-Control|CORS|HSTS|X-Frame", "lambda/*/main.go") or self._grep_pattern(r"Access-Control|CORS|HSTS|X-Frame", "main.go"), "required": False, "severity": "MINOR"},
                    {"id": "H5", "desc": "No hardcoded secrets in code", "check": lambda: not self._grep_pattern(r"AKIA|password.*=|secret.*=", "lambda/*/main.go"), "required": False, "severity": "MAJOR"},
                ]
            },
        }

    # ========== Validation Helpers ==========

    def _file_exists(self, *parts) -> bool:
        return (self.service_path / Path(*parts)).exists()

    def _dir_exists(self, path: str) -> bool:
        return (self.service_path / path).is_dir()

    def _grep_pattern(self, pattern: str, *file_paths) -> bool:
        """Check if pattern matches in any of the files"""
        for file_path in file_paths:
            try:
                actual_path = self.service_path / file_path
                if "*" in file_path:
                    # Handle glob patterns
                    parts = Path(file_path).parts
                    for match in self.service_path.rglob(parts[-1] if len(parts) == 1 else "/".join(parts)):
                        try:
                            content = match.read_text()
                            if re.search(pattern, content, re.MULTILINE):
                                return True
                        except:
                            pass
                else:
                    if actual_path.exists():
                        content = actual_path.read_text()
                        if re.search(pattern, content, re.MULTILINE):
                            return True
            except:
                pass
        return False

    def _all_targets_exist(self, makefile: str, targets: List[str]) -> bool:
        """Check if all Makefile targets exist"""
        try:
            path = self.service_path / makefile
            if not path.exists():
                return False
            content = path.read_text()
            for target in targets:
                if not re.search(f"^{target}:", content, re.MULTILINE):
                    return False
            return True
        except:
            return False

    def _grep_handler_start(self) -> bool:
        """Check for lambda.Start() invocation"""
        for main_file in [self.service_path / "main.go"] + list(self.service_path.rglob("lambda/*/main.go")):
            if main_file.exists():
                try:
                    if "lambda.Start(" in main_file.read_text():
                        return True
                except:
                    pass
        return False

    def _test_files_exist(self) -> bool:
        """Check if *_test.go files exist"""
        test_files = list(self.service_path.rglob("*_test.go"))
        return len(test_files) > 0

    # ========== Audit Logic ==========

    def audit(self):
        """Run audit against all patterns"""
        self.log_info(f"Starting service audit: {self.service_path}")

        for pattern_id, pattern_def in self.patterns.items():
            if self.patterns_filter and pattern_id not in self.patterns_filter:
                continue

            self.log_info(f"Auditing {pattern_id} ({pattern_def['name']})...")

            # Run all heuristic checks
            deviations = []
            heuristics_met = 0
            required_met = 0
            required_total = 0

            for heuristic in pattern_def["heuristics"]:
                try:
                    result = heuristic["check"]()
                except Exception as e:
                    result = False

                if result:
                    heuristics_met += 1
                    if heuristic["required"]:
                        required_met += 1
                else:
                    if heuristic["required"]:
                        self.has_critical = True if heuristic["severity"] == "CRITICAL" else self.has_critical
                        deviations.append({
                            "heuristic_id": heuristic["id"],
                            "description": heuristic["desc"],
                            "severity": heuristic["severity"],
                            "required": heuristic["required"]
                        })

                if heuristic["required"]:
                    required_total += 1

            # Calculate compliance
            total_heuristics = len(pattern_def["heuristics"])
            compliance_pct = (heuristics_met / total_heuristics * 100) if total_heuristics > 0 else 0

            # Determine status
            if required_met == required_total:
                status = "COMPLIANT"
            elif required_met >= required_total * 0.5:
                status = "PARTIAL"
            else:
                status = "NON_COMPLIANT"

            result = {
                "pattern_id": pattern_id,
                "pattern_name": pattern_def["name"],
                "status": status,
                "compliance_percentage": int(compliance_pct),
                "heuristics_met": heuristics_met,
                "heuristics_total": total_heuristics,
                "required_met": required_met,
                "required_total": required_total,
                "deviations": deviations,
            }
            self.results.append(result)

            status_icon = "✓" if status == "COMPLIANT" else "◐" if status == "PARTIAL" else "✗"
            self.log_success(f"{pattern_id}: {status_icon} {status} ({compliance_pct:.0f}%)")

        self.log_success("Audit complete")

    def print_report(self):
        """Print console summary"""
        print("")
        print(f"Auditing: {self.service_name}")
        print("")

        compliant_count = 0
        critical_deviations = 0

        for result in self.results:
            status_icon = "✓" if result["status"] == "COMPLIANT" else "◐" if result["status"] == "PARTIAL" else "✗"
            print(f"  {result['pattern_id']} {result['pattern_name']:<35} {status_icon} {result['status']} ({result['compliance_percentage']}%)")
            if result["status"] == "COMPLIANT":
                compliant_count += 1
            for dev in result["deviations"]:
                if dev["severity"] == "CRITICAL":
                    critical_deviations += 1

        total = len(self.results)
        print(f"\nService Compliance: {compliant_count}/{total} patterns ({compliant_count * 100 // total if total > 0 else 0}%)")

        if not self.dry_run:
            print(f"Audit Report: {self.output_dir / f'{self.service_name}-audit.md'}")

        if critical_deviations > 0:
            print(f"\n⚠ {critical_deviations} CRITICAL deviation(s) found")
        print("")

    def write_report(self):
        """Write audit report to file"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        output_file = self.output_dir / f"{self.service_name}-audit.md"

        report = f"""# Audit Report: {self.service_name}

**Generated**: {datetime.now().strftime('%Y-%m-%d')}
**Service**: {self.service_name}
**Overall Compliance**: {sum(1 for r in self.results if r['status'] == 'COMPLIANT')}/{len(self.results)} patterns

## Pattern-by-Pattern Results

"""

        for result in self.results:
            status_icon = "✓" if result["status"] == "COMPLIANT" else "◐" if result["status"] == "PARTIAL" else "✗"
            report += f"### {result['pattern_id']}: {result['pattern_name']}\n"
            report += f"- **Status**: {status_icon} {result['status']} ({result['compliance_percentage']}%)\n"
            report += f"- **Heuristics Met**: {result['heuristics_met']}/{result['heuristics_total']}\n"

            if result["deviations"]:
                report += "- **Deviations**:\n"
                for dev in result["deviations"]:
                    report += f"  - {dev['heuristic_id']}: {dev['description']} [{dev['severity']}]\n"
            report += "\n"

        report += f"\n---\n\nGenerated by `/spec-audit` Copilot Skill\n"

        output_file.write_text(report)
        self.log_success(f"Wrote: {output_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Audit service compliance against ERS patterns")
    parser.add_argument("service", nargs="?", default=".", help="Service path")
    parser.add_argument("--output-dir", default="audit", help="Audit report directory")
    parser.add_argument("--patterns", help="Comma-separated pattern IDs (e.g., P-001,P-002)")
    parser.add_argument("--fail-on-critical", action="store_true", help="Exit 1 if critical deviations")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--no-write", action="store_true", help="Dry-run (don't write files)")

    args = parser.parse_args()

    scanner = SpecAuditScanner(
        args.service,
        output_dir=args.output_dir,
        patterns_filter=args.patterns.split(",") if args.patterns else None,
        fail_on_critical=args.fail_on_critical,
        output_format="json" if args.json else "markdown",
        dry_run=args.no_write
    )

    scanner.audit()
    scanner.print_report()

    if not args.no_write:
        scanner.write_report()

    # Exit code
    exit_code = 1 if scanner.has_critical and args.fail_on_critical else 0
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
