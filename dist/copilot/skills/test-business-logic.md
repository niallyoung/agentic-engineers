---
name: test-business-logic
description: Parametric testing for ERS business rules, edge cases, and state machine transitions
type: skill
version: 1.0
track: testing
---

# test-business-logic

Generate and execute parametric tests for ERS business logic: user role transitions,
membership state machines, permission checks, and data consistency across services.

## Usage

```
/test-business-logic service_path={service-name} requirement_id=REQ-001-user-role-admin
/test-business-logic service_path={service-name} state_machine=membership_status
/test-business-logic service_path={service-name} business_logic_spec=@specs/user-permissions.yaml
```

## Input

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `service_path` | str | required | Path to service root |
| `business_logic_spec` | dict/str | null | Requirement object or path to spec file |
| `state_machine_transitions` | dict | null | Explicit state → state map to test |
| `requirement_id` | str | null | Filter to single requirement |
| `generate_edge_cases` | bool | true | Auto-generate edge cases from spec |

## Output

```json
{
  "requirement": "REQ-001-user-role-admin",
  "description": "Admin users can approve/reject calendar events",
  "edge_cases_tested": 12,
  "passed": 11,
  "failed": 1,
  "skipped": 0,
  "uncovered_transitions": ["disabled -> active"],
  "failed_cases": [
    {
      "case": "admin_rejects_own_event",
      "input": { "user_role": "admin", "event_owner": "self" },
      "expected": "HTTP 403",
      "actual": "HTTP 200",
      "file": "handlers/calendar_test.go:203"
    }
  ],
  "data_interactions": {
    "role_change_member_to_admin": "PASS",
    "admin_creates_event_after_promotion": "PASS",
    "event_creation_with_new_role_immediately": "FAIL"
  },
  "coverage_added_percent": 8.5,
  "gate_result": "WARN"
}
```

## Implementation

### Step 1: Load Business Logic Spec

```pseudo
func load_spec(business_logic_spec):
  if is_file_path(business_logic_spec):
    spec = parse_yaml_or_json(business_logic_spec)
  elif is_dict(business_logic_spec):
    spec = business_logic_spec
  else:
    # Read from {service-name}/specs/ using requirement_id
    spec = load_from_specs_dir(requirement_id)
  
  return normalize_spec(spec)  # ensure: id, description, rules, edge_cases
```

Spec format:
```yaml
requirement_id: REQ-001-user-role-admin
description: Admin users can approve/reject calendar events
rules:
  - admin can approve any event not owned by themselves
  - admin cannot approve own events
  - disabled users cannot perform any action
  - role changes take effect on next request (no session mutation)
state_machine:
  entity: User.Role
  transitions:
    - from: member → to: admin  (via admin promotion)
    - from: admin → to: disabled (via admin disable)
    - from: disabled → to: member (via admin reactivate)
    - INVALID: disabled → admin (must go via member first)
edge_cases:
  - empty permissions array
  - role change during active session
  - concurrent permission checks
```

### Step 2: Extract State Machine

```pseudo
func build_state_machine(spec, explicit_transitions):
  transitions = explicit_transitions or spec.state_machine.transitions
  
  states = set()
  edges = {}
  for t in transitions:
    states.add(t.from)
    states.add(t.to)
    edges[t.from] = edges.get(t.from, []) + [t.to]
  
  # Add INVALID transitions (should be rejected)
  invalid = [t for t in spec.state_machine if t.valid == false]
  
  return StateMachine(states, edges, invalid)
```

### Step 3: Generate Parametric Test Cases

```pseudo
func generate_test_cases(spec, state_machine):
  cases = []
  
  # 1. State transition tests
  for transition in state_machine.valid_transitions:
    cases.append(TestCase{
      name: f"{transition.from}_to_{transition.to}",
      type: "state_transition",
      setup: lambda: create_user_with_role(transition.from),
      action: lambda: perform_transition(transition.trigger),
      assert: lambda: user.role == transition.to
    })
  
  # 2. Invalid transition tests (must be rejected)
  for bad in state_machine.invalid_transitions:
    cases.append(TestCase{
      name: f"invalid_{bad.from}_to_{bad.to}",
      type: "invalid_transition",
      setup: lambda: create_user_with_role(bad.from),
      action: lambda: try_transition(bad.to),
      assert: lambda: error_returned and user.role == bad.from  # unchanged
    })
  
  # 3. Permission parametric tests (cross product: role × action)
  roles = ["member", "admin", "superadmin", "disabled"]
  actions = extract_actions_from_spec(spec)
  for role in roles:
    for action in actions:
      expected = spec.permitted(role, action)
      cases.append(TestCase{
        name: f"role_{role}_action_{action}",
        type: "permission",
        setup: lambda: create_user_with_role(role),
        action: lambda: perform_action(action),
        assert: lambda: result == expected
      })
  
  # 4. Edge cases from spec
  for ec in spec.edge_cases:
    cases.append(generate_edge_case_test(ec))
  
  return cases
```

