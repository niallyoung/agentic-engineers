---
name: session-analyzer
description: >
  Analyzes session transcripts (DELEGATE/HANDBACK pairs, conversation history,
  execution metrics) to surface automation candidates, quality anomalies, drift
  patterns, and effort mismatches. Outputs a structured analysis.yaml report
  to ~/.agentic-engineers/sessions/{session-id}/ so findings are centralized,
  version-controlled, and consumable by other skills.
license: Proprietary
compatibility: agentic-engineers framework v5.10+. Requires Python 3.8+
metadata:
  author: agentic-engineers
  version: "0.1"  # PROPOSED — not yet implemented
  category: analysis
  role: model-engineer
  model: claude-haiku-4.5
  effort: medium
  thinking: false
  trigger: post-session | on-demand
  tdd_phase: RED  # tests specified, implementation pending
  dependencies:
    - queue-management   # read completed HANDBACKs from queue
    - usage-tracking     # pull per-task token/cost metrics
    - metrics-etl        # aggregate quality scores
---

# session-analyzer

## Purpose

During manual sessions, engineers repeatedly perform the same investigative
steps (doc audits, protocol checks, enum comparisons, artifact counts) that
could be automated. `session-analyzer` detects these patterns by reading the
session's DELEGATE/HANDBACK queue and conversation metadata, then emits a
structured `analysis.yaml` report that identifies:

1. **Automation candidates** — steps performed manually 2+ times → skill proposal
2. **Quality anomalies** — task types that consistently score below 0.80
3. **Drift detections** — configs/enums that changed during the session
4. **Effort mismatches** — tasks declared `low` but consumed `high` token budgets

## Layout

```
src/skills/session-analyzer/
├── SKILL.md
├── __init__.py
├── scripts/
│   ├── __init__.py
│   └── session_analyzer.py     # SessionAnalyzer, AnalysisReport, CLI
└── tests/
    ├── __init__.py
    └── test_session_analyzer.py
```

Output location (centralized, harness-agnostic):
```
~/.agentic-engineers/sessions/{session-id}/analysis.yaml
```

## Analysis Schema (analysis.yaml)

```yaml
session_id: "2026-06-13"
generated_at: "2026-06-13T22:00:00Z"
source_queue: "~/.agentic-engineers/local/2026-06-13-session/queue/"

automation_candidates:
  - pattern: "Manual HANDBACK enum drift check"
    occurrences: 3            # times this step appeared in session
    effort_minutes: 15        # estimated manual time consumed
    recommended_action: "Add to protocol-validator --check-enum-drift"
    priority: high

  - pattern: "Manual phantom reference grep (AutomationController)"
    occurrences: 2
    effort_minutes: 10
    recommended_action: "Add to doc-quality-monitor --check-phantom-references"
    priority: high

  - pattern: "Artifact count / pruning check (artifacts/ directory)"
    occurrences: 1
    effort_minutes: 5
    recommended_action: "New skill: artifact-pruner (scan, report, prune stale files)"
    priority: medium

quality_anomalies:
  - task_type: "doc_audit"
    avg_quality: 0.72
    sample_count: 4
    recommendation: "Route doc audits to security-engineer (higher baseline quality)"

drift_detections:
  - artifact: "HANDBACK status enum"
    files_drifted: 3
    canonical_source: "src/skills/protocol-validator/scripts/protocol_validator.py"
    fix_delegate_id: "2026-06-13-handback-enum-fix"

  - artifact: "AutomationController references in docs"
    files_affected: 8
    canonical_state: "class removed in PR #47"
    fix_delegate_id: "2026-06-13-phantom-ref-cleanup"

effort_mismatches:
  - task_id: "2026-06-13-skill-audit-enhancement"
    declared_effort: high
    actual_tokens: 28000
    estimated_effort: high
    verdict: match

session_summary:
  total_delegates: 7
  completed: 5
  pending: 2
  avg_quality: 0.84
  total_tokens: 145000
  total_cost_usd: 0.87
  top_automation_savings_minutes: 30
```

