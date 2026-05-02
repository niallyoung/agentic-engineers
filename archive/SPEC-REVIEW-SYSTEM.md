# Automated Spec Review System

**Goal:** SPEC.md is the source of truth. Any changes are automatically validated to ensure consistency, completeness, architectural soundness, and security. The spec cannot drift from implementation, and vice versa.

---

## The Problem

Without automated spec validation:
- ❌ Spec drifts from implementation silently
- ❌ Documentation becomes outdated (TYPE_A: features documented but missing)
- ❌ New features added without spec (TYPE_B: undocumented features)
- ❌ Spec says one thing, code does another (TYPE_C: mismatches)
- ❌ Breaking changes sneak in (TYPE_D: without deprecation path)
- ❌ Architectural constraints violated unknowingly

**Result:** Spec becomes unreliable, team stops trusting it, communication breaks down.

---

## The Solution: SPEC Review Skill

**Automated, multi-agent spec validation triggered on every change.**

### When Triggered

1. **Pre-push (primary):** Developer modifies SPEC.md
   ```bash
   git add docs/SPEC.md
   git commit -m "feat: update spec"
   git push
   → Pre-push hook detects SPEC.md change
   → Triggers SPEC REVIEW SKILL
   → Blocks push if NEEDS_REVISION
   → Allows push if APPROVED
   ```

2. **Post-merge:** SPEC.md merged to main
   ```bash
   → Automatic review runs
   → Records findings in artifacts/
   ```

3. **Manual:** Developer requests review
   ```bash
   agentic-engineers review-spec --file docs/SPEC.md
   ```

4. **Scheduled:** Weekly audit
   ```bash
   (cron job on Monday 9am)
   → Audits current spec
   → Reports findings
   ```

---

## How It Works

### Step 1: SpecEngineerOrchestrator Receives DELEGATE

```
SPEC.md changed
  ↓
Git hook creates DELEGATE:
  {
    task_id: 2026-04-29-spec-review-abc123,
    role: spec_engineer_orchestrator,
    scope: "Review SPEC.md changes",
    context: {
      spec_content: <full SPEC.md>,
      previous_spec: <HEAD~1 version>,
      diff: <git diff>
    }
  }
  ↓
SpecEngineerOrchestrator.execute(delegate)
```

### Step 2: Orchestrator Delegates to 4 Review Agents (Parallel)

```
SpecEngineerOrchestrator
  ├─ ConsistencyReviewerAgent (Sonnet 4.6)
  │  └─ Checks for contradictions, broken references, unclear definitions
  │
  ├─ ArchitectureReviewerAgent (Opus 4.7)
  │  └─ Validates self-contained constraint, agent delegations, clean interfaces
  │
  ├─ CompletenessReviewerAgent (Sonnet 4.6)
  │  └─ Verifies all agents documented, protocols complete, examples present
  │
  └─ SecurityReviewerAgent (Opus 4.7)
     └─ Reviews security constraints, compliance implications, risk changes
```

Each agent reviews in parallel (~20-30ms), total <2 seconds.

### Step 3: Agents Return HANDBACK with Findings

Each reviewer returns:
```yaml
status: PASS | ESCALATE
issues_found:
  - "Contradiction: Section 3.1 says Haiku, Section 5.2 says Sonnet"
  - "Broken ref: Agent 'FutureAgent' mentioned but not defined"
severity: PASS | LOW | MEDIUM | HIGH
confidence: 0.90
```

### Step 4: Orchestrator Classifies Issues as TYPE_A/B/C/D

```python
for issue in all_issues:
    if issue.type == "feature_documented_missing_code":
        issue.classification = TYPE_A  # Critical
    elif issue.type == "feature_undocumented":
        issue.classification = TYPE_B  # Moderate
    elif issue.type == "spec_code_mismatch":
        issue.classification = TYPE_C  # Moderate
    elif issue.type == "breaking_change":
        issue.classification = TYPE_D  # Critical
```

### Step 5: Make Decision

```
if TYPE_A_count > 0 or TYPE_D_count > 0:
    Decision = NEEDS_REVISION  ← BLOCKS COMMIT
    Severity = HIGH
    Message: "Fix these critical issues before committing"

elif TYPE_B_count > 0 or TYPE_C_count > 0:
    Decision = NEEDS_REVIEW  ← WARNS DEVELOPER
    Severity = MEDIUM
    Message: "Review these findings, you may proceed"

else:
    Decision = APPROVED  ← ALLOWS COMMIT
    Severity = PASS
    Message: "Spec review passed"
```

