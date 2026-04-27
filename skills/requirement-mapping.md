---
name: requirement-mapping
description: Map requirements to tests to code, calculate traceability coverage
type: skill
version: 1.0
track: compliance
---

# requirement-mapping

Trace each requirement through tests to implementation code. Identify unmapped
requirements (no tests), orphaned code (no requirement), and calculate coverage %.

## Usage

```
/requirement-mapping service_path={service-name} spec_file=specs/user-management.yaml
/requirement-mapping service_path={service-name} requirement_id=REQ-004-membership
/requirement-mapping service_path={service-name}  # use default spec discovery
```

## Input

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `service_path` | str | required | Path to service root |
| `spec_file` | str | null | Path to requirement spec (YAML/JSON/Markdown) |
| `requirement_id` | str | null | Filter to single requirement |
| `include_orphaned_code` | bool | true | Report code without requirement mapping |

## Output

```json
{
  "service": "{service-name}",
  "spec_file": "specs/user-management.yaml",
  "requirements_total": 15,
  "requirements_covered": 13,
  "requirements_unmapped": 2,
  "coverage_percent": 86.7,
  "mappings": [
    {
      "requirement_id": "REQ-001-user-role-admin",
      "description": "Admin users can approve/reject calendar events",
      "test_count": 3,
      "tests": [
        "TestAdminApproveEvent (handlers/calendar_test.go:45)",
        "TestAdminRejectEvent (handlers/calendar_test.go:78)",
        "TestRoleTransition_MemberToAdmin (models/user_test.go:112)"
      ],
      "code_files": [
        "handlers/calendar.go:AdminApprovalHandler",
        "models/user.go:User.IsAdmin",
        "models/user.go:User.CanApprove"
      ],
      "all_tests_passing": true,
      "coverage": "100%"
    }
  ],
  "unmapped_requirements": [
    {
      "requirement_id": "REQ-005-audit-logging",
      "description": "All admin actions must be audit logged",
      "gap": "no tests found matching this requirement"
    }
  ],
  "orphaned_code": [
    {
      "file": "handlers/legacy.go:OldApprovalHandler",
      "reason": "no requirement reference, no test coverage"
    }
  ]
}
```

## Implementation

### Step 1: Load Requirements

```pseudo
func load_requirements(spec_file, service_path):
  if spec_file:
    return parse_spec(spec_file)
  
  # Auto-discover specs for service
  spec_dirs = [
    service_path + "/specs/",
    "{service-name}/specs/",
    "~/.agents/agentic-engineers/skills/specs/"
  ]
  
  for dir in spec_dirs:
    files = find(dir, "*.yaml") + find(dir, "*.md")
    specs = [parse_spec(f) for f in files if mentions_service(f, service_name)]
    if specs:
      return merge_specs(specs)
  
  error("No requirement spec found for " + service_name)
```

Supported spec formats:

**YAML:**
```yaml
requirements:
  - id: REQ-001-user-role-admin
    description: Admin users can approve/reject calendar events
    tags: [admin, calendar, permissions]
    acceptance_criteria:
      - admin can approve events they do not own
      - admin cannot approve their own events
```

**Markdown (with requirement annotations):**
```markdown
## REQ-001: Admin Calendar Approval
<!-- req-id: REQ-001-user-role-admin -->
Admin users must be able to approve or reject calendar events submitted by members.
```

**Code annotations (extracted from Go comments):**
```go
// REQ-001-user-role-admin: validates admin can approve calendar events
func TestAdminApproveEvent(t *testing.T) { ... }
```

### Step 2: Discover Tests for Each Requirement

```pseudo
func find_tests_for_requirement(req_id, service_path):
  tests = []
  
  # Strategy 1: explicit annotation in test file
  # grep for "// REQ-001" or "// Requirement: REQ-001"
  annotated = grep_recursive(service_path, f"// {req_id}", "*.go")
  tests += extract_test_names_from_context(annotated)
  
  # Strategy 2: test name contains requirement keywords
  keywords = extract_keywords(req_id)  # ["admin", "approve", "calendar"]
  for keyword in keywords:
    matches = grep_test_functions(service_path, keyword)
    tests += matches
  
  # Strategy 3: test file in requirement-named directory
  # e.g., test/admin/ for admin requirements
  dir_tests = find_tests_in_matching_dirs(service_path, req_id)
  tests += dir_tests
  
  # Deduplicate and score (annotated > keyword > directory)
  return rank_and_dedupe(tests)
```

