# ERS Platform — Coding Standards

Quality and consistency guidelines for all ERS services (Go, TypeScript, CDK).

---

## Go Services ({example-service}, {example-service}, {example-service}, {example-service}, {service-name}, {service-name}, {service-name})

### Code Organization

- **Package structure**: `lambda/<service>/` with `main.go`, `handlers.go`, `types.go` as needed
- **No panic in production**: All errors return explicit error values
- **Explicit error handling**: No silent failures or ignored errors
- **Single responsibility**: Functions do one thing well

### Testing

- **Test coverage**: ≥80% for business logic, ≥95% for critical paths
- **Table-driven tests**: Multiple scenarios in one test function
- **Test naming**: `TestXxxBehaviorWhenYyy` (describes what it tests)
- **Integration tests**: Hit real databases (not mocks)
- **Red-Green-Refactor**: Write test first, then code

Example:
```go
func TestValidateJWTAudience(t *testing.T) {
  tests := []struct {
    name    string
    token   string
    wantErr bool
  }{
    {"valid", validToken, false},
    {"missing_aud", tokenNoAud, true},
  }
  for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
      err := validateJWT(tt.token)
      if (err != nil) != tt.wantErr {
        t.Errorf("wanted error=%v, got %v", tt.wantErr, err)
      }
    })
  }
}
```

### Logging

- **Structured JSON logging**, not printf-style debug output
- **No debug logs in production code** (only in tests)
- **Log what matters**: errors, significant state changes, performance warnings
- **Never log secrets**: No API keys, tokens, passwords in logs

Example:
```go
log.Printf(`{"timestamp":"%s","userId":"%s","action":"LOGIN","statusCode":%d}`, 
  time.Now().Format(time.RFC3339), userID, statusCode)
```

### Error Handling

```go
// ✅ Explicit error handling
if err := service.Do(ctx); err != nil {
  return nil, fmt.Errorf("failed to process: %w", err)
}

// ❌ Ignore errors
_ = service.Do(ctx)

// ❌ Panic in production
if err != nil {
  panic(err)
}
```

### Dependencies

- **Go 1.26+** with `GOWORK=off` when building individual services
- **golangci-lint v2** for linting (run in pre-commit hook)
- **Standard library first**: Prefer crypto, net/http, encoding/json over external packages
- **Minimal external deps**: Only add if stdlib doesn't cover it

### File Naming

- `main.go`: Entry point, HTTP handler routing
- `handlers.go`: Business logic handlers
- `types.go`: Domain types and structs
- `*_test.go`: Unit tests (alongside code)

---

## TypeScript / React ({service-name}, {service-name})

### Code Organization

- **Feature-based structure**: `src/features/<feature>/` with components, hooks, tests
- **No `any` types**: Always define types (use generics if needed)
- **Strict mode**: `"strict": true` in tsconfig.json
- **Single responsibility**: Components do one thing

### Testing

- **Vitest + React Testing Library**: Unit tests for all components
- **Test coverage**: ≥80% for business logic
- **User-centric tests**: Test behavior, not implementation details
- **E2E tests**: Playwright for critical workflows (auth, CRUD, navigation)

Example:
```tsx
describe('LoginForm', () => {
  it('submits credentials when form is submitted', async () => {
    render(<LoginForm onLogin={mockFn} />);
    await userEvent.type(screen.getByLabelText(/email/), 'user@example.com');
    await userEvent.type(screen.getByLabelText(/password/), 'password');
    await userEvent.click(screen.getByText(/submit/));
    expect(mockFn).toHaveBeenCalled();
  });
});
```

### Styling

- **Tailwind CSS**: Utility-first approach, no custom CSS files
- **Component-scoped**: Use CSS Modules if needed for complex styles
- **Responsive design**: Mobile-first (sm: 640px, md: 768px, etc.)

### State Management

- **React hooks** (useState, useContext) for local state
- **No Redux unless necessary**: Context API for shared state
- **Suspense & Error Boundaries**: For async data + error handling

### Async Patterns

```ts
// ✅ Proper error handling with abort controller
async function fetchUser(signal: AbortSignal) {
  try {
    const response = await fetch(`/api/users`, { signal });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  } catch (err) {
    if (err instanceof TypeError && err.message.includes('AbortError')) {
      console.log('Request cancelled');
    } else {
      throw err;
    }
  }
}

// ❌ Unhandled promise rejection
fetch(`/api/users`).then(r => r.json());
```

---

## AWS CDK (TypeScript, all stacks)

### Stack Structure

- **One stack per component**: `cdk/stacks/<component>.ts`
- **Constructor params**: Pass required values (API URLs, table names, etc.)
- **Explicit permissions**: Use IAM roles and permission boundaries
- **DLQ for async**: SQS/SNS consumers should have DLQ

