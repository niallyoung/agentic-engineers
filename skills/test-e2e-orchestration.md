---
name: test-e2e-orchestration
description: Orchestrate Playwright E2E tests for {service-name} with scenario filtering
type: skill
version: 1.0
track: testing
---

# test-e2e-orchestration

Run Playwright E2E tests for {service-name} with scenario filtering, parallel execution, and
trace capture on failure. Integrates with the ERS pre-push hook and quality gate.

## Usage

```
/test-e2e-orchestration
/test-e2e-orchestration scenario_filter=login
/test-e2e-orchestration scenario_filter=create_event parallel_workers=4
/test-e2e-orchestration headless=false trace_on_failure=true
```

## Input

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scenario_filter` | str | null | Filter by scenario name (e.g., `login`, `create_event`) |
| `headless` | bool | true | Run browser in headless mode |
| `trace_on_failure` | bool | true | Capture Playwright trace on test failure |
| `parallel_workers` | int | 2 | Number of parallel test workers |
| `base_url` | str | from env | Override test base URL |
| `timeout_sec` | int | 300 | Max total execution time |

## Output

```json
{
  "scenarios_found": 8,
  "scenarios_run": 3,
  "passed": 3,
  "failed": 0,
  "skipped": 0,
  "execution_time_sec": 125,
  "parallel_workers": 2,
  "base_url": "http://localhost:5173",
  "traces": [],
  "screenshots": [],
  "failed_scenarios": [],
  "gate_result": "PASS"
}
```

Failure example:
```json
{
  "scenarios_found": 8,
  "scenarios_run": 8,
  "passed": 6,
  "failed": 2,
  "failed_scenarios": [
    {
      "name": "admin can approve calendar event",
      "file": "e2e/calendar.spec.ts:45",
      "error": "Timeout: element 'button[data-testid=approve-btn]' not found",
      "trace": "test-results/trace-calendar-approve.zip",
      "screenshot": "test-results/screenshot-calendar-approve.png"
    }
  ],
  "gate_result": "WARN"
}
```

## Implementation

### Step 1: Locate E2E Tests

```pseudo
func discover_e2e_tests(app_path):
  # {service-name} standard: tests in e2e/ directory
  e2e_dir = app_path + "/e2e"
  if not exists(e2e_dir):
    e2e_dir = app_path + "/tests/e2e"
  
  spec_files = find(e2e_dir, "*.spec.ts") + find(e2e_dir, "*.spec.tsx")
  
  scenarios = []
  for file in spec_files:
    # Parse: test('scenario name', ...) or it('scenario name', ...)
    names = regex_find(r"(?:test|it)\(['\"](.+?)['\"]", read(file))
    scenarios += [{ name: n, file: file } for n in names]
  
  return scenarios
```

### Step 2: Apply Scenario Filter

```pseudo
func filter_scenarios(scenarios, filter):
  if filter is None:
    return scenarios
  
  # Exact match first
  exact = [s for s in scenarios if filter.lower() in s.name.lower()]
  if exact:
    return exact
  
  # Fuzzy: split by underscore/space and match all words
  words = filter.replace("_", " ").lower().split()
  return [s for s in scenarios if all(w in s.name.lower() for w in words)]
```

ERS scenario names (from {service-name}/e2e/):
- `login` — user authentication flow
- `create_event` or `calendar` — calendar event creation
- `member_registration` — new member signup
- `admin_dashboard` — admin panel access
- `profile_update` — user profile editing
- `group_management` — group CRUD operations

### Step 3: Configure Playwright

```pseudo
func build_playwright_config(params):
  return {
    workers: params.parallel_workers,
    headless: params.headless,
    use: {
      baseURL: params.base_url or env.PLAYWRIGHT_BASE_URL or "http://localhost:5173",
      video: "retain-on-failure",
      screenshot: "only-on-failure",
      trace: "retain-on-failure" if params.trace_on_failure else "off"
    },
    reporter: [["json", { outputFile: "test-results/results.json" }], ["list"]],
    timeout: 30000,  # 30s per test
    retries: 1  # 1 retry for flaky network tests
  }