### Step 3: Map Tests to Code

```pseudo
func trace_test_to_code(test_name, service_path):
  # Find test function
  test_file, line = find_function(service_path, test_name)
  
  # Read test body — what functions does it call?
  test_body = read_function_body(test_file, test_name)
  
  # Extract called functions (simple: grep for function calls)
  called = extract_function_calls(test_body)
  
  # Find implementation files
  impl_files = []
  for fn in called:
    if is_test_helper(fn):
      continue
    location = find_function_definition(service_path, fn)
    if location:
      impl_files.append(f"{location.file}:{fn}")
  
  return impl_files
```

### Step 4: Check Test Status

```pseudo
func check_test_status(tests, service_path):
  # Run only the tests mapped to this requirement
  test_names = [t.name for t in tests]
  run_filter = "|".join(test_names)
  
  output = exec(f"go test ./... -run '{run_filter}' -v", cwd=service_path)
  
  passed = [t for t in tests if f"--- PASS: {t.name}" in output]
  failed = [t for t in tests if f"--- FAIL: {t.name}" in output]
  
  return { passed: len(passed), failed: len(failed), all_passing: len(failed) == 0 }
```

### Step 5: Identify Orphaned Code

```pseudo
func find_orphaned_code(service_path, all_requirement_code_files):
  # All exported functions in service
  all_functions = find_exported_functions(service_path)
  
  # Functions covered by requirements
  covered_functions = set(all_requirement_code_files)
  
  orphaned = []
  for fn in all_functions:
    if fn not in covered_functions:
      # Check if it has any test coverage at all
      has_test = grep(service_path, fn.name, "*_test.go")
      orphaned.append({
        file: fn.file + ":" + fn.name,
        reason: "no requirement reference" + (", no test coverage" if not has_test else "")
      })
  
  return orphaned
```

### Step 6: Calculate Coverage

```pseudo
func calculate_coverage(requirements, mappings):
  covered = [r for r in requirements if r.id in mappings and len(mappings[r.id].tests) > 0]
  coverage_pct = len(covered) / len(requirements) * 100
  
  per_requirement = {}
  for req in requirements:
    mapping = mappings.get(req.id)
    if mapping:
      all_tests_count = len(mapping.tests)
      passing_count = mapping.tests_passing
      per_requirement[req.id] = f"{passing_count}/{all_tests_count} passing"
    else:
      per_requirement[req.id] = "0 tests"
  
  return { total_pct: coverage_pct, per_requirement: per_requirement }
```

## ERS Requirement Reference

### {service-name} Requirements (examples)

```
REQ-001-user-role-admin       Admin calendar event approval
REQ-002-user-create           Create user with optional email/phone
REQ-003-membership-states     Membership pending/active/cancelled
REQ-004-email-optional        Users can exist without email (phone-only)
REQ-005-audit-logging         Admin actions must be logged
REQ-006-app-access-flag       appAccess controls Cognito login
REQ-007-event-first           Domain events stored before external API calls
REQ-008-cognito-fields        Cognito needs email+name; phone optional
```

### Annotation Convention for ERS Tests

Add requirement annotations to test functions:
```go
// REQ-002-user-create: validates phone-only user creation
func TestCreateUser_PhoneOnly(t *testing.T) {
    // ...
}

// REQ-004-email-optional: user without email should not receive email notifications
func TestUpdateUser_NoEmailNoEmailNotification(t *testing.T) {
    // ...
}
```

### Finding Unannotated Tests

Run this to see which tests lack requirement annotations:
```bash
grep -r "^func Test" {service-name} --include="*_test.go" | \
  grep -v "// REQ-" | \
  head -20
```

## Integration

- Called by `requirement-verification` (uses output as input)
- Called by `spec-compliance-verification` for cross-spec checking
- Results shown in `quality-gate-orchestration` compliance report
- Unmapped requirements become backlog items in planning tools
- Orphaned code flagged for `cleanup.md` consideration

## Success Criteria

- Map REQ-001 through REQ-008 to tests in {service-name}
- Calculate coverage % accurately
- Identify at least 1 unmapped requirement (REQ-005-audit-logging is likely gap)
- List orphaned handlers/functions with no requirement link
