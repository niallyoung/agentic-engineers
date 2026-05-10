# Comprehensive Audit — Agents, Roles, Skills

**Date:** 2026-04-24  
**Purpose:** Identify inconsistencies, gaps, and missing implementations  
**Status:** Multiple issues found — requires cleanup

---

## Role Definitions (from AGENTS.md)

| Role | Model | Effort | Cost Tier | Skills Defined |
|------|-------|--------|-----------|---|
| **Orchestrator** | Haiku | low | 1x | ❌ 10 documented, 11 files found |
| **Engineer** | Haiku | high | 1x | ❌ 3 documented, 8 files found |
| **Senior Engineer** | Sonnet | high | 3x | ✅ 2 (api-resilience, event-consumer) |
| **Lead Engineer** | Sonnet | high | 3x | ✅ 1 (code-review) |
| **Principal Engineer** | Opus | high | 7.5x | ❌❌ **0 SKILLS DEFINED** |
| **Security Engineer** | Opus | max | 7.5x | ❌❌ **0 SKILLS DEFINED** |
| **Quality Engineer** | Sonnet | medium | 3x | ✅ 4 (code-quality-analysis, quorum-qe, e2e-playwright, SKILLS overview) |
| **Model Engineer** | Opus | high | 7.5x | ✅ 5 (model-analysis, recommendation, cost-quality, comparison, quality-feedback) |

---

## Actual Skills Found (33 files)

### **Orchestrator (11 files — 10 documented + 1 duplicate)**

**Documented (10 in INDEX.md, CLAUDE.md, IMPLEMENTATION_COMPLETE.md):**
1. ✅ task-routing.md
2. ✅ metrics-collection.md
3. ✅ model-engineer-coordination.md
4. ✅ github-cli-operations.md
5. ✅ token-advisor.md
6. ✅ tokenadvisor-scheduler.md
7. ✅ model-engineer.md (automation)
8. ✅ model-engineer-automation.md (automation)
9. ✅ ab-testing-framework.md
10. ✅ ab-test-automation.md

**Found on disk (11 files):**
- All 10 above PLUS:
- ❌ `github-cli.md` (DUPLICATE — also in shared/)

**Issue:** `github-cli.md` exists in BOTH:
- `/skills/orchestrator/skills/github-cli.md`
- `/skills/shared/github-cli.md`

Should be: Move to shared/ only, remove from orchestrator/

---

### **Engineer (8 files — 3 documented + 5 NOT DOCUMENTED)**

**Documented (3 in INDEX.md, CLAUDE.md):**
1. ✅ implementation-coding.md
2. ✅ local-ci.md
3. ✅ playwright-ui-testing.md

**Found on disk (8 files):**
- All 3 above PLUS:
- ❌ `cdk-stack.md` — NOT DOCUMENTED
- ❌ `cicd-watch.md` — NOT DOCUMENTED
- ❌ `lambda-handler.md` — NOT DOCUMENTED
- ❌ `makefile.md` — NOT DOCUMENTED
- ❌ `sigv4-client.md` — NOT DOCUMENTED

**Issue:** 5 additional skills exist but:
1. Not listed in INDEX.md, CLAUDE.md, or IMPLEMENTATION_COMPLETE.md
2. Appear to be leftover from orphaned ers-* directories
3. Should be either:
   - Moved to `shared/` (if cross-role)
   - Deleted (if duplicates/obsolete)
   - Properly cataloged in documentation

**Evidence of orphan cleanup incomplete:**
These files match the directory names we deleted:
- `lambda-handler.md` ← was `{example-service}/`
- `makefile.md` ← was `{example-service}/`
- `cdk-stack.md` ← was `{example-service}/`
- `cicd-watch.md` ← was `{service-name}/`
- `sigv4-client.md` ← was `{example-service}/`

---

### **Senior Engineer (2 files — 2 documented)**

**Documented:**
1. ✅ api-resilience.md
2. ✅ event-consumer.md

**Status:** ✅ Consistent. No orphans.

---

### **Lead Engineer (1 file — 1 documented)**

**Documented:**
1. ✅ code-review.md

**Status:** ✅ Consistent. No orphans.

---

### **Quality Engineer (4 files — 4 documented)**

**Documented:**
1. ✅ SKILLS.md (overview)
2. ✅ code-quality-analysis.md
3. ✅ quorum-qe.md
4. ✅ e2e-playwright.md

**Status:** ✅ Consistent. No orphans.

**Minor issue:** `SKILLS.md` is in root of quality-engineer/, not in `skills/` subdirectory. All others use `skills/` subdirectory convention. **Should be:** Move to `skills/overview.md` for consistency.

---

### **Model Engineer (5 files — 5 documented)**

**Documented:**
1. ✅ model-analysis.md
2. ✅ model-recommendation.md
3. ✅ cost-quality-tradeoff.md
4. ✅ model-comparison.md
5. ✅ quality-feedback-analysis.md

