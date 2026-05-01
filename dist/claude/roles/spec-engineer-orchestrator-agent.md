# Spec Engineer Orchestrator Agent

**Model:** Sonnet 4.6  
**Effort:** medium  
**Status:** ⚠️ Needs implementation  

## Purpose

Automatically review SPEC.md when it changes, ensuring it remains consistent, complete, architecturally sound, and secure. Acts as the "keeper of the spec" — no spec change gets through without automated validation.

## Role

Entry point for SPEC Review Skill. Coordinates 4 parallel review agents, aggregates findings, makes APPROVED/NEEDS_REVISION/NEEDS_REVIEW decision.

## Input (DELEGATE Block)

```yaml
handoff_type: DELEGATE
task_id: 2026-04-29-spec-review-<hash>
role: spec_engineer_orchestrator
model: claude-sonnet-4-6
effort: medium
scope: "Review and validate SPEC.md changes"

context:
  spec_file_path: docs/SPEC.md
  change_type: modify | new | delete
  
  # Full spec content
  spec_content: |
    # Agentic Engineers System Specification
    ...full SPEC.md content...
  
  # Previous version (for diff detection)
  previous_spec_version: |
    # Agentic Engineers System Specification (v1.1)
    ...previous version...
  
  # Git diff for human readability
  diff: |
    --- a/docs/SPEC.md
    +++ b/docs/SPEC.md
    ...git diff output...
  
  # Change metadata
  author: username
  timestamp: 2026-04-29T14:32:00Z
  commit_message: "feat: update routing tree documentation"
```

## Output (HANDBACK Block)

```yaml
handoff_type: HANDBACK
task_id: 2026-04-29-spec-review-<hash>
timestamp: 2026-04-29T14:35:00Z
status: PASS  # PASS = approved, ESCALATE = needs revision
severity: PASS | LOW | MEDIUM | HIGH
confidence: 0.85

# Decision
decision: APPROVED | NEEDS_REVISION | NEEDS_REVIEW

# Findings by review type
consistency_review:
  status: PASS | ESCALATE
  issues_found: []
  # Example: ["Contradiction: Section 3.1 says Haiku, Section 5 says Sonnet"]

architecture_review:
  status: PASS | ESCALATE
  issues_found: []
  # Example: ["External API call mentioned in agent description (violates constraint)"]

completeness_review:
  status: PASS | ESCALATE
  issues_found: []
  # Example: ["Agent 'SpecEngineerOrchestrator' defined in AGENTS.md but not in SPEC.md"]

security_review:
  status: PASS | ESCALATE
  issues_found: []
  # Example: ["Security constraint weakened: was 'max effort', now 'high effort'"]

# Aggregated findings
all_issues:
  type_a:  # Documented feature missing in code (critical)
    count: 0
    issues: []
  type_b:  # Code feature undocumented (moderate)
    count: 0
    issues: []
  type_c:  # Spec/code mismatch (moderate)
    count: 0
    issues: []
  type_d:  # Breaking change (critical)
    count: 0
    issues: []

# Recommendations
recommendations:
  - "Clarify agent model assignments in Section 3"
  - "Add missing protocol example to Section 2"
  - "Update agent status from 'stub' to 'ready' for Engineer Agent"

# Summary
summary:
  total_issues: 0
  high_severity: 0
  medium_severity: 0
  approval_recommended: true

deliverables:
  - "Full spec review completed"
  - "4 review agents executed in parallel"
  - "All findings aggregated"
  - "Recommendations provided"

token_metrics:
  input_tokens: 8500
  output_tokens: 1200
  total_tokens: 9700
```

## Decision Logic

```
if (TYPE_A_count > 0 or TYPE_D_count > 0):
    decision = NEEDS_REVISION  # Block commit
    status = ESCALATE
    severity = HIGH
elif (TYPE_B_count > 0 or TYPE_C_count > 0):
    decision = NEEDS_REVIEW    # Flag for human
    status = ESCALATE if critical else PASS
    severity = MEDIUM
else:
    decision = APPROVED        # Allow commit
    status = PASS
    severity = PASS

confidence = 0.90  # High confidence in spec reviews
```

## Implementation Steps

### 1. Parse SPEC.md Content

```python
def do_work(self) -> Dict:
    spec_content = self.delegate_block.get("context", {}).get("spec_content", "")
    previous_spec = self.delegate_block.get("context", {}).get("previous_spec_version", "")
    diff = self.delegate_block.get("context", {}).get("diff", "")
    
    if not spec_content:
        raise ValueError("spec_content required in context")
```

### 2. Delegate to 4 Review Agents in Parallel

```python
# Build DELEGATE for each reviewer
consistency_delegate = {
    "handoff_type": "DELEGATE",
    "task_id": self.task_id,
    "role": "consistency_reviewer",
    "scope": "Check SPEC.md for contradictions and broken references",
    "context": {
        "spec_content": spec_content,
        "previous_spec": previous_spec,
        "diff": diff
    }
}

# Similar for architecture, completeness, security reviewers

# Delegate in parallel
from implementations import create_agent

consistency_agent = create_agent("consistency_reviewer")
architecture_agent = create_agent("architecture_reviewer")
completeness_agent = create_agent("completeness_reviewer")
security_agent = create_agent("security_reviewer")

# Execute in parallel (spawn threads or use asyncio)
consistency_handback = consistency_agent.execute(consistency_delegate)
architecture_handback = architecture_agent.execute(architecture_delegate)
completeness_handback = completeness_agent.execute(completeness_delegate)
security_handback = security_agent.execute(security_delegate)
```

