---
name: self-healing-review
description: Codifies a repeatable investigate-fix-verify quality cycle for the framework/repo — fan out read-only QE investigations across dimensions, consolidate findings, dispatch disjoint fix packages routed by severity and file ownership, independently verify every HANDBACK, run the full battery, and commit — repeating until a round surfaces no material new findings. Runs interactively or fully autonomously (e.g. overnight via /loop or ScheduleWakeup).
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0.0"
  category: orchestration
  role: orchestrator
  model: claude-sonnet-5
  effort: low
---

## Overview

Self-Healing-Review codifies a repeatable **investigate → fix → verify** cycle for
framework/repo quality, correctness, consistency, and efficiency. It is not a
one-off checklist — it is the process an Orchestrator runs, round after round,
until a round turns up nothing materially new. It is designed to run either
interactively (operator watching, approving each round) or fully autonomously
(e.g. overnight while the operator is away, via `/loop` or `ScheduleWakeup`),
and it is designed to keep finding **new classes** of issues as the models
assigned to each role improve, without the skill itself needing to be rewritten
each time a stronger model ships.

## Why This Is Model-Agnostic By Design

This skill describes a **process** — which dimensions to investigate, the
fan-out/verification discipline, severity-based routing — not a fixed catalog
of known bugs or hardcoded model names. Nowhere in this document does a model
ID appear as part of the *procedure*; the only model reference is this skill's
own `metadata.model`, which is what the Orchestrator itself runs as.

Whichever models `src/AGENTS.md`'s roster currently assigns to Quality
Engineer, Engineer, Senior Engineer, Lead Engineer, and Security Engineer will
naturally surface issues at their own capability ceiling. A stronger future QE
model finds subtler drift than today's; a stronger future Engineer model fixes
more of what it finds without escalation. Upgrading a role's model in the
roster — already a supported, tested operation — is the **only** change needed
to make this skill "pick up" improved capability. **Never** edit this skill's
procedure to hardcode a new bug pattern, a specific file path that was buggy
once, or a specific model name; encode the *kind* of check instead (see
Investigation Dimensions below), so the check keeps paying off after the bug
that inspired it is long fixed.

## Investigation Dimensions

An extensible menu, not an exhaustive list — add rows as the framework grows.
Seeded here with dimensions that were actually exercised and proved valuable in
practice, cited concretely rather than left hypothetical:

