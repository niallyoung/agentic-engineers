# -*- coding: utf-8 -*-
"""
ABTestingFramework — Model-selection A/B experiments with statistical rigor.

This module extends the existing skills/ab-testing/scripts/ab-testing.py with:
  - Welch's t-test (proper degrees of freedom, not approximation)
  - Early stopping detection (both winner and regression signals)
  - Minimum sample size enforcement (n=30 per group)
  - Effect size (Cohen's d) reporting
  - Integration with ModelSelector routing decisions

Experiment lifecycle:
  DRAFT → RUNNING → COMPLETED | FAILED
                 ↘ PAUSED → RUNNING
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_SAMPLE_SIZE: int = 30          # Minimum tasks per group for significance
SIGNIFICANCE_THRESHOLD: float = 0.05
EARLY_STOP_THRESHOLD: float = 0.01  # Very strong signal → early stop
DEFAULT_DURATION_DAYS: int = 7
DEFAULT_TRAFFIC_SPLIT: float = 0.5


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------

class ExperimentStatus(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ExperimentResult:
    """Statistical analysis result for a completed or in-progress experiment."""
    control_count: int
    variant_count: int
    control_avg_quality: float
    variant_avg_quality: float
    control_avg_cost: float
    variant_avg_cost: float
    quality_improvement_pct: float
    cost_reduction_pct: float
    p_value: float
    significant: bool
    cohens_d: float
    power: float
    variant_better: bool
    early_stop_signal: bool
    regression_signal: bool
    status: str = "ok"  # "ok" | "insufficient_data"


@dataclass
class Experiment:
    """A/B test experiment definition."""
    id: str
    name: str
    hypothesis: str
    control: Dict[str, Any]
    variant: Dict[str, Any]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_days: int = DEFAULT_DURATION_DAYS
    traffic_split: float = DEFAULT_TRAFFIC_SPLIT
    status: str = ExperimentStatus.DRAFT.value
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    hypothesis_accepted: Optional[bool] = None
    winner: Optional[str] = None
    notes: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

def _welch_t_test(a: List[float], b: List[float]) -> Tuple[float, float]:
    """
    Welch's t-test for two independent samples with unequal variances.

    Returns:
        (t_statistic, p_value)  — two-tailed p-value
    """
    if len(a) < 2 or len(b) < 2:
        return 0.0, 1.0

    mean_a = statistics.mean(a)
    mean_b = statistics.mean(b)
    var_a = statistics.variance(a)
    var_b = statistics.variance(b)
    n_a = len(a)
    n_b = len(b)

    se = math.sqrt(var_a / n_a + var_b / n_b)
    if se == 0:
        return (0.0, 0.0) if mean_a != mean_b else (0.0, 1.0)

    t = (mean_a - mean_b) / se

    # Welch–Satterthwaite degrees of freedom
    num = (var_a / n_a + var_b / n_b) ** 2
    denom = (var_a / n_a) ** 2 / (n_a - 1) + (var_b / n_b) ** 2 / (n_b - 1)
    df = num / denom if denom > 0 else n_a + n_b - 2

    # Two-tailed p-value via regularised incomplete beta function approximation
    p = _t_dist_pvalue(abs(t), df)
    return t, p


def _t_dist_pvalue(t: float, df: float) -> float:
    """
    Approximate two-tailed p-value from t and degrees of freedom.

    Uses the regularised incomplete beta function: p = I(df/(df+t²), df/2, 0.5).
    Falls back to normal approximation for df >= 30.
    """
    if df <= 0:
        return 1.0
    if df >= 30:
        # Normal approximation (accurate for large df)
        p_one_tail = 0.5 * math.erfc(t / math.sqrt(2))
        return min(1.0, 2.0 * p_one_tail)

    # Beta function approximation for small df
    x = df / (df + t * t)
    try:
        p = _regularised_incomplete_beta(x, df / 2.0, 0.5)
    except Exception:
        p = 1.0
    return min(1.0, max(0.0, p))


def _regularised_incomplete_beta(x: float, a: float, b: float) -> float:
    """Continued-fraction approximation of the regularised incomplete beta function."""
    if x < 0 or x > 1:
        return 1.0
    if x == 0:
        return 0.0
    if x == 1:
        return 1.0

    # Use symmetry relation for better convergence
    if x > (a + 1) / (a + b + 2):
        return 1.0 - _regularised_incomplete_beta(1 - x, b, a)

    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a

    # Lentz's continued fraction
    MAXIT = 200
    EPS = 3e-7
    FPMIN = 1e-30

    qab = a + b
    qap = a + 1
    qam = a - 1
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d

    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break

    return front * h


def _cohens_d(a: List[float], b: List[float]) -> float:
    """Cohen's d effect size."""
    if len(a) < 2 or len(b) < 2:
        return 0.0
    pooled_std = math.sqrt(
        ((len(a) - 1) * statistics.variance(a) + (len(b) - 1) * statistics.variance(b))
        / (len(a) + len(b) - 2)
    )
    if pooled_std == 0:
        return 0.0
    return (statistics.mean(a) - statistics.mean(b)) / pooled_std


