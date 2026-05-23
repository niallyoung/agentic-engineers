# -*- coding: utf-8 -*-
"""
repo_init.py — Main orchestrator for repo-init skill.

Runs all 8 phases of repository initialization in order:
  1. Analyze      — Scan repo for language, tools, CI, etc.
  2. Generate SPEC.md — Render project-specific specification
  3. Bootstrap structure — Create agents/, skills/, tests/, docs/
  4. Housekeeping — Patch .gitignore, README.md
  5. Framework bootstrap — Copy core agents + skills
  6. Validate compatibility — Check harness + tool availability
  7. Initialize TODO.md — Bootstrap task queue
  8. Generate docs — ONBOARDING.md, QUICK-START.md, AGENTS.md

Author: Senior Engineer
Phase: Design + Implementation scaffold
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# Phase imports (each in its own module for single-responsibility)
from analyze_repo import AnalysisResult, analyze_repo
from generate_spec import generate_spec
from bootstrap_structure import bootstrap_structure
from housekeeping import run_housekeeping
from framework_bootstrap import framework_bootstrap
from validate_compatibility import CompatibilityResult, validate_compatibility
from init_todo import init_todo
from generate_docs import generate_docs


# ============================================================================
# CONSTANTS
# ============================================================================

SKILL_VERSION = "1.0"
SUPPORTED_HARNESSES = ("claude", "gpt5", "local", "copilot")
SUPPORTED_FRAMEWORK_VERSIONS = ("5.10",)

ALL_PHASES = (
    "analyze",
    "generate-spec",
    "bootstrap-structure",
    "housekeeping",
    "framework-bootstrap",
    "validate-compatibility",
    "init-todo",
    "generate-docs",
)


# ============================================================================
# CONFIG
# ============================================================================

@dataclass
class RepoInitConfig:
    """Configuration for a single repo-init run."""

    repo_root: Path
    project_name: str = ""                 # Inferred from dirname if empty
    project_description: str = ""
    model_harness: str = "claude"          # "claude" | "gpt5" | "local" | "copilot"
    framework_version: str = "5.10"
    dry_run: bool = False
    force_reinit: bool = False             # Overwrite existing init marker
    resume: bool = False                   # Resume from failed init
    conservative_defaults: bool = True
    skip_phases: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.repo_root = Path(self.repo_root).resolve()
        if not self.project_name:
            self.project_name = self.repo_root.name.lower().replace(" ", "-")
        if self.model_harness not in SUPPORTED_HARNESSES:
            raise ValueError(
                f"model_harness must be one of {SUPPORTED_HARNESSES}; "
                f"got: {self.model_harness!r}"
            )
        for phase in self.skip_phases:
            if phase not in ALL_PHASES:
                raise ValueError(
                    f"Unknown phase {phase!r}. Valid phases: {ALL_PHASES}"
                )


# ============================================================================
# RESULT
# ============================================================================

@dataclass
class InitResult:
    """Result of a repo-init run."""

    status: str                           # "SUCCESS" | "FAILED" | "PARTIAL" | "DRY_RUN"
    project_name: str
    phases_completed: List[str] = field(default_factory=list)
    phases_skipped: List[str] = field(default_factory=list)
    phases_failed: List[str] = field(default_factory=list)
    files_created: List[Path] = field(default_factory=list)
    files_modified: List[Path] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    compatibility: Optional[CompatibilityResult] = None
    span: Dict = field(default_factory=dict)

    def __str__(self) -> str:
        lines = [
            f"[{self.status}] repo-init: {self.project_name}",
            f"  phases completed: {len(self.phases_completed)}/{len(ALL_PHASES)}",
            f"  files created:    {len(self.files_created)}",
            f"  files modified:   {len(self.files_modified)}",
            f"  warnings:         {len(self.warnings)}",
            f"  errors:           {len(self.errors)}",
        ]
        if self.warnings:
            for w in self.warnings:
                lines.append(f"  ⚠  {w}")
        if self.errors:
            for e in self.errors:
                lines.append(f"  ✗  {e}")
        if "duration_ms" in self.span:
            lines.append(f"  duration:         {self.span['duration_ms']}ms")
        return "\n".join(lines)


# ============================================================================
# INITIALIZER
# ============================================================================

class RepoInitializer:
    """
    Orchestrates all 8 phases of repository initialization.

    Usage:
        cfg = RepoInitConfig(repo_root=Path("/path/to/repo"))
        result = RepoInitializer().run(cfg)
    """

    def run(self, cfg: RepoInitConfig) -> InitResult:
        """Run all phases and return an InitResult."""
        start_ms = int(time.monotonic() * 1000)

        result = InitResult(
            status="FAILED",
            project_name=cfg.project_name,
        )

        # ── Pre-flight checks ─────────────────────────────────────────────
        preflight_errors = self._preflight(cfg)
        if preflight_errors:
            result.errors.extend(preflight_errors)
            result.status = "FAILED"
            return result

        if cfg.dry_run:
            result.status = "DRY_RUN"
            result.phases_completed = list(ALL_PHASES)
            result.span = {"duration_ms": 0, "files_created": 0}
            return result

        # ── Phase execution ───────────────────────────────────────────────
        analysis: Optional[AnalysisResult] = None
        compat: Optional[CompatibilityResult] = None

        for phase in ALL_PHASES:
            if phase in cfg.skip_phases:
                result.phases_skipped.append(phase)
                continue

            try:
                created, modified = self._run_phase(
                    phase=phase,
                    cfg=cfg,
                    result=result,
                    analysis=analysis,
                    compat=compat,
                )
                result.files_created.extend(created)
                result.files_modified.extend(modified)
                result.phases_completed.append(phase)

                # Carry forward state from key phases
                if phase == "analyze":
                    analysis = result._analysis  # type: ignore[attr-defined]
                if phase == "validate-compatibility":
                    compat = result._compat  # type: ignore[attr-defined]

            except Exception as exc:
                result.phases_failed.append(phase)
                result.errors.append(f"[{phase}] {exc}")
                self._write_failed_marker(cfg, result)
                result.status = "PARTIAL" if result.phases_completed else "FAILED"
                result.span = {
                    "duration_ms": int(time.monotonic() * 1000) - start_ms,
                    "files_created": len(result.files_created),
                }
                return result

        # ── Write init marker ─────────────────────────────────────────────
        if not cfg.dry_run:
            self._write_success_marker(cfg, result, compat)

        result.compatibility = compat
        result.status = "SUCCESS"
        result.span = {
            "duration_ms": int(time.monotonic() * 1000) - start_ms,
            "files_created": len(result.files_created),
            "files_modified": len(result.files_modified),
        }
        return result

    # ── Phase dispatch ────────────────────────────────────────────────────

    def _run_phase(
        self,
        phase: str,
        cfg: RepoInitConfig,
        result: InitResult,
        analysis: Optional[AnalysisResult],
        compat: Optional[CompatibilityResult],
    ):
        """Dispatch to the correct phase function. Returns (created, modified)."""
        if phase == "analyze":
            a = analyze_repo(cfg.repo_root)
            result._analysis = a  # type: ignore[attr-defined]
            return [], []

        if phase == "generate-spec":
            assert analysis is not None
            created = generate_spec(cfg, analysis, dry_run=cfg.dry_run)
            return created, []

        if phase == "bootstrap-structure":
            assert analysis is not None
            created = bootstrap_structure(cfg, analysis, dry_run=cfg.dry_run)
            return created, []

        if phase == "housekeeping":
            created, modified = run_housekeeping(cfg, dry_run=cfg.dry_run)
            return created, modified

        if phase == "framework-bootstrap":
            created = framework_bootstrap(cfg, dry_run=cfg.dry_run)
            return created, []

        if phase == "validate-compatibility":
            c = validate_compatibility(cfg)
            result._compat = c  # type: ignore[attr-defined]
            result.warnings.extend(c.warnings)
            if c.hard_failures:
                raise RuntimeError(
                    f"Hard compatibility failures: {'; '.join(c.hard_failures)}"
                )
            return [], []

        if phase == "init-todo":
            assert analysis is not None
            created = init_todo(cfg, analysis, dry_run=cfg.dry_run)
            return created, []

        if phase == "generate-docs":
            assert analysis is not None
            created = generate_docs(cfg, analysis, dry_run=cfg.dry_run)
            return created, []

        raise ValueError(f"Unknown phase: {phase!r}")

    # ── Helpers ───────────────────────────────────────────────────────────

    def _preflight(self, cfg: RepoInitConfig) -> List[str]:
        """Run pre-flight guard checks. Return list of error strings."""
        errors: List[str] = []

        if not cfg.repo_root.is_dir():
            errors.append(f"repo_root does not exist: {cfg.repo_root}")
            return errors  # Can't proceed

        # Git check
        git_dir = cfg.repo_root / ".git"
        if not git_dir.is_dir():
            errors.append(
                f"{cfg.repo_root} is not a git repository. "
                "Run 'git init' first."
            )

        # Init marker check
        init_marker = cfg.repo_root / ".agentic-engineers" / "INIT-COMPLETE.yaml"
        if init_marker.exists() and not cfg.force_reinit and not cfg.resume:
            errors.append(
                f"Repository already initialized ({init_marker}). "
                "Pass force_reinit=True to overwrite."
            )

        return errors

    def _write_success_marker(
        self,
        cfg: RepoInitConfig,
        result: InitResult,
        compat: Optional[CompatibilityResult],
    ) -> None:
        """Write .agentic-engineers/INIT-COMPLETE.yaml."""
        import datetime
        import yaml  # type: ignore[import]

        marker_dir = cfg.repo_root / ".agentic-engineers"
        marker_dir.mkdir(parents=True, exist_ok=True)
        marker_path = marker_dir / "INIT-COMPLETE.yaml"

        data = {
            "status": "SUCCESS",
            "project_name": cfg.project_name,
            "framework_version": cfg.framework_version,
            "initialized_at": datetime.datetime.utcnow().isoformat() + "Z",
            "initialized_by": f"repo-init v{SKILL_VERSION}",
            "phases_completed": result.phases_completed,
            "files_created": len(result.files_created),
            "files_modified": len(result.files_modified),
            "warnings": len(result.warnings),
            "compatibility": {
                "harness": cfg.model_harness,
                "hard_failures": compat.hard_failures if compat else [],
                "warnings": compat.warnings if compat else [],
            },
        }
        marker_path.write_text(yaml.dump(data, default_flow_style=False))

    def _write_failed_marker(self, cfg: RepoInitConfig, result: InitResult) -> None:
        """Write .agentic-engineers/INIT-FAILED.yaml for resume support."""
        import datetime

        try:
            marker_dir = cfg.repo_root / ".agentic-engineers"
            marker_dir.mkdir(parents=True, exist_ok=True)
            marker_path = marker_dir / "INIT-FAILED.yaml"
            lines = [
                "status: FAILED",
                f"project_name: {cfg.project_name}",
                f"failed_at: {result.phases_failed[-1] if result.phases_failed else 'unknown'}",
                f"timestamp: {datetime.datetime.utcnow().isoformat()}Z",
                "completed_phases:",
            ]
            for phase in result.phases_completed:
                lines.append(f"  - {phase}")
            marker_path.write_text("\n".join(lines) + "\n")
        except Exception:
            pass  # Best-effort; don't mask original error


# ============================================================================
# CLI
# ============================================================================

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="repo_init",
        description="Initialize a repository with the agentic-engineers framework.",
    )
    p.add_argument("--repo-root", required=True, help="Path to target repository")
    p.add_argument("--project-name", default="", help="Project name (inferred if omitted)")
    p.add_argument("--project-description", default="", help="Project description")
    p.add_argument(
        "--model-harness",
        default="claude",
        choices=list(SUPPORTED_HARNESSES),
        help="Model harness to configure for",
    )
    p.add_argument("--framework-version", default="5.10", help="Framework version to pin")
    p.add_argument("--dry-run", action="store_true", help="Validate only, no writes")
    p.add_argument("--force-reinit", action="store_true", help="Overwrite existing init")
    p.add_argument("--resume", action="store_true", help="Resume from failed init")
    p.add_argument(
        "--skip-phases",
        default="",
        help="Comma-separated list of phases to skip",
    )
    return p


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    skip = [p.strip() for p in args.skip_phases.split(",") if p.strip()]

    cfg = RepoInitConfig(
        repo_root=Path(args.repo_root),
        project_name=args.project_name,
        project_description=args.project_description,
        model_harness=args.model_harness,
        framework_version=args.framework_version,
        dry_run=args.dry_run,
        force_reinit=args.force_reinit,
        resume=args.resume,
        skip_phases=skip,
    )

    initializer = RepoInitializer()
    result = initializer.run(cfg)
    print(result)
    return 0 if result.status in ("SUCCESS", "DRY_RUN") else 1


if __name__ == "__main__":
    sys.exit(main())
