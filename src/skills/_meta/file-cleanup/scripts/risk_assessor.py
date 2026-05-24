# -*- coding: utf-8 -*-
"""
risk_assessor.py — Calculate risk levels for file deletions.

Risk scoring matrix (scale 0-100):
  0-30:   LOW     (confidence ~0.95)  → recommendation: DELETE
  31-59:  MEDIUM  (confidence ~0.75)  → recommendation: REVIEW
  60+:    HIGH    (confidence ~0.85)  → recommendation: KEEP or ARCHIVE

Risk factors (weighted):
  1. Active references (40%): 0 refs=0pts, 1-3 refs=20pts, 4+=40pts
  2. Hidden references (30%): 0=0pts, 1-2=10pts, 3+=30pts
  3. Git history (20%): recent=5pts, multi-branch=10pts, tags=10pts
  4. Age & frequency (10%): 50+ commits=10pts
"""

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .reference_scanner import Reference


@dataclass
class RiskScore:
    """Risk assessment for a file deletion."""

    score: int        # 0-100
    level: str        # LOW | MEDIUM | HIGH
    confidence: float # 0.0-1.0
    recommendation: str  # DELETE | REVIEW | KEEP | ARCHIVE
    reasoning: List[str] = field(default_factory=list)


class RiskAssessor:
    """Assesses deletion risk for files."""

    def __init__(self, root: Path) -> None:
        """Initialize risk assessor with repo root."""
        self.root = Path(root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def assess_deletion_risk(self, file_path: Path, references: List[Reference]) -> RiskScore:
        """
        Assess risk of deleting a file.
        
        Args:
            file_path: Path to the file being considered for deletion
            references: List of references found to this file
        
        Returns:
            RiskScore with level, confidence, and recommendation
        """
        factors: List[str] = []

        # Factor 1: Active references (40 pts max)
        ref_score = self._score_active_references(len(references))
        factors.append(f"References: {ref_score:.0f}pts")

        # Factor 2: Hidden references (30 pts max)
        hidden_count = sum(1 for r in references if r.ref_type in ("string", "fstring", "subprocess"))
        hidden_score = self._score_hidden_references(hidden_count)
        factors.append(f"Hidden refs: {hidden_score:.0f}pts")

        # Factor 3: Git history (20 pts max)
        git_score = self._score_git_history(file_path)
        factors.append(f"Git history: {git_score:.0f}pts")

        # Factor 4: Age and frequency (10 pts max)
        age_score = self._score_age_and_frequency(file_path)
        factors.append(f"Age/frequency: {age_score:.0f}pts")

        score = int(min(100, ref_score + hidden_score + git_score + age_score))

        # Categorize
        if score <= 30:
            level = "LOW"
            confidence = 0.95
            recommendation = "DELETE"
        elif score <= 59:
            level = "MEDIUM"
            confidence = 0.75
            recommendation = "REVIEW"
        else:
            level = "HIGH"
            confidence = 0.85
            recommendation = "KEEP"

        return RiskScore(
            score=score,
            level=level,
            confidence=confidence,
            recommendation=recommendation,
            reasoning=factors,
        )

    # ------------------------------------------------------------------
    # Scoring sub-factors
    # ------------------------------------------------------------------

    def _score_active_references(self, count: int) -> float:
        """Score based on number of active references (0-40)."""
        if count == 0:
            return 0.0
        elif count <= 3:
            return 20.0
        else:
            return 40.0

    def _score_hidden_references(self, count: int) -> float:
        """Score based on hidden references (0-30)."""
        if count == 0:
            return 0.0
        elif count <= 2:
            return 10.0
        else:
            return 30.0

    def _score_git_history(self, file_path: Path) -> float:
        """Score based on git history (0-40)."""
        score = 0.0

        if self._is_recently_modified(file_path):
            score += 5.0
        if self._appears_in_multiple_branches(file_path):
            score += 10.0
        if self._appears_in_git_tags(file_path):
            score += 10.0

        return score

    def _score_age_and_frequency(self, file_path: Path) -> float:
        """Score based on age and modification frequency (0-10)."""
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", str(file_path.relative_to(self.root))],
                capture_output=True,
                text=True,
                cwd=str(self.root),
            )
            commit_count = len([l for l in result.stdout.splitlines() if l.strip()])
            if commit_count >= 50:
                return 10.0
            elif commit_count >= 10:
                return 5.0
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
        return 0.0

    def _is_recently_modified(self, file_path: Path) -> bool:
        """Check if file was modified in the last 7 days."""
        full_path = self.root / file_path if not file_path.is_absolute() else file_path
        try:
            mod_time = full_path.stat().st_mtime
            now = time.time()
            days_old = (now - mod_time) / 86400
            return days_old <= 7
        except OSError:
            return False

    def _appears_in_multiple_branches(self, file_path: Path) -> bool:
        """Check if file appears in multiple git branches."""
        try:
            result = subprocess.run(
                ["git", "branch", "--contains"],
                capture_output=True,
                text=True,
                cwd=str(self.root),
            )
            branches = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            return len(branches) > 1
        except (OSError, subprocess.SubprocessError):
            return False

    def _appears_in_git_tags(self, file_path: Path) -> bool:
        """Check if file appears in any git tags."""
        try:
            result = subprocess.run(
                ["git", "tag"],
                capture_output=True,
                text=True,
                cwd=str(self.root),
            )
            tags = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            return len(tags) > 0
        except (OSError, subprocess.SubprocessError):
            return False
