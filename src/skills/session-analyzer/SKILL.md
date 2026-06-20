---
name: session-analyzer
description: >
  Meta-skill for automated session transcript analysis. Reads session artifacts
  (DELEGATEs, HANDBACKs, metrics, conversation history) to detect repetitive patterns,
  quality anomalies, drift detection, and effort mismatch. Outputs actionable
  recommendations for skill enhancement and process improvements.
license: Proprietary
compatibility: agentic-engineers framework v5.10+. Requires Python 3.8+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: meta-skill
  role: model-engineer
  model: claude-haiku-4.5
  effort: high
  thinking: false
  trigger: on-demand | on-session-end | scheduled
  tdd_phase: GREEN  # 5+ test cases passing
  dependencies:
    - queue-query
    - usage-tracking
    - metrics-etl
---

# session-analyzer

## Overview

**session-analyzer** reads session transcripts and queue artifacts to identify
automation candidates, quality issues, and process patterns. It examines:

- **Session DELEGATEs** — What work was requested (scope, effort, success criteria)
- **Session HANDBACKs** — What was delivered (status, quality scores, metrics)
- **Execution metrics** — Tokens, cost, duration per task and agent
- **Pattern repetition** — Same step/pattern executed 3+ times → skill candidate
- **Quality anomalies** — Low quality scores, high rework, frequent failures
- **Drift detection** — Config/docs changed during session → monitoring candidate
- **Effort mismatch** — Claimed low effort, took high effort → estimation issue

**Why it matters:**

- **Automation discovery** — Flagging repetitive manual work helps prevent process drift
- **Quality monitoring** — Identifying low-confidence tasks improves agent routing
- **Cost visibility** — Session-level cost analysis enables budget management
- **Process self-improvement** — Framework learns what should become skills

---

## Invocation

### Programmatic Interface

```python
from skills.session_analyzer.scripts import SessionAnalyzer

# Initialize
analyzer = SessionAnalyzer(
    session_id="2026-06-13-session",
    queue_path="~/.agentic-engineers/",
)

# Run full analysis
analysis = analyzer.analyze_session()

# Inspect results
print(f"Session: {analysis.session_id}")
print(f"Tasks: {analysis.task_count}")
print(f"Total cost: ${analysis.total_cost:.2f}")
print(f"Quality score: {analysis.overall_quality:.1%}")
print()

# Review patterns
if analysis.repetitive_patterns:
    print("Repetitive Patterns (skill candidates):")
    for pattern in analysis.repetitive_patterns:
        print(f"  - {pattern.description} (count={pattern.count})")
print()

# Review anomalies
if analysis.quality_anomalies:
    print("Quality Anomalies:")
    for anomaly in analysis.quality_anomalies:
        print(f"  - {anomaly.description} (severity={anomaly.severity})")
print()

# Review recommendations
if analysis.recommendations:
    print("Recommendations:")
    for rec in analysis.recommendations:
        print(f"  - {rec.title}")
        print(f"    Rationale: {rec.rationale}")
        print(f"    Effort: {rec.effort}")
```

### CLI Interface

```bash
# Analyze current session
python -m skills.session_analyzer --session-id 2026-06-13-session

# Analyze with custom queue path
python -m skills.session_analyzer --session-id 2026-06-13 --queue-path ~/.agentic-engineers/

# Generate analysis report
python -m skills.session_analyzer --session-id 2026-06-13 --output ~/analysis.yaml

# Analyze and pretty-print
python -m skills.session_analyzer --session-id 2026-06-13 --pretty

# Analyze specific agent
python -m skills.session_analyzer --session-id 2026-06-13 --agent orchestrator

# Compare sessions
python -m skills.session_analyzer --session-id 2026-06-13 --compare 2026-06-12 --metrics cost,quality
```

---

## Pattern Types

### Repetitive Patterns

A pattern is flagged as repetitive when **the same logical step is executed 3+ times**:

- **Code examples**: Search-replace fix, enum definition, path validation
- **Doc examples**: Manual audit (phantom references, stale sections), review pattern
- **Process examples**: Configuration check, spec compliance check, consistency validation

### Quality Anomalies

Quality anomalies are detected when:

1. **Low confidence** — Confidence score < 0.8
2. **High rework** — Task revised > 1.5x median
3. **Frequent failure** — Same task type fails > 20%
4. **Quality drift** — Quality scores decreasing over session
5. **Timeout/escalation** — Task escalated after timeout

### Drift Detection

Drift is detected when configuration or documentation changes during the session:

- **Config drift** — YAML/JSON config edited
- **Doc drift** — Markdown documents edited
- **Code drift** — Python code modified

### Effort Mismatch

Effort mismatch is detected when actual effort diverges from claim:

