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
- Until the enforcement work packages land, `.githooks/LOCKED_MODELS.sh` remains the
  enforced copy, and some tests still parse the old structure.

## Rejected alternatives

Loosening the allowlist to a regex (passes typos, no per-harness data); floating aliases or
"latest in family" (contradicts stable pinning); a runtime `ModelResolver` class (larger
surface, agent files stop being self-describing); an auto-bump bot (violates deliberate
bumps); making `src/AGENTS.md` the source of truth (brittle table parsing, no metadata).

## References

`docs/SPEC.md` (SPEC-2026-011), `src/skills/spec-management/SKILL.md`,
`docs/MODELS.md` (generated; created by a later work package).
