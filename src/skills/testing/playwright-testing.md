# Playwright Testing Skill

**Shared by:** Engineer (test development), Quality Engineer (test execution & validation)

Playwright is the primary E2E testing framework for {service-name} (React/TypeScript frontend). Use this skill when writing, running, or debugging Playwright tests.

---

## Part 1: Test Development (Engineer Focus)

**Model:** claude-haiku-4.5 | **Effort:** medium | **Token Multiplier:** ~2x

### What Engineer DOES

- ✅ Writes behavior-driven E2E tests in Playwright (TypeScript)
- ✅ Focuses on **user-centric features**: login, signup, CRUD workflows, navigation, permissions
- ✅ Tests **outcomes not implementation**: "user can create membership" not "button has className=create-btn"
- ✅ Uses page object models (POM) for maintainability and reuse
- ✅ Validates happy path + critical error cases (missing field, network timeout, permission denied)
- ✅ Integrates with Vitest test runner (same as unit tests)
- ✅ Runs full test suite locally before commit (pre-push hook with `CI=true`)
- ✅ Debugs test flakiness: retry logic, wait strategies, fixture state isolation
- ✅ Reports test results and coverage to Quality Engineer

### What Engineer DOES NOT DO

- ❌ Does not test visual appearance (screenshots, pixel matching, CSS assertions)
- ❌ Does not hardcode selectors (uses data-testid, accessible names, roles)
- ❌ Does not skip authentication (tests must go through real login when needed)
- ❌ Does not use sleep() for waiting (uses Playwright wait strategies)
- ❌ Does not test implementation details (component internals, prop drilling)
- ❌ Does not modify business logic while writing tests (TDD: test-first)

---

## Part 2: Test Execution & Validation (Quality Engineer Focus)

**Model:** claude-sonnet-4.6 | **Effort:** medium

### What Quality Engineer DOES

- ✅ Runs the full E2E suite in CI-equivalent mode (`CI=true`)
- ✅ Writes new Playwright tests using the fixture-based pattern (complements Engineer work)
- ✅ Debugs failures with trace viewer, headed mode, and log inspection
- ✅ Maintains test data fixtures (static JSON + dynamic generators)
- ✅ Validates all test results before accepting HANDBACK
- ✅ Reports test status and coverage as part of Tier 1 quality gate

### What Quality Engineer DOES NOT DO

- ❌ Does not modify `playwright.config.ts` without escalating (config affects all CI runs)
- ❌ Does not skip test failures as "acceptable flakiness" — all failures must be investigated
- ❌ Does not approve code with failing tests
- ❌ Does not write unit tests (that is Engineer's responsibility, via vitest)

---

## Playwright Setup ({service-name})

### Installation

```bash
npm install --save-dev @playwright/test
npx playwright install
```

### Configuration (playwright.config.ts)

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './src/**/*.e2e.test.ts',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173', // Vite dev server
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
  ],
});
```

### npm scripts (package.json)

```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:debug": "playwright test --debug",
    "test:e2e:headed": "playwright test --headed"
  }
}
```

---

## Test Structure: Page Object Model (POM)

Separate test logic from selectors using POM — enables selector updates without touching test code.

### Example: Login Page Object

```typescript
// src/pages/LoginPage.ts
import { Page, Locator } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly errorAlert: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page.getByLabel('Email');
    this.passwordInput = page.getByLabel('Password');
    this.submitButton = page.getByRole('button', { name: /sign in/i });
    this.errorAlert = page.getByRole('alert');
  }

  async goto() {
    await this.page.goto('/login');
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }

  async expectErrorMessage(message: string) {
    await expect(this.errorAlert).toContainText(message);
  }
}
```

### Example: Test Using Page Object

```typescript
// src/auth/login.e2e.test.ts
import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

test.describe('Login Flow', () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
  });

  test('User can login with valid credentials', async ({ page }) => {
    await loginPage.login('user@example.com', 'validPassword123');
    await expect(page).toHaveURL('/dashboard');
  });

  test('User sees error with invalid credentials', async () => {
    await loginPage.login('user@example.com', 'wrongPassword');
    await loginPage.expectErrorMessage('Invalid email or password');
  });

  test('User must enter both email and password', async () => {
    await loginPage.emailInput.fill('user@example.com');
    await loginPage.submitButton.click();
    await loginPage.expectErrorMessage('Password is required');
  });
});
```

---

## Running E2E Tests

### Matching CI Exactly (CI=true)

**This is the correct way to validate locally before commit:**

```bash
CI=true npx playwright test
```

This gives you:
- **4 browser projects**: chromium, firefox, webkit, mobile-chrome
- **2 retries** on failure (with trace on first retry)
- **1 worker** (serial execution, deterministic)
- **Fresh dev server** (`reuseExistingServer: false`)

### Fast Local Iteration (without CI=true)

```bash
npx playwright test
```

Only runs chromium + mobile-chrome, parallel workers, no retries, reuses server. **Fast but NOT equivalent to CI — use only for quick iteration, never for validation.**

### Common Variations

```bash
# Single test file
CI=true npx playwright test e2e/tests/feature/my-test.spec.ts