### Step 6: Return HANDBACK

```yaml
decision: APPROVED | NEEDS_REVISION | NEEDS_REVIEW
status: PASS | ESCALATE
findings:
  type_a: [...]  # Critical
  type_b: [...]  # Moderate
  type_c: [...]  # Moderate
  type_d: [...]  # Critical
recommendations:
  - "Clarify agent model assignments"
  - "Add missing protocol example"
  - "Update agent status from 'stub' to 'ready'"
confidence: 0.90
```

---

## Review Agents (Detailed)

### 1. Consistency Reviewer Agent

**Purpose:** Detect logical contradictions and broken references within SPEC.md

**Checks:**
- Contradictions: Agent defined with conflicting properties
  - Example: Section 3.1 says "Haiku 4.5", Section 5.2 says "Sonnet 4.6"
- Broken references: Mentions agent/protocol not defined
  - Example: "Engineer delegates to TaskExecutor" but TaskExecutor not documented
- Unclear definitions: Ambiguous or contradictory descriptions
  - Example: "Low effort but can be high effort tasks" (contradiction)
- Format consistency: Spec structure follows conventions

**Output:**
```yaml
status: PASS | ESCALATE
issues_found:
  - type: contradiction
    location: "Section 3.1 vs Section 5.2"
    description: "Agent model conflicts"
  - type: broken_reference
    location: "Section 4.2"
    description: "TaskExecutor mentioned but not defined"
severity: HIGH | MEDIUM | LOW
```

### 2. Architecture Reviewer Agent

**Purpose:** Validate self-contained constraint and architectural soundness

**Checks:**
- Self-contained constraint: No external API calls mentioned
  - Validates: No "call Claude API", no "invoke AWS", no "shell script"
- Agent delegation model: All work is agent-to-agent
  - Validates: No external integrations, pure delegation
- Clean interfaces: DELEGATE/HANDBACK structures defined
  - Validates: Protocol consistency, no hidden dependencies
- No breaking changes: Architectural decisions stable
  - Validates: New constraints don't contradict existing ones

**Output:**
```yaml
status: PASS | ESCALATE
issues_found:
  - type: external_api_mention
    location: "Section 8.3"
    description: "Mentions calling Claude API (violates constraint)"
  - type: missing_delegation
    location: "Agent XYZ"
    description: "Doesn't specify what agent to delegate to"
severity: HIGH | MEDIUM
```

### 3. Completeness Reviewer Agent

**Purpose:** Verify spec is complete and ready for implementation/re-implementation

**Checks:**
- All agents documented: 13 SDLC/QG + 7 Review agents all specified
- All protocols defined: DELEGATE, HANDBACK, FEEDBACK fully specified
- All examples provided: Usage examples for key scenarios
- All success criteria stated: Each agent has measurable criteria
- No TODO/FIXME left: Spec is finalized

**Output:**
```yaml
status: PASS | ESCALATE
missing_items:
  - type: missing_agent_spec
    agent: "SpecEngineerOrchestrator"
    location: "AGENTS.md"
  - type: missing_example
    protocol: "Feedback loop"
    location: "Section 7"
severity: MEDIUM
```

### 4. Security Reviewer Agent

**Purpose:** Ensure spec change doesn't weaken security constraints

**Checks:**
- Constraint preservation: Self-contained constraint still enforced
  - Example: Change doesn't allow external integrations
- Compliance implications: No new risks introduced
  - Example: Change doesn't expose credentials, doesn't bypass validations
- Model security: No downgrade of security-critical agents
  - Example: Security Engineer still uses Opus (not downgraded to Haiku)
- Change risk assessment: Breaking changes properly documented
  - Example: Deprecated features have migration path

**Output:**
```yaml
status: PASS | ESCALATE
security_issues:
  - type: constraint_violation
    constraint: "Self-contained"
    description: "New mention of external API integration"
  - type: security_downgrade
    agent: "SecurityEngineerAgent"
    change: "Opus 4.7 → Haiku 4.5"
    risk: "HIGH"
severity: HIGH | MEDIUM
```

---

## Decision Logic (Summary)