```

### Step 4: Start Dev Server (if needed)

```pseudo
func ensure_dev_server(app_path, base_url):
  if base_url is explicitly provided:
    verify_reachable(base_url)
    return None  # use existing server
  
  # Check if already running
  if port_open(5173):
    return None
  
  # Start {service-name} dev server
  server_proc = spawn("npm run dev", cwd=app_path, env={NODE_ENV: "test"})
  wait_until_ready("http://localhost:5173", timeout=30)
  return server_proc  # caller must stop after tests
```

### Step 5: Execute Tests

```bash
cd {app_path}

# Run all:
npx playwright test --workers={workers} --reporter=json 2>&1

# Run filtered (by scenario name):
npx playwright test --grep "{scenario_filter}" --workers={workers} --reporter=json 2>&1

# Run specific file:
npx playwright test e2e/{file}.spec.ts --workers={workers} 2>&1
```

ERS standard (uses `make` when available):
```bash
# From {service-name} pre-push hook pattern:
make e2e-headless  # or npm run test:e2e
```

### Step 6: Parse Results

```pseudo
func parse_playwright_results(results_json):
  data = load_json("test-results/results.json")
  
  passed = sum(s.status == "passed" for s in data.suites.specs)
  failed = sum(s.status == "failed" for s in data.suites.specs)
  
  failures = []
  for spec in data.suites.specs where status == "failed":
    trace_file = find_trace_file(spec.title)
    screenshot = find_screenshot(spec.title)
    failures.append({
      name: spec.title,
      file: spec.file + ":" + spec.line,
      error: spec.tests[0].results[0].error.message,
      trace: trace_file,
      screenshot: screenshot
    })
  
  return { passed, failed, failures, execution_time: data.stats.duration / 1000 }
```

### Step 7: Gate Decision

```pseudo
gate_result = "PASS"

if failed > 0:
  # E2E failures are serious but may be flaky infra
  if failed / scenarios_run > 0.25:  # >25% failure rate
    gate_result = "BLOCK"
  else:
    gate_result = "WARN"

# Expensive: E2E only blocks prod deployments
# For dev deployments: WARN is acceptable
```

## ERS-Specific Patterns

### {service-name} Playwright Setup

```typescript
// e2e/fixtures.ts — ERS test fixture pattern
import { test as base } from '@playwright/test';

export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    // Login via Cognito test user
    await page.goto('/login');
    await page.fill('[data-testid=email]', process.env.TEST_USER_EMAIL);
    await page.fill('[data-testid=password]', process.env.TEST_USER_PASSWORD);
    await page.click('[data-testid=login-button]');
    await page.waitForURL('/dashboard');
    await use(page);
  }
});
```

### Test Environment Requirements

```bash
# Required env vars for E2E tests:
PLAYWRIGHT_BASE_URL=http://localhost:5173
TEST_USER_EMAIL=e2e-test@evolutionrollersports.com
TEST_USER_PASSWORD=<test-user-password>
TEST_ADMIN_EMAIL=e2e-admin@evolutionrollersports.com
```

### Running Against Dev Environment

```bash
# Run E2E against live dev environment:
PLAYWRIGHT_BASE_URL=https://dev.evolutionrollersports.com \
npx playwright test --workers=1  # serial against live env
```

## Integration

- Called by `quality-gate-orchestration` as the most expensive test tier
- Only run full suite on pre-push; filter to `smoke` scenarios for PR checks
- Trace files uploaded to S3 for post-mortem analysis
- Failed scenarios feed `issue-diagnostic-engine` for UI failure analysis
- ERS pre-push hook already runs `make e2e-headless` — this skill wraps that

## Success Criteria

- Discover all Playwright spec files in {service-name}/e2e/
- Filter and run "login" scenario in <60 seconds
- Capture trace zip on failure
- Report correct pass/fail counts with file:line references
