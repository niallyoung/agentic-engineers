---
name: workflow-review
description: Validates end-to-end delegation workflows for correctness. Generates ASCII workflow diagrams showing agent data flow. Checks for missing quality gates, incomplete feedback loops, blocked exit criteria, and unused components.
license: Proprietary
compatibility: agentic-engineers framework v5.10+. Requires Python 3.8+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: validation
  role: quality-engineer
  model: claude-sonnet-4.6
  effort: medium
  thinking: false
  dependencies:
    - consistency-checker
---

# workflow-review

## Overview

Workflow-Review skill validates end-to-end delegation workflows for correctness across the
agentic-engineers framework. It parses the `FRAMEWORK-MANIFEST.yaml` to understand the full
agent topology, generates visual ASCII diagrams of agent data flow, and performs a suite of
consistency checks to detect structural issues.

**What it does:**

1. **Manifest Parsing** — Reads `config/FRAMEWORK-MANIFEST.yaml` to discover all agents and skills
2. **ASCII Diagram Generation** — Produces a readable workflow diagram showing DELEGATE/HANDBACK flows
3. **Consistency Checking** — Runs 6 structural checks covering quality gates, orchestrator presence,
   feedback loops, cycles, agent documentation, and SKILL.md markers
4. **Cycle Detection** — Detects circular delegation chains using DFS traversal
5. **Quality Scoring** — Produces a 0–100 quality score and pass/fail decision (threshold: 70)
6. **Recommendations** — Generates actionable improvement suggestions based on failed checks

**Why it matters:**

- **Workflow Integrity** — Ensures every delegation chain has a corresponding HANDBACK path
- **Quality Gate Enforcement** — Prevents workflows from bypassing quality review
- **Visual Documentation** — ASCII diagrams serve as living documentation of agent topology
- **CI Integration** — Runs as a GitHub Actions gate on workflow-related branches
- **Framework Health** — Provides an objective quality score for the overall agent framework

---

## CLI Usage

```bash
# Run full workflow review (uses default manifest path)
python3 src/skills/workflow-review/scripts/workflow_review.py config/FRAMEWORK-MANIFEST.yaml
```

---

## Programmatic Usage

```python
import importlib.util
from pathlib import Path

skill_script = Path("src/skills/workflow-review/scripts/workflow_review.py")
spec = importlib.util.spec_from_file_location("workflow_review", skill_script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

WorkflowReviewer = module.WorkflowReviewer

reviewer = WorkflowReviewer(Path("config/FRAMEWORK-MANIFEST.yaml"))
report = reviewer.review()
print(report.diagram)
print(f"Quality Score: {report.quality_score:.1f}/100")
print(f"Status: {'PASS' if report.passed else 'FAIL'}")
```

---

## Report Format

### WorkflowReport Dataclass

```python
@dataclass
class WorkflowReport:
    timestamp: str               # ISO 8601
    diagram: str                 # ASCII workflow diagram
    consistency_checklist: dict  # {passed: [...], failed: [...], warnings: [...]}
    cycles_detected: list        # Cycle path strings
    unused_agents: list          # Agents not referenced in active workflows
    missing_quality_gates: list  # Phases lacking validation
    recommendations: list        # Actionable improvement suggestions
    quality_score: float         # 0–100
    passed: bool                 # quality_score >= 70
```

### Quality Score Calculation

- Start at **100**
- Deduct **15** per failed consistency check
- Deduct **5** per warning
- Clamp to **0–100**
- **passed** = `quality_score >= 70`

---

## Consistency Checks

| Check | Description | Failure Impact |
|-------|-------------|----------------|
| `has_quality_gates` | Validation-type agent exists | -15 |
| `has_orchestrator` | Orchestrator agent present | -15 |
| `has_feedback_loops` | HANDBACK paths can complete | -15 |
| `no_circular_chains` | No delegation cycles | -15 |
| `agents_documented` | All agents have descriptions | -15 |
| `skills_have_skill_md` | All manifest skills have SKILL.md | -15 |

---

## Testing

### Example Test Names

```python
def test_workflow_report_dataclass_fields(): ...
def test_reviewer_initialization(): ...
def test_generate_diagram_returns_string(): ...
def test_generate_diagram_contains_box_chars(): ...
def test_check_consistency_returns_dict(): ...
def test_detect_cycles_returns_list(): ...
def test_review_returns_workflow_report(): ...
def test_quality_score_range(): ...
def test_passed_is_bool(): ...
def test_orchestrator_passes_has_orchestrator_check(): ...
def test_quality_agent_passes_has_quality_gates(): ...
def test_missing_skills_section_handled_gracefully(): ...
def test_cycle_detection_with_known_cycle(): ...
def test_quality_score_healthy_manifest(): ...
```

---

## References

- `config/FRAMEWORK-MANIFEST.yaml` — Agent and skill registry
- `src/skills/consistency-checker/` — Protocol queue consistency
- `docs/SKILLS-AVAILABLE.md` — Skill index
- `.github/workflows/framework-integrity.yml` — CI gate integration

---

## Version History

### v1.0 (Current)
- Initial release with manifest parsing, ASCII diagram, 6 consistency checks, cycle detection

## Self-Improvement

This skill participates in the framework's continuous improvement cycle
(see [skill-improvement-feedback](../skill-improvement-feedback/SKILL.md)).

When you use **workflow-review** during a task, include a skill_feedback entry
in your HANDBACK to help improve it over time:

```yaml
skill_feedback:
  - skill_name: workflow-review
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