# Single browser
CI=true npx playwright test --project=chromium

# Headed mode (watch browser)
CI=true npx playwright test --headed

# UI mode (interactive debugging)
npx playwright test --ui

# Via Makefile (check project's targets)
make e2e           # full suite
make e2e.ui        # UI mode
make e2e.smoke     # smoke tests only
```

### Prerequisites

All browsers must be installed:

```bash
npx playwright install
npx playwright install-deps  # Install system dependencies (Linux only)
```

---

## Debugging Test Failures

### Trace Viewer (Inspector)

When `CI=true` and a test fails on first retry, Playwright saves a trace automatically:

```bash
npx playwright show-trace trace.zip
```

Opens interactive trace viewer showing:
- Step-by-step action replay
- DOM state at each step
- Network requests
- Console logs

### Headed Mode (Watch Browser)

Run with `--headed` to watch the browser while tests execute:

```bash
npx playwright test --headed
npx playwright test --headed --project=chromium
```

### UI Mode (Interactive Debugging)

Best for iterating on test logic:

```bash
npx playwright test --ui
```

Provides:
- Run individual tests
- Pause and step through
- Inspect locators
- Live picker for selectors

### Common Debugging Steps

1. **Test fails locally but passes in CI?**
   - Likely timing issue or data state inconsistency
   - Run with `CI=true` to match CI environment
   - Check fixture setup and teardown

2. **Flaky test (sometimes passes, sometimes fails)?**
   - Use Playwright wait strategies (avoid `sleep()`)
   - Increase retries in config if acceptable
   - Inspect trace to find timing gaps

3. **Can't find element?**
   - Use Playwright Inspector to pick the right locator
   - Prefer semantic locators: `getByLabel`, `getByRole`, `getByText`
   - Only use `data-testid` for hard-to-target elements

4. **Test passes locally, fails in CI?**
   - Check for timezone/locale differences
   - Verify test data fixtures exist in CI environment
   - Run `CI=true` locally to reproduce

---

## Fixture Management

### Static Test Data

```typescript
// src/fixtures/testData.ts
export const testUsers = {
  admin: {
    email: 'admin@example.com',
    password: process.env.TEST_ADMIN_PASSWORD || 'AdminPass123!',
  },
  member: {
    email: 'member@example.com',
    password: process.env.TEST_MEMBER_PASSWORD || 'MemberPass123!',
  },
};

export const testEvents = [
  { name: 'Derby 101', date: '2026-05-15', location: 'Central Park' },
  { name: 'Roller Derby Tournament', date: '2026-06-20', location: 'Brooklyn' },
];
```

### Dynamic Fixtures (API)

```typescript
// src/fixtures/api.ts
export async function createTestUser(api: APIRequestContext, overrides = {}) {
  const response = await api.post('/api/users', {
    data: {
      email: `test-${Date.now()}@example.com`,
      givenName: 'Test',
      familyName: 'User',
      ...overrides,
    },
  });
  return response.json();
}
```

---

## Playwright vs Other Tools

| Tool | Use Case | Playwright Alternative |
|------|----------|----------------------|
| Vitest | Unit tests | N/A (different tool) |
| Playwright | E2E tests (this skill) | ✓ What we use |
| Cypress | E2E (older alternative) | Replaced by Playwright |
| Jest | Testing framework | Replaced by Vitest |

**Bottom line:** Playwright only for E2E (user workflows). Unit tests use Vitest. Integration tests use Playwright with real API.

---

## Quality Checklist

**Before Engineer submits HANDBACK:**
- ✅ All new E2E tests pass with `CI=true`
- ✅ Tests use POM pattern, not hardcoded selectors
- ✅ Tests focus on user behavior, not implementation
- ✅ No `sleep()` calls (use wait strategies instead)
- ✅ Test data is reusable and isolatable

**Before Quality Engineer accepts HANDBACK:**
- ✅ Run full test suite: `CI=true npx playwright test`
- ✅ All browsers pass (chromium, firefox, webkit, mobile)
- ✅ No new test flakiness introduced
- ✅ Coverage metrics acceptable (check `playwright-report/`)
- ✅ Document any test skips or known flakiness

---

## See Also

- `shared/git-workflow.md` — Pre-push hook runs `CI=true` E2E suite
- `orchestration/QUALITY.md` — Tier 1 gate includes E2E test results
- Root `CLAUDE.md` — {service-name} architecture and testing strategy
