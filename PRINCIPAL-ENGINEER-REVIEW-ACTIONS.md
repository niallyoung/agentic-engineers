# PRINCIPAL ENGINEER REVIEW — ACTION ITEMS

**Status:** ✅ Architecture Review COMPLETE — Ready for Engineer Implementation

---

## IMMEDIATE ACTIONS (Do these FIRST — 1 minute)

These bugs must be fixed before Engineer begins work.

### ❌ BUG #1: Fix Path in quality-engineer.md

**File:** `skills/roles/quality-engineer.md`  
**Line:** 20  
**Current:** `7. **review/security-architecture-review.md** — Tier 3 security review (group)`  
**Fix to:** `7. **security/security-architecture-review.md** — Tier 3 security review (group)`

**Why:** The file is in `security/` directory, not `review/`. Quality Engineer can't access the skill without this fix.

---

### ❌ BUG #2: Fix Typo in lead-engineer.md

**File:** `skills/roles/lead-engineer.md`  
**Line:** 13  
**Current:** `3. **monitoring/cidc-watch.md** — Monitor CI/CD pipeline status`  
**Fix to:** `3. **monitoring/cicd-watch.md** — Monitor CI/CD pipeline status`

**Why:** Typo in filename (cidc → cicd). Lead Engineer can't access the skill without this fix.

---

## TIER CORRECTIONS (Do these BEFORE Engineer starts — 5 minutes)

These aren't bugs but architectural corrections. Verify these 4 roles understand the changes:

### ✅ VERIFICATION: Check all 4 roles reference github-cli.md

These should reference `shared/github-cli.md`:
- [ ] `skills/roles/engineer.md` — uses for `git push`
- [ ] `skills/roles/senior-engineer.md` — uses for PR merge operations
- [ ] `skills/roles/lead-engineer.md` — uses for PR review operations
- [ ] `skills/roles/quality-engineer.md` — uses for artifact handling

**Note:** `github-cli.md` is **Tier B** (4/4 roles), not Tier C

---

### ✅ VERIFICATION: Check all 4 roles reference cdk-stack.md

These should reference `shared/cdk-stack.md`:
- [ ] `skills/roles/engineer.md` — uses for deployment
- [ ] `skills/roles/senior-engineer.md` — uses for infrastructure review
- [ ] `skills/roles/lead-engineer.md` — uses for validation
- [ ] `skills/roles/quality-engineer.md` — uses for code review

**Note:** `cdk-stack.md` is **Tier B** (4/4 roles), not Tier C

---

## ENGINEER IMPLEMENTATION PHASE

Engineer agent will execute the DELEGATE block from `PRINCIPAL-ENGINEER-HANDBACK.md`

### Phase 1: Bug Fixes (5 minutes)
- [ ] Fix quality-engineer.md path
- [ ] Fix lead-engineer.md typo
- [ ] Verify both files resolve

### Phase 2: Create Core Baseline (1 hour)
- [ ] Create `shared/core-engineering-baseline.md`
- [ ] Section 1: Git Workflow
- [ ] Section 2: TDD & Implementation
- [ ] Section 3: Code Review Standards
- [ ] Section 4: Testing Overview
- [ ] Section 5: GitHub CLI Essentials
- [ ] Section 6: CDK Stack Patterns
- [ ] Cross-link all sections

### Phase 3: Create Engineer-Specifics (30 minutes)
- [ ] Create `shared/engineer-specifics.md`
- [ ] Section 1: Local CI Pipeline
- [ ] Section 2: Lambda Handler Patterns
- [ ] Section 3: Makefile Standards
- [ ] Add clear "Engineer only" notice

### Phase 4: Update Role Files (30 minutes)
- [ ] Update `skills/roles/engineer.md` to reference baselines
- [ ] Update `skills/roles/senior-engineer.md` to reference baselines
- [ ] Update `skills/roles/lead-engineer.md` to reference baselines
- [ ] Update `skills/roles/quality-engineer.md` to reference baselines

### Phase 5: Validation (1 hour)
- [ ] Grep for broken references
- [ ] Test each role can find baseline sections
- [ ] Verify no files deleted or hidden
- [ ] Confirm rollback procedures work

---

## VALIDATION CHECKLIST (After Engineer completes)

Run these checks to verify implementation quality:

### File Existence
```bash
[ -f skills/shared/core-engineering-baseline.md ] && echo "✅ core baseline exists"
[ -f skills/shared/engineer-specifics.md ] && echo "✅ engineer specifics exist"
```