### Step 4: Execute Test Cases

ERS business logic tests run as Go table-driven tests:

```pseudo
func execute_go_parametric_tests(service_path, cases):
  # Generate test file
  test_code = generate_table_driven_test(cases)
  write_to(service_path + "/generated_test.go", test_code)
  
  # Run generated tests
  output = exec("go test ./... -run TestGenerated -v", cwd=service_path)
  
  # Parse results
  results = parse_go_test_output(output)
  
  # Cleanup
  delete(service_path + "/generated_test.go")
  
  return results
```

Generated Go test pattern:
```go
func TestBusinessLogic_UserRoleTransitions(t *testing.T) {
    tests := []struct{
        name     string
        fromRole string
        toRole   string
        wantErr  bool
    }{
        {"member to admin", "member", "admin", false},
        {"admin to disabled", "admin", "disabled", false},
        {"disabled to member", "disabled", "member", false},
        {"invalid: disabled to admin", "disabled", "admin", true},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            user := createTestUser(tt.fromRole)
            err := user.TransitionRole(tt.toRole)
            if (err != nil) != tt.wantErr {
                t.Errorf("TransitionRole() error = %v, wantErr = %v", err, tt.wantErr)
            }
        })
    }
}
```

### Step 5: Test Data Interactions

Cross-service consistency checks (role change → downstream effects):

```pseudo
func test_data_interactions(spec, service_path):
  interactions = []
  
  for each data_interaction in spec.data_interactions:
    # e.g., "role_change_member_to_admin" → check that:
    # 1. {service-name} DynamoDB record updated
    # 2. {service-name} Cognito group membership updated
    # 3. JWT claims reflect new role on next login
    
    result = run_interaction_test(data_interaction)
    interactions[data_interaction.name] = result.status  # PASS/FAIL
  
  return interactions
```

ERS-specific data interactions to test:

| Trigger | Expected Effects |
|---------|-----------------|
| User role: member → admin | Cognito group change, {service-name} record updated |
| User disabled | appAccess = false, Cognito account disabled |
| Email changed | {service-name} + {service-name} both updated, verification sent |
| Membership created | {service-name} MembershipCount incremented |
| CalendarEvent cancelled | Attendees notified ({service-name} triggered) |

### Step 6: Coverage Gap Analysis

```pseudo
func find_uncovered_transitions(state_machine, existing_tests):
  covered = set()
  for test in existing_tests:
    # Find state transition tests already in codebase
    if test.covers_transition(from, to):
      covered.add((from, to))
  
  all_transitions = set((t.from, t.to) for t in state_machine.transitions)
  uncovered = all_transitions - covered
  
  return [f"{f} -> {t}" for (f, t) in uncovered]
```

### Step 7: Gate Decision

```pseudo
gate_result = "PASS"

if failed > 0:
  gate_result = "WARN"

if len(uncovered_transitions) > 0:
  gate_result = "WARN"
  # Note: uncovered transitions are gaps, not failures

if critical_data_interaction_failed:
  gate_result = "BLOCK"  # data consistency failure = block
```

## ERS Business Logic Specifications

### User Role State Machine

```
member ──► admin ──► disabled
  ▲                      │
  └──────────────────────┘
  
INVALID: disabled → admin (must pass through member)
INVALID: member → superadmin (superadmin is manual Cognito setup only)
```

### Membership Status State Machine

```
pending ──► active ──► cancelled
                ▲           │
                └───────────┘ (rejoin creates new pending)
```

### CalendarEvent Status State Machine

```
draft ──► published ──► cancelled
              │
              ▼
           completed (past events auto-transition)
```

### Permission Matrix (ERS OAuth2 scopes)

| Action | member | admin | superadmin |
|--------|--------|-------|------------|
| View events | ✓ | ✓ | ✓ |
| Create event | ✗ | ✓ | ✓ |
| Approve event | ✗ | ✓ | ✓ |
| Approve own event | ✗ | ✗ | ✓ |
| Manage members | ✗ | ✓ | ✓ |
| Disable admin | ✗ | ✗ | ✓ |

## Integration

- Receives low-coverage package list from `test-unit-orchestration`
- Uses mock infrastructure from `test-integration-orchestration`
- Results feed `requirement-mapping` for coverage calculation
- Failed data interaction tests feed `issue-diagnostic-engine`
- State machine gaps become backlog items

## Success Criteria

- Test all valid/invalid role transitions for ERS User model
- Identify permission matrix violations
- Detect cross-service data consistency issues
- Report uncovered state machine transitions
