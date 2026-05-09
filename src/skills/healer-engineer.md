---
name: healer-engineer
description: Auto-fix low-risk, pattern-matchable issues; create PR with optional auto-merge
type: skill
version: 1.0
track: self-healing
role: Healer Engineer
---

# healer-engineer

Receives a diagnostic from `issue-diagnostic-engine` and applies an automated fix for low-risk,
pattern-matchable issues. Creates a PR, optionally auto-merges if CI passes, then signals the
orchestrator to re-run quality gates.

**Only executes for**: `confidence=HIGH` AND `risk_level=LOW` diagnostics.

## Usage

```
/healer-engineer diagnostic={...} service_path={service-name}
/healer-engineer diagnostic={...} service_path={service-name} auto_merge_if_ci_passes=false
```

## Input

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `diagnostic` | dict | required | Output from `issue-diagnostic-engine` |
| `service_path` | str | required | Absolute or relative path to service root |
| `create_pr` | bool | true | Create a GitHub PR for the fix |
| `auto_merge_if_ci_passes` | bool | true | Auto-merge PR if all CI checks pass |

### Precondition check (fail fast)

```pseudo
if diagnostic.confidence != "HIGH" or diagnostic.risk_level != "LOW":
  abort("Healer only handles HIGH confidence + LOW risk. Escalate to human.")
if diagnostic.healer_eligible != true:
  abort("healer_eligible=false. Not routed here correctly.")
```

## Output

```json
{
  "issue_fixed": true,
  "fix_type": "config_missing",
  "file_modified": "cdk/stacks/command_stack.go",
  "fix_applied": "Added SNS_TOPIC_ARN to Lambda environment vars block",
  "pr_created": true,
  "pr_url": "https://github.com/{your-org}/{service-name}/pull/47",
  "pr_status": "CI_RUNNING",
  "auto_merge_eligible": true,
  "merge_status": "MERGED",
  "notes": "CI passed in 3m12s. Auto-merged. Quality gates re-triggered.",
  "audit": {
    "issue_type": "config_missing",
    "service": "{service-name}",
    "fixed_at": "2026-04-27T14:23:00Z",
    "fix_commit": "abc1234",
    "healer_version": "1.0"
  }
}
```

### Field Reference

| Field | Values | Description |
|-------|--------|-------------|
| `pr_status` | `CI_RUNNING` \| `CI_PASSED` \| `CI_FAILED` \| `NOT_CREATED` | Current PR CI state |
| `merge_status` | `MERGED` \| `SKIPPED` \| `FAILED` \| `PENDING` | Auto-merge outcome |
| `issue_fixed` | bool | Whether the code change was applied successfully |

## Allowed Fix Types

The Healer only acts on these five issue types. All others must be escalated.

### 1. config_missing — Missing environment variable

**Trigger**: `issue_type = "config_missing"` or `root_cause = "configuration"`

**What to fix**:
- Add missing env var to the Lambda environment block in the CDK stack file
- If var name matches an SSM Parameter Store pattern, reference SSM (not hardcode value)
- Single file change only — the CDK stack for that service

**Constraint**: Do NOT add secrets or credentials directly. If the value looks like a secret,
escalate with: `"Env var appears to be a secret — human must supply value."`

**Pattern** (Go CDK stack):
```go
// Before
Environment: map[string]*string{
    "APP_NAME": jsii.String(appName),
},

// After
Environment: map[string]*string{
    "APP_NAME":        jsii.String(appName),
    "SNS_TOPIC_ARN":   jsii.String(*snsTopicArn.StringValue()),
},
```

---

### 2. dependency_version — Outdated or vulnerable package (patch/minor bump only)

**Trigger**: `issue_type = "dependency_issue"` with `confidence = HIGH` (patch/minor bump)

**What to fix**:
- Go: update version in `go.mod`, run `go mod tidy` to regenerate `go.sum`
- Node: update version in `package.json`, run `npm install` to update lockfile
- Single version bump per Healer invocation

**Constraint**: Only patch or minor bumps. Major version bumps → escalate to lead.

**ERS example**:
```bash
# go.mod before
github.com/aws/aws-sdk-go v1.44.0

# go.mod after
github.com/aws/aws-sdk-go v1.44.3

# Then run:
go mod tidy
```

---

### 3. test_flakiness — Intermittent / timing-dependent test

**Trigger**: `root_cause = "test_flakiness"`

**What to fix** (choose one, in order of preference):
1. Increase timeout constant in test setup
2. Add retry wrapper around flaky assertion
3. Add `time.Sleep` / `waitForCondition` before assertion if timing-dependent
4. Isolate shared state that causes non-determinism between parallel tests

**Constraint**: Only modify test files (`*_test.go`, `*.test.ts`). Do NOT touch production code.

**ERS example**:
```go
// Before
func TestSNSPublish(t *testing.T) {
    result, err := publish(ctx, msg)
    assert.NoError(t, err)
}

// After
func TestSNSPublish(t *testing.T) {
    var result Result
    var err error
    require.Eventually(t, func() bool {
        result, err = publish(ctx, msg)
        return err == nil
    }, 5*time.Second, 100*time.Millisecond)
    assert.NotNil(t, result)
}
```

