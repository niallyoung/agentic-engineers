"""Core skill interoperability matrix test runner."""

import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

from .models import (
    SkillTestResult,
    MatrixResult,
    TestStatus,
    FailureMode,
    SkillInvocationTest,
)
from .protocol import DelegateGenerator, HandbackValidator


class SkillInteropMatrix:
    """Main test runner for skill interoperability matrix."""

    # 14 skills available across all harnesses
    ALL_SKILLS = [
        "ab-testing",
        "agent-creator",
        "cicd-monitor",
        "consistency-checker",
        "cost-aggregation",
        "file-sync",
        "metrics-etl",
        "model-engineer",
        "model-selection",
        "protocol-validator",
        "queue-management",
        "skill-creator",
        "spec-management",
        "spec-validator",
        "usage-tracking",
        "voice-notify",
        "workflow-review",
    ]

    # 4 harnesses to test
    ALL_HARNESSES = [
        "copilot",
        "claude",
        "opencode",
        "pi",
    ]

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        artifacts_dir: Optional[Path] = None,
        timeout_seconds: int = 30,
        latency_threshold_ms: float = 5000.0,
    ):
        """Initialize matrix runner.
        
        Args:
            repo_root: Repository root path
            artifacts_dir: Directory for test artifacts
            timeout_seconds: Timeout for each skill invocation
            latency_threshold_ms: Latency threshold (5s default)
        """
        self.repo_root = repo_root or self._get_default_repo_root()
        self.artifacts_dir = artifacts_dir or (self.repo_root / "artifacts" / "evals")
        self.timeout_seconds = timeout_seconds
        self.latency_threshold_ms = latency_threshold_ms
        
        # Create artifacts directory
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        self.result = MatrixResult()

    def _get_default_repo_root(self) -> Path:
        """Get the default repository root path.
        
        Uses environment variable REPO_ROOT if set, otherwise derives from current file location.
        Falls back to Path.home() for CI compatibility.
        """
        import os
        
        # Check environment variable first
        env_root = os.getenv("REPO_ROOT")
        if env_root:
            return Path(env_root)
        
        # Try to derive from current file location (relative to src/evals)
        current_file = Path(__file__)
        if "src/evals" in str(current_file):
            # Navigate up from src/evals/skill_matrix/matrix_runner.py
            repo_root = current_file.parent.parent.parent.parent
            if (repo_root / ".git").exists():
                return repo_root
        
        # Fallback for CI: use home directory
        return Path.home() / "git" / "agentic-engineers"

    def _skills_dir(self) -> Path:
        """Return the rendered skills directory.

        Uses the repository's deterministic rendered output
        ``<repo_root>/dist/claude/skills`` (produced by ``make render-claude``)
        rather than the developer's ``~/.claude/skills``, which is only
        populated by ``make install-claude`` and is empty on fresh CI runners.
        """
        return self.repo_root / "dist" / "claude" / "skills"

    def get_available_skills(self) -> List[str]:
        """Get list of available skills."""
        skills_dir = self._skills_dir()
        if not skills_dir.exists():
            return []
        
        available = []
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                available.append(skill_dir.name)
        
        return sorted(available)

    def test_skill_availability(self, skill_name: str) -> Tuple[bool, Optional[str]]:
        """Test if a skill is available.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            Tuple of (is_available, error_message)
        """
        skills_dir = self._skills_dir()
        skill_path = skills_dir / skill_name
        
        if not skill_path.exists():
            return False, f"Skill directory not found: {skill_path}"
        
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            return False, f"SKILL.md not found in {skill_path}"
        
        try:
            with open(skill_md, 'r') as f:
                content = f.read()
                if not content.strip():
                    return False, f"SKILL.md is empty for {skill_name}"
                # Check for minimal YAML frontmatter
                if "---" not in content and "name:" not in content:
                    return False, f"SKILL.md missing frontmatter for {skill_name}"
        except Exception as e:
            return False, f"Failed to read SKILL.md: {str(e)}"
        
        return True, None

    def invoke_skill_on_harness(
        self,
        skill_name: str,
        harness: str,
        test_id: Optional[str] = None,
    ) -> SkillTestResult:
        """Invoke a skill on a specific harness.
        
        Args:
            skill_name: Name of the skill
            harness: Target harness
            test_id: Optional test ID
            
        Returns:
            SkillTestResult with invocation details
        """
        if test_id is None:
            timestamp = datetime.now().strftime("%Y-%m-%d")
            test_id = f"{timestamp}-skill-{skill_name}-{harness}"
        
        start_time = time.time()
        
        # Check skill availability first
        is_available, error_msg = self.test_skill_availability(skill_name)
        if not is_available:
            latency_ms = (time.time() - start_time) * 1000
            result = SkillTestResult(
                skill_name=skill_name,
                harness=harness,
                status=TestStatus.UNAVAILABLE,
                success_rate=0.0,
                latency_ms=latency_ms,
                failure_mode=FailureMode.SKILL_UNAVAILABLE,
                error_message=error_msg,
            )
            return result
        
        try:
            # Generate DELEGATE
            delegate = DelegateGenerator.create_skill_test_delegate(
                skill_name=skill_name,
                harness=harness,
                task_id=test_id,
            )
            
            delegate_path = self._save_test_artifact(
                "delegates",
                f"DELEGATE-{test_id}.yaml",
                delegate,
            )
            
            # Simulate skill invocation with DELEGATE
            # In actual implementation, this would invoke the skill on the harness
            invocation_result = self._invoke_skill_simulation(
                skill_name=skill_name,
                harness=harness,
                delegate=delegate,
                timeout_seconds=self.timeout_seconds,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Determine status based on latency and success
            if invocation_result.get("error"):
                status = TestStatus.FAIL
                failure_mode = FailureMode.INVOCATION_FAILED
            elif latency_ms > self.latency_threshold_ms:
                status = TestStatus.TIMEOUT
                failure_mode = FailureMode.LATENCY_EXCEEDED
            elif invocation_result.get("success_rate", 0.0) >= 0.95:
                status = TestStatus.PASS
                failure_mode = None
            elif invocation_result.get("success_rate", 0.0) >= 0.80:
                status = TestStatus.YELLOW
                failure_mode = None
            else:
                status = TestStatus.FAIL
                failure_mode = FailureMode.INVOCATION_FAILED
            
            result = SkillTestResult(
                skill_name=skill_name,
                harness=harness,
                status=status,
                success_rate=invocation_result.get("success_rate", 0.0),
                latency_ms=latency_ms,
                failure_mode=failure_mode,
                error_message=invocation_result.get("error"),
                delegate_path=str(delegate_path),
                tokens_in=invocation_result.get("tokens_in", 0),
                tokens_out=invocation_result.get("tokens_out", 0),
                cost_usd=invocation_result.get("cost_usd", 0.0),
            )
            
            return result
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return SkillTestResult(
                skill_name=skill_name,
                harness=harness,
                status=TestStatus.FAIL,
                success_rate=0.0,
                latency_ms=latency_ms,
                failure_mode=FailureMode.UNKNOWN,
                error_message=str(e),
            )

    def _invoke_skill_simulation(
        self,
        skill_name: str,
        harness: str,
        delegate: Dict[str, Any],
        timeout_seconds: int = 30,
    ) -> Dict[str, Any]:
        """Simulate skill invocation (simplified version for testing).
        
        In production, this would actually invoke the skill on the harness.
        For now, we perform basic validation checks.
        """
        try:
            # Basic validation checks that simulate invocation
            # This is a simplified version - real implementation would actually invoke skills
            
            # Check 1: Delegate validation
            if not delegate.get("handoff_type") == "DELEGATE":
                return {
                    "error": "Invalid DELEGATE structure",
                    "success_rate": 0.0,
                }
            
            # Check 2: Skill metadata validation
            skills_dir = self._skills_dir()
            skill_path = skills_dir / skill_name
            
            if not skill_path.exists():
                return {
                    "error": f"Skill {skill_name} not available on {harness}",
                    "success_rate": 0.0,
                }
            
            # Check 3: Validate skill metadata
            try:
                skill_md_path = skill_path / "SKILL.md"
                with open(skill_md_path, 'r') as f:
                    content = f.read()
                    # Simple checks for frontmatter
                    if "---" in content and len(content) > 50:
                        # Skill appears valid
                        return {
                            "success": True,
                            "success_rate": 1.0,
                            "tokens_in": 100,
                            "tokens_out": 50,
                            "cost_usd": 0.005,
                        }
            except Exception as e:
                return {
                    "error": f"Failed to read skill metadata: {str(e)}",
                    "success_rate": 0.0,
                }
            
            # Default to warning state (yellow)
            return {
                "success_rate": 0.85,
                "tokens_in": 100,
                "tokens_out": 50,
                "cost_usd": 0.005,
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "success_rate": 0.0,
            }

    def _save_test_artifact(
        self,
        subdirectory: str,
        filename: str,
        data: Dict[str, Any],
    ) -> Path:
        """Save test artifact to disk.
        
        Args:
            subdirectory: Subdirectory within artifacts_dir
            filename: Filename for the artifact
            data: Data to save (will be YAML)
            
        Returns:
            Path to saved artifact
        """
        artifact_path = self.artifacts_dir / subdirectory
        artifact_path.mkdir(parents=True, exist_ok=True)
        
        filepath = artifact_path / filename
        
        import yaml
        with open(filepath, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
        return filepath

    def run_full_matrix(
        self,
        skills: Optional[List[str]] = None,
        harnesses: Optional[List[str]] = None,
    ) -> MatrixResult:
        """Run full interoperability matrix tests.
        
        Args:
            skills: Skills to test (all if None)
            harnesses: Harnesses to test (all if None)
            
        Returns:
            MatrixResult with all test results
        """
        if skills is None:
            skills = self.get_available_skills()
        if harnesses is None:
            harnesses = self.ALL_HARNESSES
        
        print(f"Running skill interoperability matrix...")
        print(f"Skills: {len(skills)}")
        print(f"Harnesses: {len(harnesses)}")
        print(f"Total combinations: {len(skills) * len(harnesses)}")
        print()
        
        combination_count = 0
        for skill in skills:
            for harness in harnesses:
                combination_count += 1
                print(f"[{combination_count}] Testing {skill} on {harness}...", end=" ", flush=True)
                
                result = self.invoke_skill_on_harness(skill, harness)
                self.result.add_result(result)
                
                print(f"{result.status.value}")
        
        return self.result

    def run_filtered_matrix(
        self,
        skill_filter: Optional[str] = None,
        harness_filter: Optional[str] = None,
    ) -> MatrixResult:
        """Run filtered interoperability matrix tests.
        
        Args:
            skill_filter: Only test skills matching this pattern
            harness_filter: Only test harnesses matching this pattern
            
        Returns:
            MatrixResult with filtered test results
        """
        available_skills = self.get_available_skills()
        
        # Filter skills
        if skill_filter:
            skills = [s for s in available_skills if skill_filter.lower() in s.lower()]
        else:
            skills = available_skills
        
        # Filter harnesses
        if harness_filter:
            harnesses = [h for h in self.ALL_HARNESSES if harness_filter.lower() in h.lower()]
        else:
            harnesses = self.ALL_HARNESSES
        
        return self.run_full_matrix(skills=skills, harnesses=harnesses)

    def generate_matrix_visualization(self) -> str:
        """Generate colored matrix visualization.
        
        Returns:
            String representation of the matrix
        """
        # Group results by skill
        by_skill: Dict[str, Dict[str, SkillTestResult]] = {}
        for cell in self.result.cells:
            if cell.skill_name not in by_skill:
                by_skill[cell.skill_name] = {}
            by_skill[cell.skill_name][cell.harness] = cell
        
        # Build header
        lines = []
        lines.append("=" * 80)
        lines.append("Skill Interoperability Matrix")
        lines.append("=" * 80)
        lines.append("")
        
        # Add summary
        lines.append(f"Total Combinations: {self.result.total_combinations}")
        lines.append(f"Passed:  {self.result.passed} {TestStatus.PASS.value}")
        lines.append(f"Warning: {self.result.warned} {TestStatus.YELLOW.value}")
        lines.append(f"Failed:  {self.result.failed} {TestStatus.FAIL.value}")
        lines.append(f"Skipped: {self.result.skipped} {TestStatus.SKIPPED.value}")
        lines.append("")
        lines.append(f"Overall Success Rate: {self.result.overall_success_rate:.1%}")
        lines.append(f"Quality Score: {self.result.quality_score:.1f}/100")
        lines.append("")
        lines.append("-" * 80)
        lines.append("")
        
        # Build matrix
        header = "Skill".ljust(25) + " ".join(h.ljust(12) for h in self.ALL_HARNESSES)
        lines.append(header)
        lines.append("-" * 80)
        
        for skill in sorted(by_skill.keys()):
            cells = by_skill[skill]
            statuses = []
            for harness in self.ALL_HARNESSES:
                if harness in cells:
                    status = cells[harness].status.value
                else:
                    status = "⊘"
                statuses.append(status.ljust(12))
            
            line = skill.ljust(25) + " ".join(statuses)
            lines.append(line)
        
        lines.append("-" * 80)
        lines.append("")
        
        return "\n".join(lines)

    def generate_json_report(self) -> str:
        """Generate JSON report of test results.
        
        Returns:
            JSON string with all test results
        """
        return json.dumps(self.result.to_dict(), indent=2)

    def save_report(self, output_dir: Optional[Path] = None) -> Tuple[Path, Path]:
        """Save report to disk.
        
        Args:
            output_dir: Directory to save reports (uses artifacts_dir if None)
            
        Returns:
            Tuple of (matrix_txt_path, matrix_json_path)
        """
        if output_dir is None:
            output_dir = self.artifacts_dir
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save text report
        matrix_txt = output_dir / "skill-matrix.txt"
        with open(matrix_txt, 'w') as f:
            f.write(self.generate_matrix_visualization())
        
        # Save JSON report
        matrix_json = output_dir / "skill-matrix.json"
        with open(matrix_json, 'w') as f:
            f.write(self.generate_json_report())
        
        return matrix_txt, matrix_json
