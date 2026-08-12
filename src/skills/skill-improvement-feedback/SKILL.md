---
name: skill-improvement-feedback
description: >
  Canonical pattern definition for the skill self-improvement feedback loop.
  Defines how agents emit structured skill_feedback in HANDBACKs, what fields
  are expected, and how feedback accumulates into improvement tasks. Every other
  skill references this as the single source of truth for its ## Self-Improvement
  section.
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: meta-skill
  role: orchestrator
  model: claude-haiku-4.5
  effort: low
  thinking: false
  trigger: on-demand
  tdd_phase: GREEN
  dependencies: []
---

# skill-improvement-feedback

## Overview

**skill-improvement-feedback** defines how every skill in agentic-engineers
participates in continuous self-improvement. When an agent uses a skill, it
can include a `skill_feedback` block in its HANDBACK. Feedback accumulates
automatically. When three or more items exist for a single skill, the
orchestrator spawns an improvement task to a senior-engineer.

**Goal over rule:** Skills aspire to make their users effective, not to
enforce compliance. We describe what good looks like rather than forbidding
specific actions. Feedback tells us where skills fall short of that aspiration.

## The `skill_feedback` Block

Include this in a HANDBACK when a skill made a material difference to the
task outcome — positive or negative. All fields except `skill_name` and
`effectiveness_score` are optional.

```yaml
skill_feedback:
  - skill_name: <kebab-case-skill-name>
    effectiveness_score: 0.0-1.0      # required
    clarity_score: 0.0-1.0            # optional
    coverage_gaps:
      - "<specific scenario not covered>"
    improvement_suggestions:
      - "<concrete actionable suggestion>"
    usage_context: "<one sentence>"
    tone_note: "<note if language felt prescriptive>"
```

## Accumulation and Routing

- `FeedbackLoop.record_from_handback()` extracts `skill_feedback` and persists
  raw items to `artifacts/metrics/skill-feedback/<skill-name>.jsonl`
- `OrchestratorSkill._route_skill_feedback()` checks accumulation counts
- **Threshold:** ≥ 3 items for one skill → spawn DELEGATE to senior-engineer
  (effort: low, model: claude-sonnet-4.6)
- **Deduplication:** if an improvement task for that skill is already in
  `incoming/` or `processing/`, skip spawning

## Adding `## Self-Improvement` to a Skill

Every SKILL.md ends with a `## Self-Improvement` section (before any version
history). The template is in this skill's body above. Replace `[skill-name]`
with the actual kebab-case skill name.

High-traffic skills (orchestrator, queue-management, spec-validator,
spec-management) add this opening line before the template:

> We aim for [skill-name] to feel like a knowledgeable colleague rather than
> a rulebook. If any section felt prescriptive rather than guiding, a
> `tone_note` in your feedback helps us improve it.

## Integration Points

- `handback-schema.yaml` — defines the `skill_feedback` optional field
- `protocol_validator.py` — warns on malformed items; never errors on unknown sub-fields
- `session_analyzer.py` — `_harvest_skill_feedback()` aggregates per session
- `orchestrator_skill.py` — `_route_skill_feedback()` checks threshold and spawns DELEGATEs
- `feedback_loop.py` — `record_from_handback()` persists raw feedback items

## Self-Improvement

This skill is the root definition; improvements to it require a spec-management
proposal because changing it changes all downstream skills. Feedback on this skill
should include `skill_name: skill-improvement-feedback` and be specific about
what part of the pattern needs refinement.