---

### 4. lockfile_stale — Stale or missing lockfile

**Trigger**: `root_cause = "dependency"` and error contains lockfile mismatch

**What to fix**:
- Go: run `go mod tidy` to regenerate `go.sum`
- Node: run `npm install` to update `package-lock.json`
- Commit the regenerated lockfile

**Constraint**: Only regenerate — do NOT bump versions when fixing a lockfile.

---

### 5. import_path_wrong — Incorrect import path

**Trigger**: `root_cause = "dependency"` and error is `"cannot find module"` / `"package not found"`

**What to fix**:
- Correct the import path in the single file that references it
- Verify the correct path exists in `go.mod` or `package.json`

**Constraint**: Single-file fix only. If the wrong import appears in >3 files, escalate to lead
(indicates a module rename — needs broader refactoring decision).

---

## NOT Allowed (Escalate Immediately)

| Issue Type | Reason | Escalate To |
|------------|--------|-------------|
| Logic bug | Code understanding required | lead |
| Security finding | Security judgment required | security |
| Architecture change | Design decision required | principal |
| Major dependency bump | Breaking changes possible | lead |
| Multi-file refactoring | Risk too high | lead |
| Secret / credential value | Must not be automated | lead |
| Infrastructure misconfiguration | IAM / VPC risk | principal |

## Implementation

### Step 1: Validate input

```pseudo
func validate(diagnostic):
  assert diagnostic.confidence == "HIGH"
  assert diagnostic.risk_level == "LOW"
  assert diagnostic.healer_eligible == true
  assert diagnostic.issue_type in ALLOWED_FIX_TYPES
```

### Step 2: Select fix strategy

```pseudo
func select_fix(diagnostic):
  match diagnostic.issue_type:
    "config_missing"   → fix_config_missing(diagnostic, service_path)
    "dependency_issue" → fix_dependency_version(diagnostic, service_path)
    "test_flakiness"   → fix_flaky_test(diagnostic, service_path)
    "lockfile_stale"   → fix_lockfile(diagnostic, service_path)
    "import_path_wrong"→ fix_import_path(diagnostic, service_path)
    default            → abort("Unknown fix type: " + diagnostic.issue_type)
```

### Step 3: Apply fix (single file)

```pseudo
func apply_fix(fix_strategy, service_path):
  file = fix_strategy.target_file
  original = read_file(file)
  patched = fix_strategy.apply(original)

  if diff(original, patched).files_changed > 1:
    abort("Fix touches multiple files — escalate to lead")

  write_file(file, patched)
  if fix_strategy.requires_regeneration:
    run_command(fix_strategy.regen_command, cwd=service_path)

  return {file_modified: file, fix_applied: fix_strategy.description}
```

### Step 4: Create branch and commit

```pseudo
func create_fix_branch(issue_type, description):
  branch_name = f"healer/{issue_type}/{slugify(description)}"
  git checkout -b branch_name
  git add <fixed_file>
  git commit -m f"fix(auto): {issue_type} - {description}"
  # Commit message format: "fix(auto): [issue_type] - [fix description]"
  # Example: "fix(auto): config_missing - add SNS_TOPIC_ARN to command Lambda env"
  return branch_name
```

### Step 5: Create PR

```pseudo
func create_pr(branch_name, diagnostic, fix_result):
  pr_body = f"""
## Auto-Heal: {diagnostic.root_cause_details}

**Issue type**: {diagnostic.issue_type}
**Root cause**: {diagnostic.root_cause}
**Fix applied**: {fix_result.fix_applied}
**File modified**: {fix_result.file_modified}
**Confidence**: {diagnostic.confidence} | **Risk**: {diagnostic.risk_level}

---
*Generated by healer-engineer v1.0. Review before merging if auto-merge is disabled.*
"""
  pr = gh pr create \
    --title f"fix(auto): {diagnostic.issue_type} - {truncate(diagnostic.root_cause_details, 60)}" \
    --body pr_body \
    --base main \
    --head branch_name

  return pr.url
```

### Step 6: Optional auto-merge

```pseudo
func auto_merge(pr_url, auto_merge_if_ci_passes):
  if not auto_merge_if_ci_passes:
    return {merge_status: "SKIPPED"}

  # Poll CI status (max 10 min)
  for attempt in range(10):
    sleep(60s)
    status = gh pr checks pr_url --json state
    if status.all_passed:
      gh pr merge pr_url --squash --auto
      return {merge_status: "MERGED"}
    if status.any_failed:
      return {merge_status: "FAILED", notes: "CI failed — healer escalates to lead"}

  return {merge_status: "PENDING", notes: "CI still running after 10 min — check manually"}
```

### Step 7: Build audit trail

