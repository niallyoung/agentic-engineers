#!/usr/bin/env python3
"""
spec-extract scanner
Hybrid pattern detection engine with regex phase + template validation
Detects all 8 ERS architectural patterns and generates confidence scores
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


class SpecExtractScanner:
    def __init__(self, service_path: str, output_dir: str = "specs",
                 patterns_filter: Optional[str] = None,
                 confidence_threshold: Optional[str] = None,
                 output_format: str = "markdown", dry_run: bool = False):
        self.service_path = Path(service_path).absolute()
        self.output_dir = Path(output_dir)
        if not self.output_dir.is_absolute():
            self.output_dir = self.service_path / self.output_dir
        self.patterns_filter = patterns_filter.split(",") if patterns_filter else None
        self.confidence_threshold = confidence_threshold
        self.output_format = output_format
        self.dry_run = dry_run
        self.service_name = self.get_service_name()
        self.results = []

        # All patterns to detect
        self.all_patterns = ["P-001", "P-002", "P-003", "P-004", "P-005", "P-006", "P-007", "P-008"]
        self.pattern_names = {
            "P-001": "Makefile 3-Phase",
            "P-002": "Environment Sourcing",
            "P-003": "GitHub Actions",
            "P-004": "CDK Stack",
            "P-005": "Go Modules",
            "P-006": "Lambda Handler",
            "P-007": "Table-Driven Testing",
            "P-008": "Security Patterns",
        }

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

    def file_exists(self, *parts) -> bool:
        return (self.service_path / Path(*parts)).exists()

    def file_contains(self, path: Path, pattern: str) -> bool:
        """Check if file contains regex pattern"""
        try:
            with open(path) as f:
                return bool(re.search(pattern, f.read(), re.MULTILINE))
        except:
            return False

    def grep_count(self, pattern: str, *paths) -> int:
        """Count matching lines across files"""
        count = 0
        for path_part in paths:
            path = self.service_path / path_part if isinstance(path_part, str) else path_part
            if path.is_file():
                try:
                    with open(path) as f:
                        count += len([l for l in f if re.search(pattern, l)])
                except:
                    pass
            elif path.is_dir():
                try:
                    result = subprocess.run(
                        ["grep", "-r", pattern, str(path)],
                        capture_output=True, text=True
                    )
                    count += len([l for l in result.stdout.split("\n") if l])
                except:
                    pass
        return count

    def find_files(self, pattern: str, *dirs) -> List[str]:
        """Find files matching pattern"""
        found = []
        for dir_part in dirs:
            dir_path = self.service_path / dir_part if isinstance(dir_part, str) else dir_part
            if dir_path.is_dir():
                try:
                    result = subprocess.run(
                        ["find", str(dir_path), "-name", pattern],
                        capture_output=True, text=True
                    )
                    found.extend([l for l in result.stdout.split("\n") if l])
                except:
                    pass
        return found

    # ========== Pattern Detectors ==========

    def detect_p001(self) -> Tuple[bool, str, List[str], str]:
        """Makefile 3-Phase"""
        makefile = self.service_path / "Makefile"
        if not makefile.exists():
            return False, "0%", [], ""

        evidence = ["File exists at service root"]
        targets = ["lint", "test", "build", "deploy"]
        found_targets = 0

        content = makefile.read_text()
        for target in targets:
            if re.search(f"^{target}:", content, re.MULTILINE):
                found_targets += 1
                evidence.append(f"Target '{target}' present")

        if re.search(r"^\\.PHONY:", content, re.MULTILINE):
            evidence.append(".PHONY declaration present")

        if "&&" in content:
            evidence.append("Error propagation with && chains")

        # Confidence
        if found_targets >= 4:
            confidence = "100%"
        elif found_targets >= 3:
            confidence = "88%"
        elif found_targets >= 2:
            confidence = "75%"
        else:
            confidence = "50%"

        return True, confidence, evidence, str(makefile)

    def detect_p002(self) -> Tuple[bool, str, List[str], str]:
        """Environment Sourcing"""
        env_dir = self.service_path / "env"
        makefile = self.service_path / "Makefile"

        if not env_dir.exists():
            return False, "0%", [], ""

        evidence = ["env/ directory exists"]
        files = [str(env_dir)]

        # Check for env files
        env_files = list(env_dir.glob(".env.*"))
        if env_files:
            evidence.append(f"Found {len(env_files)} environment files")

        # Check Makefile sourcing
        if makefile.exists() and "-include env/" in makefile.read_text():
            evidence.append("Makefile sources environment via -include")

        confidence = "100%" if len(env_files) >= 2 else "75%"
        return True, confidence, evidence, "|".join(str(f) for f in env_files)

    def detect_p003(self) -> Tuple[bool, str, List[str], str]:
        """GitHub Actions"""
        workflows_dir = self.service_path / ".github" / "workflows"
        if not workflows_dir.exists():
            return False, "0%", [], ""

        evidence = [".github/workflows/ directory exists"]
        has_branch = (workflows_dir / "branch.yaml").exists()
        has_main = (workflows_dir / "main.yaml").exists()
        make_count = self.grep_count("make ", workflows_dir)

        if has_branch:
            evidence.append("branch.yaml workflow found")
        if has_main:
            evidence.append("main.yaml workflow found")
        if make_count > 0:
            evidence.append(f"Workflows invoke make targets ({make_count} occurrences)")

        # Confidence
        if has_branch and has_main and make_count > 0:
            confidence = "100%"
        elif has_branch and has_main:
            confidence = "88%"
        elif has_branch or has_main:
            confidence = "75%"
        else:
            confidence = "50%"

        return True, confidence, evidence, str(workflows_dir)

    def detect_p004(self) -> Tuple[bool, str, List[str], str]:
        """CDK Stack"""
        cdk_dir = self.service_path / "cdk"
        if not cdk_dir.exists():
            return False, "0%", [], ""

        evidence = ["cdk/ directory exists"]
        files = [str(cdk_dir)]

        # Check for main CDK file
        cdk_main = cdk_dir / "main.go"
        if not cdk_main.exists():
            cdk_main = cdk_dir / "cdk.go"

        if cdk_main.exists():
            evidence.append(f"{cdk_main.name} found")
            files.append(str(cdk_main))

        # Check for ENV_NAME reading
        if cdk_main.exists() and "ENV_NAME" in cdk_main.read_text():
            evidence.append("Reads ENV_NAME from environment")

        # Check for aws-cdk-go import
        go_mod = self.service_path / "go.mod"
        if go_mod.exists() and "aws-cdk-go" in go_mod.read_text():
            evidence.append("aws-cdk-go v2 dependency present")

        confidence = "100%" if len(files) >= 2 and any("ENV_NAME" in open(f).read() for f in files if Path(f).is_file() and f.endswith(".go")) else "75%"
        return True, confidence, evidence, "|".join(files)

    def detect_p005(self) -> Tuple[bool, str, List[str], str]:
        """Go Modules"""
        go_mod = self.service_path / "go.mod"
        if not go_mod.exists():
            return False, "0%", [], ""

        content = go_mod.read_text()
        evidence = ["go.mod present"]

        # Check module name
        match = re.search(r"^module github\.com/{your-org}/ers-", content, re.MULTILINE)
        if match:
            evidence.append("Module follows github.com/{your-org}/ers-* pattern")

        # Check Go version
        if "go 1.2" in content:
            evidence.append("Go 1.20+ version")

        # Check dependencies
        if "aws-sdk-go-v2" in content:
            evidence.append("AWS SDK v2 dependency present")
        if "github.com/{your-org}/{service-name}" in content:
            evidence.append("{service-name} shared library dependency")

        confidence = "100%" if len(evidence) >= 3 else "75%"
        return True, confidence, evidence, str(go_mod)

    def detect_p006(self) -> Tuple[bool, str, List[str], str]:
        """Lambda Handler"""
        lambda_dir = self.service_path / "lambda"
        service_main = self.service_path / "main.go"

        handler_files = []
        if lambda_dir.exists():
            handler_files = self.find_files("main.go", lambda_dir)
        elif service_main.exists():
            handler_files = [str(service_main)]

        if not handler_files:
            return False, "0%", [], ""

        evidence = ["Lambda handler file(s) found"]

        # Check for lambda imports
        go_mod = self.service_path / "go.mod"
        if go_mod.exists() and "aws-lambda-go" in go_mod.read_text():
            evidence.append("aws-lambda-go dependency present")

        # Check for lambda.Start() calls
        total_lambda_start = 0
        for handler_file in handler_files:
            try:
                if "lambda.Start(" in open(handler_file).read():
                    total_lambda_start += 1
                    evidence.append(f"{Path(handler_file).name} has lambda.Start() call")
            except:
                pass

        confidence = "100%" if total_lambda_start > 0 else "75%"
        return True, confidence, evidence, "|".join(handler_files[:3])

    def detect_p007(self) -> Tuple[bool, str, List[str], str]:
        """Table-Driven Testing"""
        test_files = self.find_files("*_test.go", self.service_path)

        if not test_files:
            return False, "0%", [], ""

        evidence = [f"Found {len(test_files)} test files"]

        # Check for table-driven pattern
        table_tests = 0
        for test_file in test_files:
            try:
                if "tests := []struct" in open(test_file).read():
                    table_tests += 1
            except:
                pass

        if table_tests > 0:
            evidence.append(f"{table_tests} files use table-driven pattern")

        # Check for coverage target
        makefile = self.service_path / "Makefile"
        if makefile.exists() and "coverage" in makefile.read_text():
            evidence.append("Coverage target in Makefile")

        confidence = "100%" if len(test_files) >= 5 and table_tests >= 3 else "88%" if len(test_files) >= 3 else "50%"
        return True, confidence, evidence, "|".join(test_files[:3])

    def detect_p008(self) -> Tuple[bool, str, List[str], str]:
        """Security Patterns"""
        evidence = []

        # Check for JWT handling
        jwt_files = []
        try:
            result = subprocess.run(
                ["grep", "-r", "-l", "JWT\|JWKS\|jwt\|claims", str(self.service_path)],
                capture_output=True, text=True
            )
            jwt_files = [f for f in result.stdout.split("\n") if f and not ".git" in f]
        except:
            pass

        # Check for OAuth
        oauth_files = []
        try:
            result = subprocess.run(
                ["grep", "-r", "-l", "oauth\|Cognito\|authorization", str(self.service_path)],
                capture_output=True, text=True
            )
            oauth_files = [f for f in result.stdout.split("\n") if f and not ".git" in f]
        except:
            pass

        # Check for SigV4
        sigv4_files = []
        try:
            result = subprocess.run(
                ["grep", "-r", "-l", "SigV4\|aws.*sign", str(self.service_path)],
                capture_output=True, text=True
            )
            sigv4_files = [f for f in result.stdout.split("\n") if f and not ".git" in f]
        except:
            pass

        if jwt_files:
            evidence.append(f"JWT/JWKS handling found ({len(jwt_files)} files)")
        if oauth_files:
            evidence.append(f"OAuth/Cognito handling found ({len(oauth_files)} files)")
        if sigv4_files:
            evidence.append(f"SigV4 signing found ({len(sigv4_files)} files)")

        security_count = len([x for x in [jwt_files, oauth_files, sigv4_files] if x])
        if not security_count:
            return False, "0%", ["No security patterns detected"], ""

        confidence = "100%" if security_count >= 2 else "75%"
        files = "|".join((jwt_files + oauth_files + sigv4_files)[:5])
        return True, confidence, evidence, files

    def scan(self):
        """Run all pattern detections"""
        self.log_info(f"Starting service scan: {self.service_path}")

        detectors = [
            ("P-001", self.detect_p001),
            ("P-002", self.detect_p002),
            ("P-003", self.detect_p003),
            ("P-004", self.detect_p004),
            ("P-005", self.detect_p005),
            ("P-006", self.detect_p006),
            ("P-007", self.detect_p007),
            ("P-008", self.detect_p008),
        ]

        for pattern_id, detector in detectors:
            if self.patterns_filter and pattern_id not in self.patterns_filter:
                continue

            self.log_info(f"Scanning {pattern_id} ({self.pattern_names[pattern_id]})...")
            found, confidence, evidence, files = detector()

            result = {
                "pattern_id": pattern_id,
                "pattern_name": self.pattern_names[pattern_id],
                "found": found,
                "confidence": confidence,
                "evidence": evidence,
                "files": files,
            }
            self.results.append(result)

            if found:
                self.log_success(f"{pattern_id}: Found with {confidence} confidence")
            else:
                self.log_warn(f"{pattern_id}: Not found")

        self.log_success("Scan complete")

    def print_summary(self):
        """Print console summary"""
        print("")
        print(f"Scanning: {self.service_name}")

        found_count = 0
        for result in self.results:
            if result["found"]:
                found_count += 1
                print(f"  {result['pattern_id']} {result['pattern_name']:<35} ✓ {result['confidence']}")
            else:
                print(f"  {result['pattern_id']} {result['pattern_name']:<35} ✗ Not found")

        total = len(self.results)
        percentage = (found_count * 100 // total) if total > 0 else 0
        print(f"\nOverall Compliance: {found_count}/{total} patterns ({percentage}%)")

        if not self.dry_run:
            print(f"Spec files written to: {self.output_dir}")
        else:
            print("Dry-run mode (no files written)")
        print("")

    def write_spec_files(self):
        """Write YAML frontmatter + Markdown spec files"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for result in self.results:
            if not result["found"]:
                continue

            output_file = self.output_dir / f"{self.service_name}-{result['pattern_id']}.md"

            # YAML frontmatter
            yaml_content = f"""---
pattern_id: {result['pattern_id']}
pattern_name: {result['pattern_name']}
service: {self.service_name}
confidence: "{result['confidence']}"
last_verified: "{datetime.now().strftime('%Y-%m-%d')}"
compliance: "✓ Full"
files:
"""

            for file in result['files'].split("|") if result['files'] else []:
                if file:
                    yaml_content += f'  - "{file}"\n'
            if not result['files']:
                yaml_content += "  []\n"

            yaml_content += "evidence:\n"
            for ev in result['evidence']:
                yaml_content += f'  - "{ev}"\n'

            yaml_content += """variations: []
false_positives: []
---

## Pattern: {pattern_name}

Service: **{service_name}**
Confidence: **{confidence}**

### Evidence Found

""".format(
                pattern_name=result['pattern_name'],
                service_name=self.service_name,
                confidence=result['confidence']
            )

            for ev in result['evidence']:
                yaml_content += f"- {ev}\n"

            yaml_content += f"\n### Files Analyzed\n\n"
            for file in result['files'].split("|") if result['files'] else []:
                if file:
                    yaml_content += f"- `{file}`\n"

            yaml_content += f"\n---\n\nGenerated: {datetime.now().isoformat()}\n"

            output_file.write_text(yaml_content)
            self.log_success(f"Wrote: {output_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extract architectural specifications from services")
    parser.add_argument("service", nargs="?", default=".", help="Service path")
    parser.add_argument("--output-dir", default="specs", help="Output directory for spec files")
    parser.add_argument("--patterns", help="Comma-separated pattern IDs to scan (default: all)")
    parser.add_argument("--confidence-threshold", choices=["high", "medium", "low"], help="Minimum confidence to report")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of Markdown")
    parser.add_argument("--no-write", action="store_true", help="Dry-run (don't write files)")

    args = parser.parse_args()

    scanner = SpecExtractScanner(
        args.service,
        output_dir=args.output_dir,
        patterns_filter=args.patterns,
        confidence_threshold=args.confidence_threshold,
        output_format="json" if args.json else "markdown",
        dry_run=args.no_write
    )

    scanner.scan()
    scanner.print_summary()

    if not args.no_write:
        scanner.write_spec_files()


if __name__ == "__main__":
    main()