| Dimension | What to check | Typical owner-role for fixes |
|---|---|---|
| Rendered output correctness | Parse every rendered artifact with a real parser, across every harness — not just "does the file exist." A pure existence check missed a production-breaking Copilot YAML corruption bug; a real YAML parse caught it. | engineer / senior-engineer |
| Installed-deliverable drift | `dist/` vs the real `$HOME` installs actually on disk; orphaned or leaked build artifacts from prior runs; foreign-file-protection edge cases (never delete a file `make install` didn't put there). | engineer |
| Test-suite health | Vacuous/tautological tests (assert `True`, assert a mock's own return value); tests violating this repo's `tmp_path`-only hermeticity convention; orphaned test files with no corresponding source; whether recent fixes are actually exercised at the *body* level, not just counted as "a test exists." | engineer / senior-engineer |
| Documentation accuracy | Doc claims vs actual code/config; dead cross-references; fabricated or hallucinated content. One prior round found a doc that was **actively injecting false context into live sessions** via a filesystem case-sensitivity quirk — a genuinely severe class of finding, not cosmetic. | lead-engineer (if docs/SPEC.md) / engineer (otherwise) |
| Makefile / build-target health | Every target actually runs; no orphaned targets; help text matches real behavior. | engineer |
| CI workflow + git hook consistency | Every path/script a workflow or hook references still resolves after churn elsewhere in the repo. | engineer / senior-engineer |
| Registry/config cross-consistency | Does every place a fact is stated — a roster table, a manifest YAML, an agent's own frontmatter, a skill's own frontmatter — agree with every other place? Treat the SKILL.md/AGENTS.md frontmatter as source of truth; everything else must match it, not the other way around. | engineer (mechanical) / lead-engineer (if authoritative doc itself is wrong) |
| Security review | Injection risks, credential handling, entropy-detector coverage, privacy (session data never entering tracked files). Defensive-scope only; route to Security Engineer — see Security Review Cadence below, run as its own periodic pass rather than folded into the QE-led dimensions. | security-engineer |

This menu is a **starting point**. Each round, consider whether a new
dimension deserves auditing — performance, dependency freshness, accessibility
of generated docs, whatever the repo's current shape suggests — and add it as
a new investigation package rather than always re-running the same fixed set.
A dimension that stops finding anything for several consecutive rounds can be
run less often; a new one can be added the moment a plausible new risk surface
appears (e.g. a new harness, a new script, a new external dependency).

## Procedure

1. **Scope the round.** The Orchestrator selects which dimensions to
   investigate this round — all of them for a full review, or a subset if
   explicitly scoped (e.g. "just docs," or "just the last commit's blast
   radius").

2. **Fan out investigations.** Issue one read-only QE investigation DELEGATE
   per dimension, in parallel, respecting the fan-out ≤ 5 limit from
   `src/AGENTS.md` (batch across multiple rounds of fan-out if more than 5
   dimensions are in scope this round). Each investigation DELEGATE MUST:
   - be **read-only** — report findings, fix nothing;
   - include a pointer to what is already known-fixed from prior rounds, so
     investigations don't churn on old ground;
   - require **live execution / re-parsing of real artifacts** wherever
     possible, rather than trusting prior claims — findings are real
     specifically *because* investigators re-run things instead of reading
     old reports;
   - require a **zero-modification proof** (git status/hash captured before
     and after the investigation) confirming the read-only constraint held.

3. **Consolidate.** Merge all findings into one ranked list, ordered by
   severity: actively-harmful-right-now > production-breaking >
   high-confidence real bug > medium drift/inconsistency > low/cosmetic.

4. **Group into disjoint fix packages by file ownership**, not just by
   severity. Two agents editing the same file concurrently has silently lost
   work before. Before dispatching, explicitly list which files each fix
   package will touch and verify zero overlap across concurrently-dispatched
   packages. If two findings genuinely require the same file, either merge
   them into one package or sequence them — never fan them out concurrently.

5. **Route each fix package by risk/authority:**
   - mechanical/low-risk config + test hygiene → `engineer`;
   - renderer/script logic changes, or anything requiring empirical
     verification before shipping → `senior-engineer` — explicitly instruct it
     to verify any suggested implementation empirically before shipping it,
     **even a suggestion from the Orchestrator itself** (a suggested rsync
     flag combination once looked correct but would have caused live data
     loss on BSD rsync; it was caught only because senior-engineer tested it
     in a throwaway tmp dir first, rather than trusting the suggestion);
   - anything touching `docs/SPEC.md`, or requiring spec-management authority
     → `lead-engineer`;
   - anything security-scoped → `security-engineer` (defensive-only, per the
     C5 gate — see Security Review Cadence below).

6. **Dispatch all fix packages in parallel**, again respecting fan-out ≤ 5 and
   file disjointness.

7. **Independently verify every HANDBACK before accepting it.** This is the
   framework's own Engineer HANDBACK Verification duty (`src/AGENTS.md`),
   applied here at scale: re-run at least one claimed test/check yourself,
   don't just trust a reported count. Prior rounds caught a mislabeled
   "656 passed" claim that was actually a partial run, and a genuinely wrong
   ledger status field from the Orchestrator's own tooling — both caught only
   by independent spot-verification before acceptance.

8. **Run the full battery** — bare pytest, skill tests, lint, verify,
   validate-renders, validate-agents, validate-skills, render-specs, the
   regression gate, and pre-commit. Every finding-fix round must leave the
   repo fully green before committing.

9. **Land real deliverable fixes.** If any finding required a fix to a real
   (non-`dist/`) deliverable — a stale installed file, leaked build artifacts —
   run the actual remediation (e.g. `make install-<harness>`) and
   independently verify the fix landed on disk, not just in the renderer
   source.

10. **Commit locally** with a clear, itemized commit message: what was found,
    what was fixed, how it was verified, per package. **Push only if
    explicitly authorized for this run** — default to commit-only (see
    Autonomous / AFK Operation below).

11. **Assess diminishing returns** (see below). If the round found material
    new findings, start another round. If not, declare the cycle complete and
    report a summary.

## Diminishing Returns Signal

Advisory, not mechanical: compare this round's count of **new** (not
already-known-fixed) actionable findings to the prior round's. A round that
surfaces zero new HIGH/MEDIUM findings, or only cosmetic/LOW findings already
at the bottom of prior rounds' lists, is a legitimate stopping point.

Use `python3 scripts/handback_rollup.py --events <ledger path>` for a quick
view of this round's HANDBACK volume/outcomes, and the
[audit-trail-review](../audit-trail-review/SKILL.md) skill's ledger
reconciliation for a sanity check that nothing from this round is left
orphaned before declaring done.

The decision to stop is always made by agent reasoning in context — never
hardcode a numeric threshold as a stopping *rule* (that would be control flow
in a place SPEC clause 3 reserves for agent judgment); a threshold may inform
the call, but it never makes it.

## Security Review Cadence

A full self-healing-review cycle SHOULD periodically include a Security
Engineer-led pass, independent of the QE-led dimensions above: fan out a
`security-engineer` DELEGATE (defensive-scope only, per the C5 gate documented
in `src/AGENTS.md`) to review the same repo state for injection risks,
credential handling, the entropy-detector's own coverage, and privacy
(session data never entering tracked files). Route any findings it surfaces
through Engineer/Senior-Engineer fix packages exactly like any other
dimension's findings — verified and committed the same way. A security-led
pass does not replace the QE-led dimensions; run both.

## Autonomous / AFK Operation

To run this unattended (e.g. overnight):

- Invoke via the `/loop` skill (self-paced dynamic mode) or `ScheduleWakeup`
  for recurring invocation.
- Default to **commit-only, never push**, unless the operator has explicitly
  authorized push for this run.
- State resolution is the audit-trail ledger itself — no separate state file
  is needed. Every `delegate_issued` / `handback_received` / `gate_result`
  this procedure produces is already durably logged per SPEC clause 7, so a
  resumed run can reconstruct "what was already found/fixed" by reading
  recent ledger entries before starting a new round.
- Pick a wakeup interval appropriate to how long a full round realistically
  takes — full rounds have run 15-60+ minutes wall-clock with 3-5 parallel
  investigations — rather than polling frequently.
- If genuinely idle (no material findings for two consecutive rounds),
  lengthen the interval or stop the loop rather than continuing to spin.

## Hard-Won Lessons

- **Verify any suggested fix empirically before shipping it, even one from the
  Orchestrator.** Platform-specific tool behavior (e.g. BSD vs GNU `rsync`
  flag interactions) can silently differ from the obvious/documented
  behavior.
- **Gitignored build directories (`dist/`, `.pytest_cache/`, `__pycache__/`)
  are shared mutable state** across concurrently-running agents in the same
  checkout. A transient inconsistency there is not automatically a real bug —
  reproduce it in isolation (fresh `rm -rf` + rebuild) before treating it as a
  finding.
- **Concurrent test runs against the same real repo can race on `.git/config`
  locks.** A single failing test in a large parallel run should be re-run in
  isolation before being treated as a regression.
- **Ledger corrections are append-only** per SPEC clause 7 — never edit a
  prior wrong-status line; append a corrected event and let both stand as
  honest history.
- **A HANDBACK's own self-reported summary count can be mislabeled or wrong**
  (a "full suite" claim that was actually a partial run, a status field bug
  from a shell loop's exit-code logic). The framework's own Engineer HANDBACK
  Verification duty exists specifically to catch this — apply it every time,
  not just when something looks suspicious.

## When To Invoke

At the end of a significant change campaign, before a merge, on explicit
request, or on a recurring autonomous schedule per the operator's preference.

## Self-Improvement

See [skill-improvement-feedback](../skill-improvement-feedback/SKILL.md) for feedback pattern.
Include `skill_feedback` in HANDBACK when this skill's dimension menu, routing rules, or diminishing-returns guidance need refinement.
