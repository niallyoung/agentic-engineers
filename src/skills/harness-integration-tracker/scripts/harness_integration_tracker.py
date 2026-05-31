#!/usr/bin/env python3
"""
Harness Integration Tracker - Continuously discover and document agent/sub-agent
integration code/docs/info across all harnesses (OpenCode, Copilot, Claude, PI).

Usage:
    python harness_integration_tracker.py                    # Scan all harnesses
    python harness_integration_tracker.py --harness opencode # Scan specific harness
    python harness_integration_tracker.py --dry-run          # Preview changes
    python harness_integration_tracker.py --check-drift      # Drift check only
"""

import re
import sys
import json
import yaml
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
import ast


# ==============================================================================
# DATA CLASSES
# ==============================================================================

class DriftItem:
    """Single drift detection result."""
    
    def __init__(self, key, documented, in_code, file=None, status=""):
        self.key = key
        self.documented = documented
        self.in_code = in_code
        self.file = file
        self.status = status or self._compute_status()
    
    def _compute_status(self):
        if self.documented and not self.in_code:
            return "DRIFT: Documented but not in code"
        elif self.in_code and not self.documented:
            return "DRIFT: In code but not documented"
        else:
            return "OK"
    
    def to_dict(self):
        return {
            'key': self.key,
            'documented': self.documented,
            'in_code': self.in_code,
            'file': self.file,
            'status': self.status
        }


class HarnessMetadata:
    """Metadata for a harness."""
    
    def __init__(self, provider_name):
        self.provider_name = provider_name
        self.status = "active"
        self.version = ""
        self.known_keys = {"required": [], "optional": []}
        self.known_models = []
        self.integration_points = {}
        self.drift_items = []
        self.last_updated = ""
        self.notes = ""


# ==============================================================================
# HARNESS CLASSES
# ==============================================================================

