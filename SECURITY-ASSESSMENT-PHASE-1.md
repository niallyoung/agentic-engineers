# SECURITY ASSESSMENT: Phase 1 Audit Security Implications

**Status:** CRITICAL ISSUES IDENTIFIED  
**Requested by:** Principal Engineer (Phase 1 audit lead)  
**Conducted by:** Security Engineer (3x parallel review, Round 1)  
**Date:** 2026-05-26  

---

## Executive Summary

**Recommendation: PAUSE Phase 1 audit.** Implement security hardening BEFORE correcting SPEC.md.

The proposed Phase 1 changes (fix queue path, remove version stamps, verify agent definitions) are sound in principle but will **DEGRADE SECURITY** if implemented without safeguards.

### Five Critical Issues Identified

| Issue | Severity | Impact | Fix Required |
|-------|----------|--------|--------------|
| **Queue path ambiguity** | 🔴 CRITICAL | Enables queue injection/poisoning | Enforce canonical path in all docs + runtime checks |
| **Removing version stamps** | 🟡 HIGH | Breaks audit trail linking tasks to spec | Keep stamps; add spec_version to DELEGATE/HANDBACK/SPAN |
| **Agent definition drift** | 🔴 CRITICAL | Enables silent downgrade of security capability | Tri-level verification: git hook + field + runtime |
| **Missing security-critical fields** | 🔴 CRITICAL | No way to flag security tasks → underfunded | Add security_scope, approval_gate, audit_required to DELEGATE |
| **Weak orchestrator enforcement** | 🔴 CRITICAL | Enables bypass attacks | Implement @enforce_delegate_requirement decorator |

---

## Detailed Findings

### FINDING #1: Queue Path Ambiguity (CRITICAL)

**Problem:** SPEC.md contains contradictory queue path references:
- Line 21 (Executive Summary): `artifacts/queue/`
- Lines 37, 72: `~/.copilot/queue/{session-id}/incoming/`
- Lines 504-546: `~/.agentic-engineers/{session-id}/{harness}/queue/` ← CANONICAL
- Actual implementation: `~/.agentic-engineers/{session-id}/{harness}/queue/`

**Security Impact:** Path confusion enables:
- Queue injection (write to wrong path, claim it's valid per SPEC line 21)
- Queue poisoning (modify entries if paths not enforced)
- Privilege escalation (queue isolation depends on correct paths)

**Recommendation:** 
- ✅ Correct SPEC.md but also implement runtime queue path enforcement
- ✅ Add git hook to fail builds if legacy paths appear in SPEC text
- ✅ Implement Orchestrator decorator to validate queue paths at runtime

---

### FINDING #2: Version/Date Stamp Removal (HIGH)

**Problem:** Removing `version: 1.0` and `updated: 2026-05-02` breaks security audit trail.

**Why it matters:**
1. Security audits must link: task execution → spec that authorized it → routing decision
2. Without version: "Which SPEC approved this model selection?" becomes unanswerable
3. SPAN records don't include `spec_version` field → can't detect spec drift
4. Example attack: SPEC changes model from Opus → Sonnet, but old task still claims "routed per SPEC" (which spec?)

**Recommendation:**
- ✅ KEEP version/date stamps in SPEC.md
- ✅ Add `spec_version` field to DELEGATE (mandatory):
  ```yaml
  spec_version: "1.0"  # Which SPEC authorized this routing?
  ```
- ✅ Add `spec_version` to SPAN records for audit trail linkage
- ✅ Update git hooks to REJECT commits that remove version/date stamps

---

### FINDING #3: Agent Definition Drift (CRITICAL)

**Problem:** No mechanism verifies SPEC.md agent definitions match implementation.

**Attack scenario:** SPEC says Security Engineer uses claude-opus-4.7, but implementation silently uses claude-sonnet-4.6 → security tasks are underfunded without awareness.

**Recommendation:**
- ✅ Implement tri-level verification:
  1. Git hook: verify every agent in AGENTS.md has matching implementation
  2. DELEGATE field: add `model_verification_sha` (SHA of AGENTS.md that authorized this model)
  3. Runtime check in Orchestrator: validate model exists before routing
- ✅ Add `model_mismatch` flag to SPAN records to detect drift

---

### FINDING #4: Missing Security-Critical Protocol Fields (CRITICAL)

**Problem:** DELEGATE/HANDBACK protocol has NO fields for security metadata:
- `security_scope` — Is this task auth/crypto/PII/secrets/injection-risk?
- `approval_gate` — Does task require pre-approval?
- `audit_required` — Must task be post-audit reviewed?
- `cve_check_required` — Vulnerable dependencies checked?

**Attack scenario:** Developer adds `/login` endpoint as "Engineer" task (Haiku), Orchestrator has no way to know this is security-critical → routes to cheap model instead of Security Engineer.

**Recommendation:**
- ✅ Add security fields to DELEGATE:
  ```yaml
  security_scope: none | auth | crypto | pii | secrets | injection | supply_chain
  approval_gate: none | lead_engineer | principal_engineer | security_engineer
  requires_cve_check: true | false
  audit_required: true | false
  ```
- ✅ Update Orchestrator routing: if security_scope != none, always route to Security Engineer
- ✅ Update HANDBACK to include security findings (cves_checked, crypto_review, injection_risks)

---

### FINDING #5: Weak Orchestrator-First Enforcement (CRITICAL)

**Problem:** SPEC.md says "no exceptions" (line 25) but provides no runtime enforcement.

**Why it's weak:**
1. "No other entry point exists" is false → Makefiles, tests, git hooks execute code without queue entry
2. SPAN capture happens AFTER work is done → no real-time alert if work executed without DELEGATE
3. No runtime check: "Does this task have a corresponding DELEGATE?"

**Attack scenario:**
```python
# Autonomous loop running without queue entry (not caught by git hooks)
while True:
    check_queue()
    time.sleep(30)
```

**Recommendation:**
- ✅ Define enforcement criteria in SPEC.md: Every task MUST have DELEGATE + HANDBACK + SPAN + QE review
- ✅ Implement @enforce_delegate_requirement decorator in Orchestrator
- ✅ Strengthen git hook to catch autonomous patterns:
  - `while True`, `while 1`, `asyncio.run`, `threading.Thread`, `schedule.every`
  - Standalone `if __name__ == "__main__"`
  - Direct queue writes (`os.makedirs.*queue`)

---

## Verdict

**These changes DEGRADE security if implemented without safeguards.**

**Current approach:** Fix SPEC.md documentation drift first
**Recommended approach:** 
1. **Phase 1.5 (NEW - Security Hardening):** Implement the 5 recommendations above
2. **Then Phase 1:** Audit and correct SPEC.md with security safeguards in place

---

## Next Steps

**Options:**
1. **Pause & Fix Security (Recommended):** 
   - Add 1-2 hours to timeline
   - Implement all 5 security recommendations
   - THEN proceed with SPEC audit
   - Result: SPEC.md is accurate AND secure

2. **Proceed with Caution:**
   - Continue Phase 1 but document "SECURITY DEBT" items
   - Implement security fixes in Phase 4 (after Principles+Rules design)
   - Risk: Known vulnerabilities remain for 6-9 hours

3. **Escalate & Iterate:**
   - Share findings with 3x Security Engineers
   - Get consensus on fix priority
   - Implement consensus fixes before Phase 1

**Security Engineer Recommendation:** **OPTION 1 (Pause & Fix Security)**

---

**Awaiting Principal Engineer guidance on how to proceed.**