**Status:** ✅ Consistent. No orphans.

---

### **Principal Engineer (0 files — 0 documented)**

**Skills defined:** ❌ **NONE**

**AGENTS.md says:**
- Role: Principal Engineer
- Model: claude-opus-4-6
- Effort: high
- Use: Cross-service architecture, complex planning, design decisions

**Problem:** No skills file exists. When would Principal Engineer be invoked? What's the workflow?

**Missing:**
- No `principal-engineer/skills/` directory
- No documented decision-making patterns
- No architecture analysis guidelines

---

### **Security Engineer (0 files — 0 documented)**

**Skills defined:** ❌ **NONE**

**AGENTS.md says:**
- Role: Security Engineer
- Model: claude-opus-4-7
- Effort: max
- Use: Security analysis, threat modeling, vulnerability audits

**Problem:** No skills file exists. When would Security Engineer be invoked? What's the workflow?

**Missing:**
- No `security-engineer/skills/` directory
- No threat modeling guidelines
- No vulnerability assessment patterns
- No security review checklist

---

### **Shared Skills (2 files — 1 documented, 1 duplicate)**

**Documented:**
1. ✅ git-workflow.md

**Found:**
- ✅ git-workflow.md
- ❌ github-cli.md (DUPLICATE — also in orchestrator/skills/)

**Issue:** github-cli.md appears in both places. Should consolidate to shared/ only.

---

## Summary of Issues

### **Critical Issues (Require Fix)**

| Issue | Severity | Fix |
|-------|----------|-----|
| Principal Engineer: 0 skills defined | CRITICAL | Create `principal-engineer/skills/` with 2-3 core skills |
| Security Engineer: 0 skills defined | CRITICAL | Create `security-engineer/skills/` with 2-3 core skills |
| Engineer: 5 undocumented skills on disk | HIGH | Document or delete orphaned skills (lambda, makefile, cdk-stack, cicd-watch, sigv4-client) |
| github-cli.md: Duplicate in 2 locations | HIGH | Keep in shared/ only, remove from orchestrator/ |

### **Medium Issues (Should Fix)**

| Issue | Severity | Fix |
|-------|----------|-----|
| Quality Engineer: SKILLS.md in wrong location | MEDIUM | Move to skills/overview.md for consistency |
| Engineer skills: 5 not in documentation | MEDIUM | Add to INDEX.md, CLAUDE.md if keeping; delete if obsolete |

### **Minor Issues (Consider)**