```
TYPE_A (Documented feature missing in code):
  Severity: CRITICAL
  Decision: NEEDS_REVISION (BLOCK)
  Action: Developer must implement the documented feature

TYPE_B (Feature in code but undocumented):
  Severity: MODERATE
  Decision: NEEDS_REVIEW (WARN)
  Action: Developer can proceed, but should document feature

TYPE_C (Spec/code mismatch):
  Severity: MODERATE
  Decision: NEEDS_REVIEW (WARN)
  Action: Developer can proceed, but should align spec/code

TYPE_D (Breaking change without deprecation):
  Severity: CRITICAL
  Decision: NEEDS_REVISION (BLOCK)
  Action: Developer must add deprecation path or revert

Final Decision Logic:
├─ If TYPE_A or TYPE_D found → NEEDS_REVISION (EXIT 1, BLOCK)
├─ If TYPE_B or TYPE_C found → NEEDS_REVIEW (EXIT 2, WARN)
└─ Otherwise → APPROVED (EXIT 0, ALLOW)
```

---

## Git Hook Integration

### Pre-Push Hook

```bash
#!/bin/bash
# File: .git/hooks/pre-push

echo "Running pre-push checks..."

# Check if SPEC.md is in the changes
if git diff origin/main..HEAD --name-only | grep -q "docs/SPEC.md"; then
    echo "SPEC.md changed, running spec review..."
    
    agentic-engineers review-spec \
        --file docs/SPEC.md \
        --exit-on-revision
    
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 1 ]; then
        echo "❌ Spec review FAILED (NEEDS_REVISION)"
        echo "Fix the critical issues and try again"
        exit 1
    elif [ $EXIT_CODE -eq 2 ]; then
        echo "⚠️  Spec review flagged issues (NEEDS_REVIEW)"
        echo "Proceed with caution, review findings"
        # Allow push but with warning
    else
        echo "✅ Spec review PASSED"
    fi
fi

# Continue with other checks (E2E, diff review, etc.)
...
```

### Artifact Recording

```bash
# Captures full review findings for audit trail
artifacts/2026-04-29/
├── DELEGATE-2026-04-29-spec-review-abc123.yaml
├── HANDBACK-2026-04-29-spec-review-abc123.yaml
└── spec-reviews/
    └── 2026-04-29-spec-review-findings.yaml
        ├── decision: APPROVED
        ├── consistency: PASS
        ├── architecture: PASS
        ├── completeness: PASS
        ├── security: PASS
        └── recommendations: [...]
```

---

## Impact: Keeping Spec in Sync with Code

### Without This System
```
Week 1:  Spec written accurately
Week 2:  Engineer adds feature X (not in spec)
Week 3:  SeniorEng plans feature Y based on outdated spec
Week 4:  Developers confused, spec not trusted
Week 5:  Spec becomes obsolete, not maintained
```

### With This System
```
Week 1:  Spec written accurately
Week 2:  Engineer adds feature X
         → Pre-push hook runs SPEC REVIEW
         → TYPE_B found: "Feature X not documented"
         → Developer updates SPEC.md immediately
         → Spec stays current
Week 3:  SeniorEng plans feature Y from accurate, current spec
Week 4:  Developers trust spec, follow it
Week 5+: Spec remains authoritative
```

---

## Success Criteria

✅ **Automation:** Spec review runs automatically on every change  
✅ **Blocking:** TYPE_A/D issues block commits (no broken specs escape)  
✅ **Clear Feedback:** Developers get specific, actionable recommendations  
✅ **Audit Trail:** Every review recorded in artifacts/ for compliance  
✅ **Comprehensive:** All review types (consistency, architecture, completeness, security) covered  
✅ **Fast:** <30 seconds total (4 agents in parallel)  
✅ **Accurate:** <2% false positives, 100% TYPE_A/D catch rate  

---

## Implementation Roadmap

**Phase 2 (Week 2):** Core agents ready
- ✅ SpecEngineerOrchestrator
- ✅ ConsistencyReviewerAgent
- ✅ ArchitectureReviewerAgent
- ✅ CompletenessReviewerAgent
- ✅ SecurityReviewerAgent

**Phase 3 (Week 3):** Integration complete
- ✅ Git pre-push hook wired
- ✅ Artifact recording functional
- ✅ Manual invocation working
- ✅ First spec changes validated

**Phase 4 (Week 4):** Production ready
- ✅ Tested against real spec changes
- ✅ Team trained on workflow
- ✅ Recommendations clear and actionable

---

**SPEC.md is sacred. This system keeps it that way.**