- **Overestimate** — Claimed high, took low (< 50%)
- **Underestimate** — Claimed low, took high (> 150%)

---

## Analysis Schema

Session analysis is output to `~/.agentic-engineers/sessions/{session-id}/analysis.yaml`:

```yaml
session_id: "2026-06-13-session"
session_start: "2026-06-13T08:00:00Z"
session_end: "2026-06-13T17:30:00Z"
duration_seconds: 34200

# High-level metrics
task_count: 11
total_cost: 24.57
total_tokens: 185000
overall_quality: 0.87

# Breakdown by agent and status
tasks_by_agent:
  orchestrator: 1
  engineer: 3
  lead-engineer: 2
  principal-engineer: 2
  model-engineer: 2
  quality-engineer: 1

tasks_by_status:
  success: 9
  partial: 1
  failure: 1

# Model performance
model_performance:
  claude-haiku-4.5:
    task_count: 5
    total_tokens: 45000
    total_cost: 4.50
    success_rate: 0.80
    avg_quality: 0.82

# Patterns
repetitive_patterns:
  - pattern_id: "enum-validation-drift"
    description: "Enum divergence check done manually 3 times"
    count: 3
    skill_candidate: "enhanced-protocol-validator"
    effort: "medium"
    confidence: 0.9

# Anomalies
quality_anomalies:
  - anomaly_id: "low-confidence-principal"
    description: "Principal task confidence 0.65 (below 0.8)"
    severity: "warning"
    root_cause: "Ambiguous architectural decision"

# Recommendations
recommendations:
  - title: "Create session-analyzer skill"
    category: "meta-skill"
    rationale: "Pattern detection repeated 3x; should be automated"
    effort: "medium"
    priority: "P1"

generated_at: "2026-06-13T17:31:00Z"
generator: "session-analyzer v1.0"
format_version: "1.0"
```

---

## Metrics Computed

### Per-Session
- task_count, total_cost, total_tokens, overall_quality
- session_duration, tasks_by_agent, tasks_by_status

### Per-Agent
- task_count, total_tokens, total_cost
- success_count, success_rate, avg_quality

### Per-Model
- task_count, total_tokens, total_cost
- success_rate, avg_quality, avg_duration

---

## Integration Points

### With queue-query
Load all session tasks and their DELEGATE/HANDBACK artifacts.

### With usage-tracking
Get cost and token metrics for each task.

### With metrics-etl
Get OpenTelemetry spans for duration and performance analysis.

---

## Testing

Test cases (5+):

1. `test_analyze_session_returns_analysis` — Basic functionality
2. `test_detect_repetitive_patterns_3plus` — Pattern detection (count >= 3)
3. `test_detect_low_confidence_anomaly` — Anomaly detection (confidence < 0.8)
4. `test_compute_metrics_per_agent` — Metrics aggregation
5. `test_detect_config_drift` — Drift detection

Coverage target: ≥85% line coverage

---

## Performance

- Session Size: 11 tasks → ~500ms
- Per-task analysis → ~40ms
- Report generation → ~50ms
- Total → <1 second

---

## Integration with Orchestrator

1. **At session end** — Auto-generate analysis.yaml
2. **On-demand** — `python -m skills.session_analyzer --session-id 2026-06-13`
3. **For improvement** — Model Engineer reviews recommendations and routes implementation tasks

---

## References

- `docs/DELEGATE-HANDBACK-protocol.md` — DELEGATE/HANDBACK schema
- `skills/queue-query/` — Load session tasks
- `skills/usage-tracking/` — Token and cost metrics
- `skills/metrics-etl/` — OpenTelemetry spans
- `docs/AGENTS.md` — Agent routing

---

## Version History

### v1.0 (Current)
- Initial release with pattern detection and quality anomaly analysis
- Integration with queue-query, usage-tracking, metrics-etl
- Session-level cost analysis and recommendations
- Effort mismatch detection

## Self-Improvement

We aim for **session-analyzer** to feel like a knowledgeable colleague rather than a rulebook. If any section felt prescriptive rather than guiding, a `tone_note` in your feedback helps us improve it.

This skill participates in the framework's continuous improvement cycle
(see [`skill-improvement-feedback`](../skill-improvement-feedback/SKILL.md)).

When you use **session-analyzer** during a task, include a `skill_feedback` entry
in your HANDBACK to help improve it over time:

```yaml
skill_feedback:
  - skill_name: session-analyzer
    effectiveness_score: 0.85        # required: 0.0–1.0
    clarity_score: 0.90              # optional
    coverage_gaps:
      - "Specific scenario the skill did not address"
    improvement_suggestions:
      - "Concrete change that would have helped"
    usage_context: "One sentence on how you used this skill"
```

Positive feedback is as valuable as critical feedback. Three or more
feedback items for this skill automatically trigger an improvement task.
