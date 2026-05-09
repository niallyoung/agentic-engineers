---
name: test-unit-orchestration
description: Orchestrate unit test discovery, execution, and coverage reporting for ERS services
type: skill
version: 1.0
track: testing
---

# test-unit-orchestration

Discover, execute, and report on unit tests for any ERS service. Detects test framework (Go/Jest),
runs tests, parses coverage, and returns structured results for the quality gate.

## Usage

```
/test-unit-orchestration service_path={workspace-root}/{service-name}
/test-unit-orchestration service_path={service-name} coverage_threshold=85
/test-unit-orchestration service_path={service-name} test_filter="*/auth/*"
```

## Input

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `service_path` | str | required | Absolute or relative path to service root |
| `test_filter` | str | null | Glob pattern to filter tests (e.g., `*/handlers/*_test.go`) |
| `coverage_threshold` | int | 80 | Minimum coverage % to pass |
| `fail_on_below_threshold` | bool | true | Fail gate if coverage < threshold |

## Output

```json
{
  "service": "{service-name}",
  "language": "go",
  "tests_found": 42,
  "tests_passed": 40,
  "tests_failed": 2,
  "tests_skipped": 0,
  "coverage_percent": 82.5,
  "coverage_threshold": 80,
  "coverage_status": "PASS",
  "execution_time_sec": 12.4,
  "failed_tests": [
    {
      "name": "TestCreateUser_MissingEmail",
      "file": "handlers/user_test.go:84",
      "error": "expected status 400, got 200"
    }
  ],
  "low_coverage_packages": [
    { "package": "{service-name}/internal/auth", "coverage": 62.0 }
  ],
  "mutation_recommendations": [
    "Add edge case: empty tags array in CreateCalendarEvent",
    "Test negative user ID rejection in UpdateUser"
  ],
  "gate_result": "WARN"
}
```

`gate_result`: `PASS` | `WARN` | `BLOCK`

## Implementation

### Step 1: Detect Language & Framework

```pseudo
func detect_framework(service_path):
  if exists(service_path + "/go.mod"):
    return "go"
  if exists(service_path + "/package.json"):
    check package.json "scripts.test" for jest/vitest/playwright
    return "node"
  if exists(service_path + "/requirements.txt"):
    return "python"
  error("Cannot detect test framework")
```

### Step 2: Discover Tests

**Go:**
```bash
find {service_path} -name "*_test.go" -not -path "*/vendor/*"
# Count test functions:
grep -r "^func Test" {service_path} --include="*_test.go" | wc -l
```

**Node/Jest:**
```bash
find {service_path} -name "*.test.ts" -o -name "*.test.tsx" -o -name "*.spec.ts"
# Count: grep -r "^it\|^test\|^describe" --include="*.test.*" | wc -l
```

### Step 3: Execute Tests

**Go (ERS standard):**
```bash
cd {service_path}
go test ./... -v -coverprofile=coverage.out -covermode=atomic 2>&1
go tool cover -func=coverage.out
```

With filter:
```bash
go test ./... -run {test_filter} -v -coverprofile=coverage.out 2>&1
```

**Node ({service-name}):**
```bash
cd {service_path}
npm test -- --coverage --json --outputFile=test-results.json 2>&1
```

ERS standard: `make test` if Makefile exists, falling back to direct commands.

### Step 4: Parse Coverage

**Go coverage parsing:**
```pseudo
func parse_go_coverage(coverage_output):
  lines = coverage_output.split("\n")
  total_line = lines.find(l => l.startswith("total:"))
  # format: "total:                    (statements)          82.5%"
  coverage_pct = extract_float(total_line)
  
  per_package = {}
  for line in lines:
    if line.contains("github.com/"):
      pkg, pct = parse_package_line(line)
      per_package[pkg] = pct
  
  return { total: coverage_pct, packages: per_package }
```

**Jest coverage parsing:**
```pseudo
parse jest coverage JSON from test-results.json
extract: numTotalTests, numPassedTests, numFailedTests
extract: coverageSummary.total.lines.pct
```

### Step 5: Identify Failed Tests

```pseudo
func parse_failures(test_output, language):
  if language == "go":
    # Lines starting with "--- FAIL:"
    failures = regex_find("--- FAIL: (\\S+) \\(", test_output)
    for each failure:
      find the error message (lines between FAIL marker and next test)
      find file:line from runtime error
  
  if language == "node":
    # Parse jest JSON output failures array
    failures = test_results.testResults
      .filter(r => r.status == "failed")
      .map(r => r.failureMessages)
  
  return failures
```

### Step 6: Mutation Recommendations

After coverage analysis, examine low-coverage packages:
```pseudo
for pkg in packages where coverage < 70%:
  read pkg source files
  identify: exported functions with no test, complex conditionals, error paths
  generate recommendation: "Add test for {function} - {reason}"
  limit: 5 recommendations max
```

### Step 7: Gate Decision

```pseudo
gate_result = "PASS"

if tests_failed > 0:
  gate_result = "BLOCK"

elif coverage_percent < coverage_threshold and fail_on_below_threshold:
  gate_result = "WARN"  # WARN not BLOCK for coverage (business decision)

return gate_result
```

## ERS-Specific Notes

### {service-name} (Go)
```bash
cd {workspace-root}/{service-name}
make test
# Runs: go test ./... -v -coverprofile=coverage.out
```

Expected: >30 tests, ~80% coverage. Key packages to check:
- `internal/handlers` — command routing (CreateUser, UpdateUser, etc.)
- `internal/auth` — JWT validation
- `internal/event` — event publishing to {service-name}

### {service-name} (Go)
```bash
cd {workspace-root}/{service-name}
make test
```

Key test coverage: membership state transitions, DynamoDB projections, SNS event consumers.

### {service-name} (Node/Vitest)
```bash
cd {workspace-root}/{service-name}
npm test -- --coverage
```

Key test coverage: auth flows, API client retry logic, form validation.

## Integration

- Called by `quality-gate-orchestration` in parallel with `test-integration-orchestration`
- Failed tests passed to `issue-diagnostic-engine` for root cause analysis
- Coverage report stored for trend tracking
- Low coverage packages fed to `test-business-logic` for gap analysis

## Success Criteria

- Discover all test files in target service
- Execute `make test` or equivalent and capture output
- Parse coverage to 1 decimal place
- List all failed tests with file:line references
- Gate decision correctly blocks on test failures