### Content Completeness
```bash
# Check core baseline has all 6 sections
grep -c "^## " skills/shared/core-engineering-baseline.md  # Should be 6+
grep -q "Git Workflow" skills/shared/core-engineering-baseline.md && echo "✅ Git Workflow section"
grep -q "TDD\|Implementation" skills/shared/core-engineering-baseline.md && echo "✅ TDD section"
grep -q "Code Review" skills/shared/core-engineering-baseline.md && echo "✅ Code Review section"
grep -q "Testing\|Playwright" skills/shared/core-engineering-baseline.md && echo "✅ Testing section"
grep -q "GitHub CLI" skills/shared/core-engineering-baseline.md && echo "✅ GitHub CLI section"
grep -q "CDK\|Stack" skills/shared/core-engineering-baseline.md && echo "✅ CDK Stack section"

# Check engineer-specifics has 3 sections
grep -c "^## " skills/shared/engineer-specifics.md  # Should be 3+
grep -q "Local CI" skills/shared/engineer-specifics.md && echo "✅ Local CI section"
grep -q "Lambda" skills/shared/engineer-specifics.md && echo "✅ Lambda section"
grep -q "Makefile" skills/shared/engineer-specifics.md && echo "✅ Makefile section"
```

### Broken Reference Scan
```bash
# Check for references to original files (should still work)
echo "=== Checking git-workflow references ==="
grep -r "shared/git-workflow" skills/ || echo "None found (OK if in baseline)"

echo "=== Checking implementation-coding references ==="
grep -r "patterns/implementation-coding" skills/ || echo "None found (OK if in baseline)"

echo "=== Checking code-review references ==="
grep -r "review/code-review" skills/ || echo "None found (OK if in baseline)"

echo "=== Checking playwright references ==="
grep -r "testing/playwright" skills/ || echo "None found (OK if in baseline)"
```

### Role Integration
```bash
# Verify each role README updated
grep -l "core-engineering-baseline" skills/roles/*.md | wc -l  # Should be 4

# Verify no role is broken
for role in engineer senior-engineer lead-engineer quality-engineer; do
  echo "Checking $role..."
  grep -q "shared/.*baseline\|shared/.*specifics" skills/roles/$role.md && echo "✅ $role has baseline reference" || echo "❌ $role missing baseline"
done
```

---

## POST-IMPLEMENTATION SIGN-OFF

When Engineer completes implementation, verify:

- [ ] ✅ All 5 phases completed
- [ ] ✅ Both baseline files exist and have complete content
- [ ] ✅ All bugs fixed (2/2)
- [ ] ✅ All role files updated (4/4)
- [ ] ✅ No broken references (grep clean)
- [ ] ✅ All 4 roles can access their baseline sections
- [ ] ✅ Rollback verified as trivial

**Final Status:** ✅ Implementation complete, ready for use

---

## REFERENCE DOCUMENTS

**Full Review:** `PRINCIPAL-ENGINEER-HANDBACK.md`
- Complete tier analysis
- Dependency graphs
- Architecture decisions with rationale
- Full DELEGATE block for Engineer
- Pre/post implementation checklists
- Rollback procedures

**Summary:** `PRINCIPAL-ENGINEER-REVIEW-SUMMARY.md`
- Executive summary
- Key decisions table
- Quick action items
- Risk assessment

**This Document:** `PRINCIPAL-ENGINEER-REVIEW-ACTIONS.md`
- Immediate bug fixes
- Tier corrections
- Phase checklist
- Validation commands
- Sign-off criteria

---

## STATUS DASHBOARD

| Task | Status | Owner | Time |
|------|--------|-------|------|
| **Review Complete** | ✅ Done | Principal Engineer | — |
| **Bugs Identified** | ✅ 2 found | — | — |
| **Architecture Approved** | ✅ Yes | Principal Engineer | — |
| **Bug Fixes** | ⏳ Pending | Engineer | 1 min |
| **Core Baseline** | ⏳ Pending | Engineer | 1 hr |
| **Engineer Specifics** | ⏳ Pending | Engineer | 30 min |
| **Role Updates** | ⏳ Pending | Engineer | 30 min |
| **Validation** | ⏳ Pending | Engineer | 1 hr |
| **Go-Live** | ⏳ Ready | — | 3-5 hrs |

**Next Step:** Engineer Agent begins implementation when ready

---

**Approved by:** Principal Engineer  
**Date:** 2026-05-14  
**Status:** ✅ READY FOR ENGINEER IMPLEMENTATION
