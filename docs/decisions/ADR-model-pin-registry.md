---
title: Architecture Decision Record - Model Pin Registry
type: ADR
decision: APPROVED
date: 2026-10-02
supersedes: ADR-model-centralization.md
spec_amendment: SPEC-2026-011
---

# ADR: Model Pin Registry

## Status

**APPROVED** by user directive (2026-10-02). Principal/Security co-approval of the
companion LOCKED-section amendment (SPEC-2026-011) was not obtained and is recommended.
Supersedes [ADR-model-centralization](ADR-model-centralization.md).

## Context

A role's model was stored or re-declared in about a dozen places that had to agree by
hand (`.githooks/LOCKED_MODELS.sh`, the `src/AGENTS.md` roster, agent frontmatter, the
framework manifest, `renderer/validate_agents.py`, two divergent `map_model` functions,
the SPEC tables, prose in README/CONTRIBUTING/skills, and many tests). The "LOCKED"
label covered an allowlist of versions, so every new model forced a governed SPEC
amendment about the *meaning* of a LOCKED invariant when only a *value* had changed.
Claude Code renders mapped most roles to floating tier aliases, so a provider-side alias
move could change behaviour without any repo change. The SPEC also contradicted itself
on dot versus hyphen IDs and referenced code that does not exist (`ModelResolver`,
`src/config/models.yaml`).

## Decision

Separate invariants (stay in the spec) from values (one registry file).

1. **Registry.** `config/models.yaml`, read only through `scripts/models.py`, is the single
   source of truth for models, role pins, effort, fallback chains, and per-harness IDs.
   Everything else is generated from it or validated against it.
2. **Spec.** The LOCKED section keeps only invariants I1-I6 (ID format, single source,
   exact pins, user choice never overwritten, fallback surfaced, validators check shape not
   a version list). Model tables move to generated `docs/MODELS.md`.
3. **All Claude Code roles are pinned to exact IDs.** No floating tier alias is rendered
   for an assigned role.
4. **Fallbacks.** `claude-opus-4.8` for Principal and Security; `claude-sonnet-4.6` for the
   Sonnet-tier roles. Use is always surfaced, never silent.
5. **Approval.** A `Model-Pin-Approved-By:` commit trailer plus a `pin_history` line
   suffices for a role pin change. It is not a SPEC amendment. The `spec-management` skill
   carries a carve-out.
6. **Per-user override file** (`~/.agentic-engineers/models.local.yaml`) is deferred.
7. **Tables** live in `docs/MODELS.md`, a new generated top-level doc.
8. **Naming.** Source IDs use a dot minor (`claude-sonnet-5.5`); harness renders may
   hyphenate (`claude-sonnet-5-5`), as explicit per-harness registry data.

## Consequences

- A new model or pin bump is a registry edit plus `make models-sync`; no validator, spec,
  or test edits.
- Unknown IDs remain errors (registry membership), so typo protection is not weakened.
- Claude Code fallback cannot be enforced at runtime; it is reported, not guaranteed.
- Risk: Claude Code must accept each exact pinned ID. Verify before flipping the default;
  the rollout keeps the render mode reversible by data until verified.
- (Historical, at decision time.) Until the enforcement work packages landed,
  `.githooks/LOCKED_MODELS.sh` remained the enforced copy and some tests parsed the old
  structure. The enforcement has since landed; see the 2026-10-03 addendum.

## Rejected alternatives

Loosening the allowlist to a regex (passes typos, no per-harness data); floating aliases or
"latest in family" (contradicts stable pinning); a runtime `ModelResolver` class (larger
surface, agent files stop being self-describing); an auto-bump bot (violates deliberate
bumps); making `src/AGENTS.md` the source of truth (brittle table parsing, no metadata).

## References

`docs/SPEC.md` (SPEC-2026-011), `src/skills/spec-management/SKILL.md`,
`docs/MODELS.md` (generated; created by a later work package).

## Addendum (2026-10-02, SPEC-2026-012)

By user directive, `claude-sonnet-5.5` and `claude-opus-5.5` became the *minimum* pins
for the Sonnet and Opus families, rather than merely the current ones. The registry
gained a per-family `min_pin` floor (`families.<family>.min_pin`), enforced by
`scripts/models.py check` with a numeric `major.minor` comparison — never lexical, so a
future `5.10` correctly reads as newer than `5.5`. A fallback is explicitly exempt from
the floor: the whole point of a fallback is to be an older, more-available model a role
can degrade to, so forbidding a below-floor fallback would defeat it. A family with no
`min_pin` (haiku, fable) has no floor.

Every Sonnet-family role (Lead/Quality/Senior/Model Engineer) moved to `claude-sonnet-5.5`
and Principal Engineer to `claude-opus-5.5`; Engineer and Security keep their existing
pins (`claude-haiku-4.5`, `claude-fable-5`). `claude-sonnet-5` and `claude-opus-5` are
marked `status: fallback` — a new status alongside `current`/`supported`/`deprecated`/
`retired` — to document that they remain valid, known IDs but are no longer eligible as a
role's pin (only as a fallback rung), without retiring them. This is additive to the
registry's shape, not a reversal of any point above: the registry stays the single source
of truth, a Model Pin Change (not a SPEC amendment) is still how a pin moves, and I1–I6
are unchanged. As with the original ADR, principal-engineer/security-engineer co-approval
of this user-directed change was not obtained and is recommended.

## Addendum (2026-10-03, SPEC-2026-013)

Enforcement has landed (`.githooks/commit-msg`, `.githooks/pre-commit`,
`tests/test_model_pin_hooks.py`), and `.githooks/LOCKED_MODELS.sh` is a generated shim, not
an enforced copy. An independent verification showed two tests that hard-coded the current
pins (`test_seeded_pins_match_todays_assignments` and the agents-table parity roster test)
and so failed after a legitimate pin bump, contradicting "no validator, spec, or test
edits" above. Both are now registry-driven (`test_every_role_has_a_registered_pin_and_valid_effort`,
`test_role_pins_agree_with_agent_frontmatter` and the parity roster test), so the claim holds.
The invariant is: no test hard-codes a role's pin, model or effort; tests derive expected
values from `config/models.yaml` through `scripts/models.py`. The one deliberate exception is
the family-floor directive test, which locks the SPEC-2026-012 floors on purpose.
