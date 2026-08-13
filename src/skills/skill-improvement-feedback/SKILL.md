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

## Feedback Emission & Convention

Agents emit `skill_feedback` in their HANDBACK blocks (see The `skill_feedback` Block below).
The feedback is recorded in the session transcript. No automated routing or accumulation
engine exists yet — feedback is harvested by convention and surfaced to the Orchestrator
for manual routing decisions.

## Adding `## Self-Improvement` to a Skill

Every SKILL.md ends with a `## Self-Improvement` section (before any version
history). The template is in this skill's body above. Replace `[skill-name]`
with the actual kebab-case skill name.

High-traffic skills (orchestrator, protocol-validator, spec-validator,
spec-management) add this opening line before the template:

> We aim for [skill-name] to feel like a knowledgeable colleague rather than
> a rulebook. If any section felt prescriptive rather than guiding, a
> `tone_note` in your feedback helps us improve it.

## Integration Points

- **Protocol Validator** — `KNOWN_HANDBACK_RUNTIME_FIELDS` in `src/skills/protocol-validator/scripts/protocol_validator.py`
  accepts `skill_feedback` as a forward-compatible HANDBACK extension field. Its shape is
  defined here (this skill's pattern) rather than in `protocol-core-v1.0.yaml` directly.

## Self-Improvement

This skill is the root definition; improvements to it require a spec-management
proposal because changing it changes all downstream skills. Feedback on this skill
should include `skill_name: skill-improvement-feedback` and be specific about
what part of the pattern needs refinement.