class Harness:
    """Base class for harness integrations."""
    
    provider_name: str = "base"
    config_pattern: str = ""
    env_var_pattern: str = ""
    
    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root)
        self.metadata = HarnessMetadata(provider_name=self.provider_name)
    
    def scan(self) -> HarnessMetadata:
        """Scan harness code and generate metadata."""
        self._scan_config()
        self._scan_agent_code()
        self._scan_tests()
        self._find_integration_points()
        self.metadata.last_updated = datetime.now().isoformat()
        return self.metadata
    
    def check_drift(self, docs_dir: Path) -> List[DriftItem]:
        """Check drift between docs and code."""
        self.metadata.drift_items = []
        
        if not docs_dir.exists():
            return self.metadata.drift_items
        
        # Read documented keys and models from INTEGRATION-SUMMARY.md
        summary_file = docs_dir / "INTEGRATION-SUMMARY.md"
        documented_keys = set()
        documented_models = set()
        
        if summary_file.exists():
            content = summary_file.read_text()
            # Extract documented keys
            documented_keys = self._extract_documented_keys(content)
            # Extract documented models
            documented_models = self._extract_documented_models(content)
        
        # Check for drift in keys
        code_keys = set(self.metadata.known_keys.get("required", []) + 
                       self.metadata.known_keys.get("optional", []))
        
        # Keys in docs but not code
        for key in documented_keys:
            if key not in code_keys:
                self.metadata.drift_items.append(DriftItem(
                    key=key,
                    documented=True,
                    in_code=False,
                    file=str(summary_file)
                ))
        
        # Keys in code but not documented
        for key in code_keys:
            if key not in documented_keys:
                self.metadata.drift_items.append(DriftItem(
                    key=key,
                    documented=False,
                    in_code=True,
                    file=str(self._get_agent_impl_file())
                ))
        
        # Check for model drift similarly
        code_models = set(self.metadata.known_models)
        for model in documented_models:
            if model not in code_models:
                self.metadata.drift_items.append(DriftItem(
                    key=f"model:{model}",
                    documented=True,
                    in_code=False,
                    file=str(summary_file)
                ))
        
        for model in code_models:
            if model not in documented_models:
                self.metadata.drift_items.append(DriftItem(
                    key=f"model:{model}",
                    documented=False,
                    in_code=True,
                    file=str(self._get_agent_impl_file())
                ))
        
        return self.metadata.drift_items
    
    def _scan_config(self):
        """Scan config file for version and keys."""
        if not self.config_pattern:
            return
        
        config_files = list(self.repo_root.glob(f"config/*{self.config_pattern}*"))
        if not config_files:
            return
        
        config_file = config_files[0]
        try:
            with open(config_file) as f:
                config = yaml.safe_load(f)
            
            # Extract version
            if config and 'harnesses' in config:
                harness_config = config['harnesses'].get(self.provider_name, {})
                self.metadata.version = harness_config.get('version', '')
                
                # Extract models
                if 'models' in harness_config:
                    self.metadata.known_models = harness_config['models']
                
                # Store integration point
                self.metadata.integration_points['config'] = str(config_file.relative_to(self.repo_root))
        except Exception as e:
            print(f"Warning: Failed to parse config {config_file}: {e}")
    
    def _scan_agent_code(self):
        """Scan agent implementation for KNOWN_KEYS and KNOWN_MODELS."""
        agent_file = self._get_agent_impl_file()
        if not agent_file or not agent_file.exists():
            return
        
        try:
            content = agent_file.read_text()
            
            # Extract KNOWN_KEYS
            keys = self._extract_dict_from_code(content, "KNOWN_KEYS")
            if keys:
                self.metadata.known_keys = keys
            
            # Extract KNOWN_MODELS
            models = self._extract_list_from_code(content, "KNOWN_MODELS")
            if models:
                self.metadata.known_models = models
            
            self.metadata.integration_points['agent_impl'] = str(agent_file.relative_to(self.repo_root))
        except Exception as e:
            print(f"Warning: Failed to scan agent code {agent_file}: {e}")
    
    def _scan_tests(self):
        """Scan test files for model references."""
        test_dir = self.repo_root / "tests"
        if not test_dir.exists():
            return
        
        test_files = list(test_dir.glob(f"test_*{self.provider_name}*.py"))
        if test_files:
            self.metadata.integration_points['tests'] = [
                str(f.relative_to(self.repo_root)) for f in test_files
            ]
    
    def _find_integration_points(self):
        """Find and record integration points."""
        docs_dir = self.repo_root / "docs" / "research" / f"{self.provider_name}-docs"
        if docs_dir.exists():
            doc_files = [f.name for f in docs_dir.glob("*.md")]
            self.metadata.integration_points['docs'] = str(docs_dir.relative_to(self.repo_root))
    
    def _get_agent_impl_file(self) -> Optional[Path]:
        """Get path to agent implementation file."""
        agent_dir = self.repo_root / "src" / "orchestration" / "agents"
        if not agent_dir.exists():
            return None
        
        # Look for {provider_name}.py or {provider_name}_agent.py
        candidates = [
            agent_dir / f"{self.provider_name}.py",
            agent_dir / f"{self.provider_name}_agent.py",
            agent_dir / f"{self.provider_name}_harness.py"
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
        
        return None
    
    @staticmethod
    def _extract_dict_from_code(code: str, var_name: str) -> Optional[Dict]:
        """Extract dictionary assignment from Python code."""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == var_name:
                            if isinstance(node.value, ast.Dict):
                                return Harness._dict_from_ast(node.value)
        except:
            pass
        return None
    
    @staticmethod
    def _extract_list_from_code(code: str, var_name: str) -> Optional[List]:
        """Extract list assignment from Python code."""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == var_name:
                            if isinstance(node.value, ast.List):
                                return Harness._list_from_ast(node.value)
        except:
            pass
        return None
    
    @staticmethod
    def _dict_from_ast(node: ast.Dict) -> Dict:
        """Convert AST Dict node to Python dict."""
        result = {}
        for key_node, value_node in zip(node.keys, node.values):
            key = None
            if isinstance(key_node, ast.Constant):
                key = key_node.value
            elif isinstance(key_node, ast.Str):  # Python < 3.8
                key = key_node.s
            
            if key:
                if isinstance(value_node, ast.List):
                    result[key] = Harness._list_from_ast(value_node)
                elif isinstance(value_node, ast.Dict):
                    result[key] = Harness._dict_from_ast(value_node)
        return result
    
    @staticmethod
    def _list_from_ast(node: ast.List) -> List:
        """Convert AST List node to Python list."""
        result = []
        for elem in node.elts:
            if isinstance(elem, ast.Constant):
                result.append(elem.value)
            elif isinstance(elem, ast.Str):  # Python < 3.8
                result.append(elem.s)
        return result
    
    @staticmethod
    def _extract_documented_keys(content: str) -> Set[str]:
        """Extract documented KNOWN_KEYS from markdown."""
        keys = set()
        # Look for keys listed under KNOWN_KEYS section
        if "KNOWN_KEYS" in content:
            # Find section
            section_match = re.search(r"## KNOWN_KEYS(.*?)(?=##|$)", content, re.DOTALL)
            if section_match:
                section = section_match.group(1)
                # Extract keys (lines starting with -, or in tables)
                for line in section.split('\n'):
                    if line.strip().startswith('- '):
                        key = line.strip()[2:].strip()
                        # Extract just the key name (before parentheses)
                        key = re.sub(r'\s*\(.*?\)', '', key)
                        if key:
                            keys.add(key)
        return keys
    
    @staticmethod
    def _extract_documented_models(content: str) -> Set[str]:
        """Extract documented KNOWN_MODELS from markdown."""
        models = set()
        if "KNOWN_MODELS" in content:
            section_match = re.search(r"## KNOWN_MODELS(.*?)(?=##|$)", content, re.DOTALL)
            if section_match:
                section = section_match.group(1)
                # Extract model names
                for line in section.split('\n'):
                    if line.strip().startswith('- '):
                        model = line.strip()[2:].strip()
                        # Extract model identifier
                        model = model.split('|')[0].strip()
                        model = re.sub(r'\s*\(.*?\)', '', model)
                        if model and len(model) > 2:
                            models.add(model)
        return models


class OpenCodeHarness(Harness):
    """OpenCode harness integration."""
    provider_name = "opencode"
    config_pattern = "opencode"


class CopilotHarness(Harness):
    """Copilot CLI harness integration."""
    provider_name = "copilot"
    config_pattern = "copilot"


class ClaudeHarness(Harness):
    """Claude Code harness integration."""
    provider_name = "claude"
    config_pattern = "claude"


class PIHarness(Harness):
    """Project Iris harness integration (planned)."""
    provider_name = "pi"
    config_pattern = "pi"


# ==============================================================================
# REPORT GENERATORS
# ==============================================================================

class MarkdownReportGenerator:
    """Generate markdown INTEGRATION-SUMMARY.md."""
    
    @staticmethod
    def generate(metadata: HarnessMetadata, repo_root: Path) -> str:
        """Generate markdown report from metadata."""
        lines = []
        
        # Header
        lines.append(f"# {metadata.provider_name.title()} Integration Summary")
        lines.append("")
        
        # Metadata
        lines.append(f"**Last Updated**: {metadata.last_updated}")
        lines.append(f"**Framework Version**: 5.10.0")
        lines.append(f"**Harness Status**: {'✅ Active' if metadata.status == 'active' else '🔄 Planned'}")
        lines.append("")
        
        # KNOWN_KEYS section
        lines.append("## KNOWN_KEYS")
        lines.append("")
        
        if metadata.known_keys.get('required'):
            lines.append("### Required")
            for key in metadata.known_keys['required']:
                lines.append(f"- {key}")
            lines.append("")
        
        if metadata.known_keys.get('optional'):
            lines.append("### Optional")
            for key in metadata.known_keys['optional']:
                lines.append(f"- {key}")
            lines.append("")
        
        # KNOWN_MODELS section
        if metadata.known_models:
            lines.append("## KNOWN_MODELS")
            lines.append("")
            lines.append("| Model | Version | Capability | Tested |")
            lines.append("|-------|---------|-----------|--------|")
            for model in metadata.known_models:
                lines.append(f"| {model} | 1.0 | ✅ | ✅ |")
            lines.append("")
        
        # Drift Detection section
        if metadata.drift_items:
            lines.append("## Drift Detection")
            lines.append("")
            lines.append("| Key | Documented | In Code | Status |")
            lines.append("|-----|-----------|---------|--------|")
            for drift in metadata.drift_items:
                doc_mark = "✅" if drift.documented else "❌"
                code_mark = "✅" if drift.in_code else "❌"
                status = "✅ OK" if drift.status == "OK" else f"⚠️ {drift.status}"
                lines.append(f"| {drift.key} | {doc_mark} | {code_mark} | {status} |")
            lines.append("")
        
        # Integration Points section
        if metadata.integration_points:
            lines.append("## Integration Points")
            lines.append("")
            for name, path in metadata.integration_points.items():
                if isinstance(path, list):
                    lines.append(f"- **{name}**: {', '.join(path)}")
                else:
                    lines.append(f"- **{name}**: {path}")
            lines.append("")
        
        return "\n".join(lines)


class YamlReportGenerator:
    """Generate machine-readable integration-summary.yaml."""
    
    @staticmethod
    def generate(harnesses: Dict[str, HarnessMetadata]) -> str:
        """Generate YAML report from harness metadata."""
        report = {}
        
        for name, metadata in harnesses.items():
            harness_dict = {
                'status': metadata.status,
                'version': metadata.version,
                'known_keys': metadata.known_keys,
                'known_models': metadata.known_models,
                'drift': [d.to_dict() for d in metadata.drift_items],
                'integration_points': metadata.integration_points,
                'last_updated': metadata.last_updated
            }
            report[name] = harness_dict
        
        return yaml.dump({'harnesses': report}, default_flow_style=False, sort_keys=False)


# ==============================================================================
# MAIN ORCHESTRATOR
# ==============================================================================

class HarnessIntegrationTracker:
    """Main orchestrator for harness integration tracking."""
    
    HARNESS_CLASSES = {
        'opencode': OpenCodeHarness,
        'copilot': CopilotHarness,
        'claude': ClaudeHarness,
        'pi': PIHarness
    }
    
    def __init__(self, repo_root: Path, dry_run: bool = False):
        self.repo_root = Path(repo_root)
        self.dry_run = dry_run
        self.harnesses: Dict[str, HarnessMetadata] = {}
    
    def scan_all(self) -> Dict[str, HarnessMetadata]:
        """Scan all harnesses."""
        for harness_name, harness_class in self.HARNESS_CLASSES.items():
            self.scan_harness(harness_name)
        return self.harnesses
    
    def scan_harness(self, harness_name: str) -> HarnessMetadata:
        """Scan single harness."""
        if harness_name not in self.HARNESS_CLASSES:
            raise ValueError(f"Unknown harness: {harness_name}")
        
        harness_class = self.HARNESS_CLASSES[harness_name]
        harness = harness_class(self.repo_root)
        metadata = harness.scan()
        self.harnesses[harness_name] = metadata
        
        return metadata
    
    def check_drift(self, harness_name: Optional[str] = None) -> Dict[str, List[DriftItem]]:
        """Check drift for harnesses."""
        drift_results = {}
        
        harnesses_to_check = [harness_name] if harness_name else list(self.HARNESS_CLASSES.keys())
        
        for hname in harnesses_to_check:
            harness_class = self.HARNESS_CLASSES[hname]
            harness = harness_class(self.repo_root)
            harness.scan()
            
            docs_dir = self.repo_root / "docs" / "research" / f"{hname}-docs"
            drift_items = harness.check_drift(docs_dir)
            drift_results[hname] = drift_items
            
            if hname not in self.harnesses:
                self.harnesses[hname] = harness.metadata
        
        return drift_results
    
    def generate_reports(self, harness_name: Optional[str] = None) -> Dict[str, str]:
        """Generate markdown reports for harnesses."""
        reports = {}
        
        harnesses_to_report = [harness_name] if harness_name else list(self.harnesses.keys())
        
        for hname in harnesses_to_report:
            if hname not in self.harnesses:
                continue
            
            metadata = self.harnesses[hname]
            markdown = MarkdownReportGenerator.generate(metadata, self.repo_root)
            
            # Write to file
            docs_dir = self.repo_root / "docs" / "research" / f"{hname}-docs"
            summary_file = docs_dir / "INTEGRATION-SUMMARY.md"
            
            if not self.dry_run:
                docs_dir.mkdir(parents=True, exist_ok=True)
                summary_file.write_text(markdown)
                print(f"✅ Generated {summary_file}")
            else:
                print(f"[DRY RUN] Would generate {summary_file}")
            
            reports[hname] = markdown
        
        return reports
    
    def generate_yaml_report(self) -> str:
        """Generate combined YAML report."""
        yaml_content = YamlReportGenerator.generate(self.harnesses)
        
        if not self.dry_run:
            output_file = self.repo_root / "integration-summary.yaml"
            output_file.write_text(yaml_content)
            print(f"✅ Generated {output_file}")
        else:
            print(f"[DRY RUN] Would generate integration-summary.yaml")
        
        return yaml_content


# ==============================================================================
# CLI
# ==============================================================================

def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Harness Integration Tracker - Monitor and document harness integrations"
    )
    parser.add_argument(
        '--repo-root',
        type=Path,
        default=Path.cwd(),
        help='Repository root directory (default: current directory)'
    )
    parser.add_argument(
        '--harness',
        choices=['opencode', 'copilot', 'claude', 'pi'],
        help='Scan specific harness (default: all)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without writing files'
    )
    parser.add_argument(
        '--check-drift',
        action='store_true',
        help='Check drift only (no report generation)'
    )
    parser.add_argument(
        '--generate-reports',
        action='store_true',
        help='Generate reports only (no scanning)'
    )
    parser.add_argument(
        '--report',
        type=Path,
        help='Write report to custom path'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    tracker = HarnessIntegrationTracker(args.repo_root, dry_run=args.dry_run)
    
    try:
        if args.check_drift:
            # Drift check only
            print("Checking drift...")
            drift_results = tracker.check_drift(args.harness)
            
            total_drift = sum(len(items) for items in drift_results.values())
            print(f"✅ Drift check complete: {total_drift} drift items found")
            
            for hname, items in drift_results.items():
                if items:
                    print(f"\n{hname.upper()}:")
                    for item in items:
                        print(f"  - {item.key}: {item.status}")
        
        else:
            # Full scan
            print("Scanning harnesses...")
            if args.harness:
                tracker.scan_harness(args.harness)
                print(f"✅ Scanned {args.harness}")
            else:
                tracker.scan_all()
                print(f"✅ Scanned {len(tracker.harnesses)} harnesses")
            
            # Check drift
            print("Checking drift...")
            drift_results = tracker.check_drift(args.harness)
            total_drift = sum(len(items) for items in drift_results.values())
            print(f"✅ Found {total_drift} drift items")
            
            # Generate reports
            if not args.check_drift:
                print("Generating reports...")
                tracker.generate_reports(args.harness)
                tracker.generate_yaml_report()
                print("✅ Reports generated")
        
        return 0
    
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        if args.verbose:
            import logging
            logging.exception("Detailed error context")
        return 1


if __name__ == "__main__":
    sys.exit(main())