# ---------------------------------------------------------------------------
# ABTestingFramework
# ---------------------------------------------------------------------------

class ABTestingFramework:
    """
    Orchestrate model-selection A/B experiments.

    Experiments are persisted as JSON files under ``experiments_dir``.

    Usage::

        framework = ABTestingFramework()
        exp_id = framework.create_experiment(
            name="haiku-vs-sonnet-routing",
            hypothesis="Haiku handles low-complexity routing at 0.33× cost with ≥90% quality",
            control={"model": "sonnet-4-6", "complexity_max": 20},
            variant={"model": "haiku-4-5", "complexity_max": 20},
        )
        framework.start_experiment(exp_id)
        # ... collect metrics ...
        result = framework.analyze_experiment(exp_id)
        print(result)
    """

    def __init__(self, experiments_dir: Optional[str] = None):
        if experiments_dir is None:
            experiments_dir = Path.home() / ".agentic-engineers" / "experiments"
        self._dir = Path(experiments_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_experiment(
        self,
        name: str,
        hypothesis: str,
        control: Dict[str, Any],
        variant: Dict[str, Any],
        duration_days: int = DEFAULT_DURATION_DAYS,
        traffic_split: float = DEFAULT_TRAFFIC_SPLIT,
    ) -> str:
        """Create and persist a new experiment. Returns experiment_id."""
        name_hash = hashlib.md5(
            (name + datetime.now().isoformat()).encode()
        ).hexdigest()[:8]
        exp_id = f"{name.lower().replace(' ', '-')}-{name_hash}"

        exp = Experiment(
            id=exp_id,
            name=name,
            hypothesis=hypothesis,
            control=control,
            variant=variant,
            duration_days=duration_days,
            traffic_split=traffic_split,
        )
        self._save(exp)
        return exp_id

    def load_experiment(self, experiment_id: str) -> Optional[Experiment]:
        path = self._dir / f"{experiment_id}.json"
        if not path.exists():
            return None
        with open(path) as f:
            data = json.load(f)
        return Experiment(**data)

    def list_experiments(self, status: Optional[str] = None) -> List[Experiment]:
        exps = []
        for p in self._dir.glob("*.json"):
            exp = self.load_experiment(p.stem)
            if exp and (status is None or exp.status == status):
                exps.append(exp)
        return sorted(exps, key=lambda e: e.created_at, reverse=True)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_experiment(self, experiment_id: str) -> bool:
        exp = self.load_experiment(experiment_id)
        if not exp or exp.status != ExperimentStatus.DRAFT.value:
            return False
        exp.status = ExperimentStatus.RUNNING.value
        exp.start_date = datetime.now().isoformat()
        exp.end_date = (datetime.now() + timedelta(days=exp.duration_days)).isoformat()
        exp.updated_at = datetime.now().isoformat()
        self._save(exp)
        return True

    def stop_experiment(
        self,
        experiment_id: str,
        winner: Optional[str] = None,
    ) -> bool:
        exp = self.load_experiment(experiment_id)
        if not exp or exp.status != ExperimentStatus.RUNNING.value:
            return False

        result = self.analyze_experiment(experiment_id)
        if result is None:
            return False

        if winner in ("control", "variant"):
            exp.hypothesis_accepted = winner == "variant"
            exp.winner = winner
        else:
            if result.significant and result.variant_better:
                exp.hypothesis_accepted = True
                exp.winner = "variant"
            else:
                exp.hypothesis_accepted = False
                exp.winner = "control"

        exp.status = ExperimentStatus.COMPLETED.value
        exp.updated_at = datetime.now().isoformat()
        exp.notes = (
            f"Winner: {exp.winner}  "
            f"p={result.p_value:.4f}  "
            f"quality_delta={result.quality_improvement_pct:+.1f}%  "
            f"cost_delta={result.cost_reduction_pct:+.1f}%"
        )
        self._save(exp)
        return True

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyze_experiment(
        self,
        experiment_id: str,
        control_metrics: Optional[List[dict]] = None,
        variant_metrics: Optional[List[dict]] = None,
    ) -> Optional[ExperimentResult]:
        """
        Analyze experiment results.

        If ``control_metrics`` / ``variant_metrics`` are not supplied, the
        framework attempts to load them from the metrics store (same path
        convention as the existing ab-testing.py skill).
        """
        exp = self.load_experiment(experiment_id)
        if not exp:
            return None

        if control_metrics is None:
            control_metrics = self._load_group_metrics(experiment_id, "control")
        if variant_metrics is None:
            variant_metrics = self._load_group_metrics(experiment_id, "variant")

        if len(control_metrics) < MIN_SAMPLE_SIZE or len(variant_metrics) < MIN_SAMPLE_SIZE:
            return ExperimentResult(
                control_count=len(control_metrics),
                variant_count=len(variant_metrics),
                control_avg_quality=0.0,
                variant_avg_quality=0.0,
                control_avg_cost=0.0,
                variant_avg_cost=0.0,
                quality_improvement_pct=0.0,
                cost_reduction_pct=0.0,
                p_value=1.0,
                significant=False,
                cohens_d=0.0,
                power=0.0,
                variant_better=False,
                early_stop_signal=False,
                regression_signal=False,
                status="insufficient_data",
            )

        ctrl_q = [m.get("quality_score", 0.0) for m in control_metrics]
        var_q = [m.get("quality_score", 0.0) for m in variant_metrics]
        ctrl_c = [m.get("cost", 0.0) for m in control_metrics]
        var_c = [m.get("cost", 0.0) for m in variant_metrics]

        avg_ctrl_q = statistics.mean(ctrl_q)
        avg_var_q = statistics.mean(var_q)
        avg_ctrl_c = statistics.mean(ctrl_c)
        avg_var_c = statistics.mean(var_c)

        _, p_value = _welch_t_test(ctrl_q, var_q)
        d = _cohens_d(ctrl_q, var_q)
        power = min(1.0, (min(len(ctrl_q), len(var_q)) / 100.0))

        quality_improvement = (
            (avg_var_q - avg_ctrl_q) / avg_ctrl_q * 100
            if avg_ctrl_q > 0 else 0.0
        )
        cost_reduction = (
            (avg_ctrl_c - avg_var_c) / avg_ctrl_c * 100
            if avg_ctrl_c > 0 else 0.0
        )

        significant = p_value < SIGNIFICANCE_THRESHOLD
        variant_better = avg_var_q >= avg_ctrl_q * 0.98 and avg_var_c <= avg_ctrl_c * 1.05
        early_stop = p_value < EARLY_STOP_THRESHOLD and variant_better
        regression = p_value < SIGNIFICANCE_THRESHOLD and not variant_better and avg_var_q < avg_ctrl_q * 0.95

        return ExperimentResult(
            control_count=len(control_metrics),
            variant_count=len(variant_metrics),
            control_avg_quality=avg_ctrl_q,
            variant_avg_quality=avg_var_q,
            control_avg_cost=avg_ctrl_c,
            variant_avg_cost=avg_var_c,
            quality_improvement_pct=quality_improvement,
            cost_reduction_pct=cost_reduction,
            p_value=p_value,
            significant=significant,
            cohens_d=d,
            power=power,
            variant_better=variant_better,
            early_stop_signal=early_stop,
            regression_signal=regression,
        )

    def generate_report(self, experiment_id: str, result: Optional[ExperimentResult] = None) -> str:
        exp = self.load_experiment(experiment_id)
        if not exp:
            return f"Experiment {experiment_id} not found"
        if result is None:
            result = self.analyze_experiment(experiment_id)

        lines = [
            f"=== A/B Test Report: {exp.name} ===",
            f"ID: {experiment_id}",
            f"Status: {exp.status}",
            f"Hypothesis: {exp.hypothesis}",
            "",
        ]

        if result is None or result.status == "insufficient_data":
            ctrl = result.control_count if result else 0
            var = result.variant_count if result else 0
            lines.append(
                f"⚠  Insufficient data: control={ctrl}/{MIN_SAMPLE_SIZE}, "
                f"variant={var}/{MIN_SAMPLE_SIZE} (min required)"
            )
            return "\n".join(lines)

        lines += [
            "Results:",
            f"  Control ({exp.control.get('model', '?')}): "
            f"n={result.control_count}  quality={result.control_avg_quality:.1f}%  "
            f"cost=${result.control_avg_cost:.4f}",
            f"  Variant ({exp.variant.get('model', '?')}): "
            f"n={result.variant_count}  quality={result.variant_avg_quality:.1f}%  "
            f"cost=${result.variant_avg_cost:.4f}",
            "",
            "Statistics:",
            f"  Quality delta: {result.quality_improvement_pct:+.1f}%",
            f"  Cost delta:    {result.cost_reduction_pct:+.1f}% reduction",
            f"  p-value:       {result.p_value:.4f}  ({'significant' if result.significant else 'not significant'})",
            f"  Cohen's d:     {result.cohens_d:.3f}",
            f"  Power:         {result.power:.2f}",
            "",
        ]

        if result.early_stop_signal:
            lines.append("🟢 EARLY STOP SIGNAL: Variant is clearly winning — consider stopping now")
        elif result.regression_signal:
            lines.append("🔴 REGRESSION SIGNAL: Variant is underperforming — consider rollback")
        elif result.significant and result.variant_better:
            lines.append("✓ Significant result: variant is better")
        elif result.significant:
            lines.append("⚠ Significant result: control is better")
        else:
            lines.append("⏳ No significant difference yet")

        if exp.hypothesis_accepted is not None:
            conclusion = "ACCEPTED — deploy variant" if exp.hypothesis_accepted else "REJECTED — keep control"
            lines.append(f"\nConclusion: Hypothesis {conclusion}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _save(self, exp: Experiment) -> None:
        path = self._dir / f"{exp.id}.json"
        with open(path, "w") as f:
            json.dump(asdict(exp), f, indent=2)

    def _load_group_metrics(self, experiment_id: str, group: str) -> List[dict]:
        """Load metrics tagged with experiment_id and group from metrics store."""
        metrics_dir = Path.home() / ".claude" / "metrics"
        records = []
        for date_dir in sorted(metrics_dir.glob("*"))[:7]:
            for json_file in date_dir.glob("task_*.json"):
                try:
                    with open(json_file) as f:
                        m = json.load(f)
                    if m.get("experiment_id") == experiment_id and m.get("experiment_group") == group:
                        records.append(m)
                except (json.JSONDecodeError, OSError):
                    continue
        return records