```pseudo
func build_audit(diagnostic, fix_result, pr_url, merge_status):
  return {
    issue_type:      diagnostic.issue_type,
    service:         service_name(service_path),
    fixed_at:        now_iso8601(),
    fix_commit:      git_current_sha(),
    pr_url:          pr_url,
    merge_status:    merge_status,
    healer_version:  "1.0",
  }
  # Append to: agentic-engineers/healer-audit-log.jsonl
```

## Auto-Merge Guardrails

Auto-merge only proceeds when ALL of the following are true:

1. `auto_merge_if_ci_passes = true`
2. All CI checks pass (lint, test, security scan)
3. No human escalations triggered during the same quality gate run
4. Exactly one file modified (single, isolated change)
5. PR has been open for at least 60 seconds (prevents race conditions)

If any guardrail fails: leave PR open, set `merge_status = "PENDING"`, notify orchestrator.

## ERS-Specific Examples

### Example 1: Missing env var → fix CDK stack → auto-merge

**Input diagnostic**:
```json
{
  "root_cause": "configuration",
  "issue_type": "config_missing",
  "confidence": "HIGH",
  "risk_level": "LOW",
  "healer_eligible": true,
  "suggested_fix": "Add SNS_TOPIC_ARN to Lambda env vars in cdk/stacks/command_stack.go"
}
```

**Steps**:
1. Read `cdk/stacks/command_stack.go`
2. Locate Lambda `Environment` block
3. Add `"SNS_TOPIC_ARN": jsii.String(*snsTopicParam.StringValue())` (SSM reference, not hardcoded)
4. Branch: `healer/config_missing/add-sns-topic-arn-command`
5. Commit: `fix(auto): config_missing - add SNS_TOPIC_ARN to command Lambda env`
6. PR created → CI runs → auto-merge on green

**Output**:
```json
{
  "issue_fixed": true,
  "fix_type": "config_missing",
  "file_modified": "cdk/stacks/command_stack.go",
  "fix_applied": "Added SNS_TOPIC_ARN env var referencing SSM parameter /${appName}/SNSTopicARN",
  "pr_url": "https://github.com/{your-org}/{service-name}/pull/47",
  "pr_status": "CI_PASSED",
  "merge_status": "MERGED"
}
```

### Example 2: Outdated go.mod version → bump → auto-merge

**Input diagnostic**:
```json
{
  "root_cause": "dependency",
  "issue_type": "dependency_issue",
  "confidence": "HIGH",
  "risk_level": "LOW",
  "healer_eligible": true,
  "suggested_fix": "Bump github.com/aws/aws-sdk-go to v1.44.3 in go.mod, run go mod tidy"
}
```

**Steps**:
1. Edit `go.mod`: `github.com/aws/aws-sdk-go v1.44.0` → `v1.44.3`
2. Run `go mod tidy` (regenerates `go.sum`)
3. Stage both `go.mod` and `go.sum`
4. Commit: `fix(auto): dependency_issue - bump aws-sdk-go to v1.44.3 (GO-2026-12345)`
5. PR → CI → auto-merge

**Output**:
```json
{
  "issue_fixed": true,
  "fix_type": "dependency_issue",
  "file_modified": "go.mod",
  "fix_applied": "Bumped github.com/aws/aws-sdk-go from v1.44.0 to v1.44.3, go.sum regenerated",
  "pr_url": "https://github.com/{your-org}/{service-name}/pull/31",
  "pr_status": "CI_PASSED",
  "merge_status": "MERGED"
}
```

### Example 3: CI fails on Healer PR → escalate

**Steps**:
1. Fix applied, PR created
2. CI fails (unexpected test failure in unrelated test)
3. `merge_status = "FAILED"`
4. Healer does NOT force-merge
5. Returns output with `notes: "CI failed — Healer escalates to lead for review"`

**Output**:
```json
{
  "issue_fixed": true,
  "fix_type": "config_missing",
  "file_modified": "cdk/stacks/command_stack.go",
  "pr_url": "https://github.com/{your-org}/{service-name}/pull/47",
  "pr_status": "CI_FAILED",
  "merge_status": "FAILED",
  "notes": "CI failed on unrelated test TestIntegration_DynamoDB. Healer escalates to lead for review."
}
```

## Integration

- **Receives from**: `quality-gate-orchestration` → `issue-diagnostic-engine` → here
- **Requires**: `diagnostic.healer_eligible == true`
- **After success**: notify `quality-gate-orchestration` to re-run quality gates
- **After failure**: escalate to `lead` with PR URL and CI failure details
- **Audit log**: append every action to `agentic-engineers/healer-audit-log.jsonl`

## Commit Message Format

```
fix(auto): [issue_type] - [fix description]
```

Examples:
- `fix(auto): config_missing - add SNS_TOPIC_ARN to command Lambda env`
- `fix(auto): dependency_issue - bump aws-sdk-go to v1.44.3 (GO-2026-12345)`
- `fix(auto): test_flakiness - add retry to TestSNSPublish timeout assertion`
- `fix(auto): lockfile_stale - regenerate go.sum via go mod tidy`
- `fix(auto): import_path_wrong - correct {service-name} import path in event handler`