## CLI Interface

```bash
# Analyze the current session queue
python session_analyzer.py --session-id 2026-06-13 \
    --queue-path ~/.agentic-engineers/local/2026-06-13-session/queue/ \
    --output ~/.agentic-engineers/sessions/2026-06-13/analysis.yaml

# Quick scan (stdout only, no file write)
python session_analyzer.py --session-id 2026-06-13 --dry-run

# JSON output for pipeline integration
python session_analyzer.py --session-id 2026-06-13 --format json
```

## Integration Points

| Skill | Direction | Purpose |
|---|---|---|
| `queue-management` | read | Load completed DELEGATE/HANDBACK pairs |
| `usage-tracking` | read | Pull token/cost metrics per task_id |
| `metrics-etl` | read | Pull quality scores per task_id |
| `doc-quality-monitor` | downstream | Findings feed phantom_patterns registry |
| `protocol-validator` | downstream | Findings feed status enum drift registry |
| `consistency-checker` | downstream | Aggregated drift findings inform queue audit |

## Implementation Notes (for Engineer DELEGATE)

### Core classes to implement

```python
class SessionAnalyzer:
    def __init__(self, session_id: str, queue_path: Path, metrics_source: Optional[MetricsSource] = None): ...
    def load_completed_tasks(self) -> List[Dict]: ...           # from queue/done/
    def detect_automation_candidates(self) -> List[AutomationCandidate]: ...
    def detect_quality_anomalies(self) -> List[QualityAnomaly]: ...
    def detect_drift(self) -> List[DriftDetection]: ...
    def detect_effort_mismatches(self) -> List[EffortMismatch]: ...
    def run(self) -> AnalysisReport: ...

@dataclass
class AutomationCandidate:
    pattern: str
    occurrences: int
    effort_minutes: int
    recommended_action: str
    priority: str  # high | medium | low

@dataclass
class AnalysisReport:
    session_id: str
    generated_at: str
    automation_candidates: List[AutomationCandidate]
    quality_anomalies: List[QualityAnomaly]
    drift_detections: List[DriftDetection]
    effort_mismatches: List[EffortMismatch]
    session_summary: Dict
    def to_yaml(self) -> str: ...
    def write(self, path: Path) -> None: ...
```

### Pattern detection strategy

Automation candidates are identified by:
1. Scanning DELEGATE `scope` fields for common imperative verbs ("grep", "check", "scan", "count", "audit") applied to the same subject across multiple tasks
2. Counting manual steps reported in HANDBACK `output` free-text fields
3. Cross-referencing step descriptions against the existing skills index — if a step matches no skill, it's a candidate

### Effort estimate

- Implementation: 1–2 engineer-days (medium complexity)
- Tests: ~25 unit tests, 5 integration tests
- Dependencies: all stdlib + PyYAML (already present)
- Effort level for implementation DELEGATE: `medium`

## Test Specification (TDD RED-phase)

```python
class TestSessionAnalyzer:
    def test_loads_completed_tasks_from_done_queue(self, tmp_queue): ...
    def test_detects_repeated_manual_pattern(self): ...
    def test_automation_candidate_priority_classification(self): ...
    def test_quality_anomaly_threshold_0_80(self): ...
    def test_drift_detection_reads_enum_report(self): ...
    def test_effort_mismatch_tokens_vs_declared(self): ...
    def test_report_serializes_to_valid_yaml(self): ...
    def test_write_creates_output_file(self, tmp_path): ...
    def test_dry_run_no_file_written(self, tmp_path): ...
    def test_empty_queue_produces_empty_report(self): ...
```

## Priority

**HIGH** — this skill closes the loop on the session-improvement cycle. Without it,
session pattern recognition remains manual. Recommended as DELEGATE-002 output
after model-adaptability-config is designed.