Example:
```ts
export class EventStoreStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props: cdk.StackProps & { tableName: string }) {
    super(scope, id, props);
    const table = new ddb.Table(this, 'EventTable', {
      tableName: props.tableName,
      billingMode: ddb.BillingMode.PAY_PER_REQUEST,
      stream: ddb.StreamSpecification.NEW_AND_OLD_IMAGES,
    });
  }
}
```

### CloudFormation Best Practices

- **Immutable infrastructure**: Resources defined in code, not console clicks
- **Secrets**: Use SecretsManager, not hardcoded values
- **Tags**: Add environment, owner, cost-center tags
- **Outputs**: Export critical resource names/ARNs

---

## Shared Standards (All Languages)

### Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| Constants | UPPER_SNAKE_CASE | `MAX_RETRY_ATTEMPTS`, `JWT_EXPIRY_SECONDS` |
| Variables | camelCase | `userEmail`, `isAuthenticated` |
| Functions | camelCase | `validateJWT()`, `handleCreateUser()` |
| Types | PascalCase | `User`, `TokenResponse`, `EventPayload` |
| Files | kebab-case (TS) or snake_case (Go) | `user-profile.tsx`, `main_test.go` |

### Comments

- **Avoid**: "This function validates JWT" (obvious from name)
- **Include**: WHY non-obvious decisions (e.g., "Grace period added for clock skew")
- **Max one line**: Keep it brief

Example:
```go
// Allow 30s grace period for device clock skew (mobile devices often out of sync).
gracePeriod := 30 * time.Second
```

### Imports & Exports

- **Go**: Use `goimports` to auto-organize imports
- **TypeScript**: Import only what you use
- **Cyclic imports**: Avoid (refactor if detected)

### Environment Variables

- **Required env vars**: Checked at startup, fail if missing
- **Optional env vars**: Have sensible defaults
- **Never in code**: All config comes from env or config files

```go
// ✅ Fail on missing required var
requiredVar := os.Getenv("REQUIRED_KEY")
if requiredVar == "" {
  log.Fatalf("REQUIRED_KEY not set")
}

// ✅ Optional with default
optionalVar := os.Getenv("OPTIONAL_KEY")
if optionalVar == "" {
  optionalVar = "default_value"
}

// ❌ Hardcoded value
const apiKey = "sk_test_abc123"
```

---

## Performance & Security

### Performance

- **Caching**: Cache at the right level (HTTP headers, Redis, in-memory)
- **Pagination**: Return max 100 items per request
- **Indexes**: Index frequently-queried fields in DynamoDB
- **Batch operations**: Use batch APIs when available

### Security

- **Input validation**: Validate at system boundaries (API Gateway, user input)
- **SQL injection**: Use parameterized queries (DynamoDB, prepared statements)
- **HTTPS only**: No HTTP in production
- **Authentication**: JWT tokens validated by API Gateway
- **Authorization**: Enforce scopes at handler level (never trust client-provided roles)

### Data Protection

- **PII handling**: Hash emails, phone numbers in logs
- **Secrets**: Use AWS Secrets Manager, not hardcoded values
- **Encryption**: Enable encryption at rest (DynamoDB, S3) and in transit (TLS)

---

## Code Review Checklist

Before committing:

- [ ] Tests pass locally (`make verify`)
- [ ] Coverage ≥80% for changed code
- [ ] No console logs in production code
- [ ] No hardcoded secrets or API keys
- [ ] Types defined (no `any` in TypeScript)
- [ ] Error handling explicit (no silent failures)
- [ ] No commented-out code left behind
- [ ] Follows existing code patterns
- [ ] Commit message explains "why", not "what"

---

## Anti-Patterns (What NOT to Do)

| ❌ Anti-Pattern | ✅ Better Approach |
|---|---|
| `try { ... } catch (e) { }` (silent failure) | Handle error or re-throw with context |
| `if (err) { return nil }` (ignore errors) | Return error, let caller decide |
| `var data any` | Define proper type or use generic |
| `// TODO: fix this later` | Fix now, or create GitHub issue |
| Refactor while fixing bug | Separate commit: fix bug, then refactor |
| Add feature for "future use" | Build what's needed now, extend later |
| Copy-paste code (duplication) | Extract to shared function |
| Large functions (>50 lines) | Break into smaller, focused functions |

---

## Enforcement

- **Pre-commit hook**: Runs lint + test
- **Pre-push hook**: Runs E2E tests ({service-name})
- **Cloud CI**: Full lint, test, code scanning on main
- **Code review**: Manual review before merge (for collaborative work)

Standards are **non-negotiable** for all commits to `main`.