### 3. Aggregate Findings

```python
# Collect all findings
all_issues = {
    "type_a": [],
    "type_b": [],
    "type_c": [],
    "type_d": []
}

# Extract TYPE_A/B/C/D issues from each reviewer
for issue in consistency_handback.get("issues_found", []):
    issue_type = classify_issue_type(issue)
    all_issues[issue_type].append(issue)

# Repeat for other agents...
```

### 4. Make Decision

```python
type_a_count = len(all_issues["type_a"])
type_d_count = len(all_issues["type_d"])

if type_a_count > 0 or type_d_count > 0:
    decision = "NEEDS_REVISION"
    status = "ESCALATE"
    severity = "HIGH"
elif len(all_issues["type_b"]) > 0 or len(all_issues["type_c"]) > 0:
    decision = "NEEDS_REVIEW"
    status = "ESCALATE"  # Still escalate, but for human decision
    severity = "MEDIUM"
else:
    decision = "APPROVED"
    status = "PASS"
    severity = "PASS"
```

### 5. Generate Recommendations

```python
recommendations = []

# Based on findings, generate actionable recommendations
if type_a_count > 0:
    recommendations.append(f"Address {type_a_count} documented features missing from code")

if "contradictions" in consistency_handback:
    recommendations.append("Resolve contradictions in spec (see details)")

if "external_api_mention" in architecture_handback:
    recommendations.append("Remove external API references (violates self-contained constraint)")

# etc...
```

### 6. Return HANDBACK

```python
return {
    "decision": decision,
    "status": status,
    "severity": severity,
    "consistency_review": consistency_handback,
    "architecture_review": architecture_handback,
    "completeness_review": completeness_handback,
    "security_review": security_handback,
    "all_issues": all_issues,
    "recommendations": recommendations,
    "summary": {
        "total_issues": sum(len(v) for v in all_issues.values()),
        "high_severity": type_a_count + type_d_count,
        "medium_severity": len(all_issues["type_b"]) + len(all_issues["type_c"]),
        "approval_recommended": decision == "APPROVED"
    },
    "confidence": 0.90,
    "deliverables": [
        "Full spec review completed",
        "4 review agents executed",
        "All findings aggregated",
        "Decision and recommendations provided"
    ]
}
```

## Success Criteria

- ✅ All 4 review agents execute in parallel (no serialization)
- ✅ <30 second total latency
- ✅ Zero TYPE_A/D issues leak through (100% block rate)
- ✅ <2% false positives on TYPE_B/C
- ✅ Clear, actionable recommendations
- ✅ Proper decision (APPROVED/NEEDS_REVISION/NEEDS_REVIEW)

## Integration Points

### Git Pre-Push Hook

```bash
# Triggers when SPEC.md is in staged changes
if git diff --cached --name-only | grep -q "docs/SPEC.md"; then
    agentic-engineers review-spec --exit-on-revision
    # Returns exit code 0 if APPROVED
    # Returns exit code 1 if NEEDS_REVISION (blocks push)
    # Returns exit code 2 if NEEDS_REVIEW (warns user)
fi
```

### Artifact Writing

```python
# Write DELEGATE and HANDBACK for audit trail
artifacts = ArtifactManager()
artifacts.write_delegate(self.task_id, self.delegate_block)
artifacts.write_handback(self.task_id, handback)

# Write detailed findings to artifacts/feedback/spec-reviews/
artifacts.write_spec_review(self.task_id, all_issues, recommendations)
```

## Example Scenarios

### Scenario 1: Clean Spec Update ✅

```
Input: SPEC.md updated with minor documentation clarification
ReviewFindingset:
- Consistency: No contradictions found
- Architecture: Constraint maintained
- Completeness: All agents documented
- Security: No constraint changes

Output:
- Decision: APPROVED
- Status: PASS
- Severity: PASS
- Git hook: Allows push
```

### Scenario 2: Introduces TYPE_A Violation ❌

```
Input: SPEC.md documents "FutureAgent" but no implementation exists in AGENTS.md
Findings:
- Completeness: Agent documented but not in registry

Output:
- Decision: NEEDS_REVISION (TYPE_A)
- Status: ESCALATE
- Severity: HIGH
- Git hook: BLOCKS push
```

### Scenario 3: Violates Self-Contained Constraint ❌

```
Input: SPEC.md updated to mention "calls Claude API for analysis"
Findings:
- Architecture: External API call violates self-contained constraint

Output:
- Decision: NEEDS_REVISION (TYPE_D breaking change)
- Status: ESCALATE
- Severity: HIGH
- Git hook: BLOCKS push
```

## Dependencies

- 4 review sub-agents (must be implemented):
  - ConsistencyReviewerAgent
  - ArchitectureReviewerAgent
  - CompletenessReviewerAgent
  - SecurityReviewerAgent

- Artifact management (already exists):
  - ArtifactManager class

- Git hook integration (to be added):
  - Pre-push hook that calls `agentic-engineers review-spec`