| Issue | Severity | Note |
|-------|----------|------|
| Skill counts in docs | MINOR | INDEX.md says "27+ skills"; actual is ~33 (unclear what's included) |
| Orchestrator skill count | MINOR | Docs say 10, actual is 11 (github-cli duplicate) |

---

## Detailed Analysis

### **1. Principal Engineer Gap**

**Current State:**
```
Principal Engineer (Opus 4.6, high)
  Role: Cross-service architecture, complex planning, design decisions
  Skills: NONE
```

**What's Missing:**
- How does Principal Engineer approach system design?
- What's the decision-making process?
- What output is expected (architecture docs, design decisions)?
- How does it integrate with other roles (does Principal → Senior → Engineer chain exist)?

**Recommendation:**
Create 2-3 core skills:
- `architecture-design.md` — System design patterns, cross-service impact analysis
- `design-decision-documentation.md` — How to document architectural decisions
- `system-tradeoff-analysis.md` — Cost vs. complexity vs. maintainability analysis

---

### **2. Security Engineer Gap**

**Current State:**
```
Security Engineer (Opus 4.7, max)
  Role: Security analysis, threat modeling, vulnerability audits
  Skills: NONE
```

**What's Missing:**
- Threat modeling methodology
- Vulnerability assessment checklist
- Secure coding guidelines
- Security review workflow
- How does it integrate with other roles?

**Recommendation:**
Create 2-3 core skills:
- `threat-modeling.md` — STRIDE/attack tree methodology, threat identification
- `vulnerability-assessment.md` — Testing patterns, common CVE classes, remediation
- `security-architecture-review.md` — Design review for auth, data flow, access control

---

### **3. Engineer Skills — 5 Undocumented Files**

**Files Found:**
1. `cdk-stack.md` — AWS CDK stack patterns
2. `cicd-watch.md` — CI/CD monitoring/debugging
3. `lambda-handler.md` — Lambda handler scaffolding
4. `makefile.md` — Makefile patterns
5. `sigv4-client.md` — IAM SigV4 signing

**Question:** Are these intentional Engineer skills, or orphaned from deleted ers-* directories?

**Options:**
A) **Keep as Engineer skills** → Document in INDEX.md, CLAUDE.md
B) **Move to shared/** → These are cross-role utilities, not Engineer-specific
C) **Delete** → If obsolete/duplicated elsewhere

**Recommendation:** Review each:
- `lambda-handler.md` → Keep (Engineer uses this for implementation)
- `cdk-stack.md` → Move to shared/ (used by multiple roles)
- `sigv4-client.md` → Move to shared/ (cross-role utility)
- `makefile.md` → Keep/Move? (used by Engineer + others?)
- `cicd-watch.md` → Keep (Engineer uses for debugging)

Or consolidate: Keep only reference in `reference/INFRASTRUCTURE_PATTERNS.md`, don't duplicate in skills/.

---

### **4. github-cli Duplication**

**Current State:**
```
/skills/orchestrator/skills/github-cli.md      ← Should delete
/skills/shared/github-cli.md                   ← Keep (correct location)
```

Also related: `github-cli-operations.md` in orchestrator/skills/ — is this different from `github-cli.md`?

**Recommendation:**
1. If they're the same: Delete orchestrator/ version, keep shared/
2. If they're different: Rename and document the difference
3. Likely: `github-cli-operations.md` = old name, `github-cli.md` = new name → delete old

---

### **5. Quality Engineer File Organization**

**Current State:**
```
/skills/quality-engineer/SKILLS.md              ← Wrong location
/skills/quality-engineer/skills/code-quality-analysis.md
/skills/quality-engineer/skills/quorum-qe.md
/skills/quality-engineer/skills/e2e-playwright.md
```

**Issue:** SKILLS.md is overview, but in wrong directory.

**Recommendation:** Move to `/skills/quality-engineer/skills/overview.md` for consistency with other roles.

---

## Summary Matrix

### **Skills Coverage**

```
Role                  | Documented | Found | Orphans | Missing
----------------------|-----------|-------|---------|--------
Orchestrator          |    10     |  11   |    1    |   —
Engineer              |     3     |   8   |    5    |   —
Senior Engineer       |     2     |   2   |    0    |   —
Lead Engineer         |     1     |   1   |    0    |   —
Quality Engineer      |     4     |   4   |    0    |   —
Model Engineer        |     5     |   5   |    0    |   —
Principal Engineer    |     0     |   0   |    0    |   3 (critical)
Security Engineer     |     0     |   0   |    0    |   3 (critical)
Shared                |     1     |   2   |    1    |   —
----------------------|-----------|-------|---------|--------
TOTAL                 |    26     |  33   |    7    |   6
```

---

## Recommended Actions (Priority Order)

### **CRITICAL (Do First)**

1. **Create Principal Engineer skills** (missing 3 core skills)
   - [ ] `principal-engineer/skills/architecture-design.md`
   - [ ] `principal-engineer/skills/design-decision-documentation.md`
   - [ ] `principal-engineer/skills/system-tradeoff-analysis.md`

2. **Create Security Engineer skills** (missing 3 core skills)
   - [ ] `security-engineer/skills/threat-modeling.md`
   - [ ] `security-engineer/skills/vulnerability-assessment.md`
   - [ ] `security-engineer/skills/security-architecture-review.md`

### **HIGH (Do Second)**

3. **Clean up Engineer skills**
   - [ ] Decide: Keep, move to shared/, or delete (lambda, makefile, cdk-stack, cicd-watch, sigv4-client)
   - [ ] Document final decision in skills/ README

4. **Remove github-cli duplication**
   - [ ] Delete `/skills/orchestrator/skills/github-cli.md` (keep shared/ version only)
   - [ ] Verify `github-cli-operations.md` is not a duplicate

### **MEDIUM (Do Third)**

5. **Reorganize Quality Engineer structure**
   - [ ] Move `SKILLS.md` → `skills/overview.md`

6. **Update all documentation**
   - [ ] INDEX.md: Update skill counts and organization
   - [ ] CLAUDE.md: Add Principal/Security Engineer definitions
   - [ ] IMPLEMENTATION_COMPLETE.md: Correct total skill count
   - [ ] Add Principal/Security to all role tables

---

## Definition of Done

After fixes:

- [ ] All 8 roles have skills defined (min 1 each, ideally 2-3)
- [ ] No duplicate skill files on disk
- [ ] All skills documented in INDEX.md, CLAUDE.md, IMPLEMENTATION_COMPLETE.md
- [ ] Consistent file organization (all overview files in `skills/` subdirectory)
- [ ] Skills count accurate in documentation (currently 27+, will be ~35+ with Principal/Security)
- [ ] No orphaned files from deleted ers-* directories
- [ ] Principal and Security engineers have clear workflows defined
- [ ] All role tables in docs are consistent (same role/model/effort definitions)

---

**Status:** ⚠️ **Requires Cleanup** (7 files to handle, 6 skills to create, 5 documentation updates)

**Estimated effort:** 4-6 hours (skill creation + documentation updates + testing)
