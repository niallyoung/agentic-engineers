# Design Patterns — ERS Platform

Architectural and implementation patterns established in the ERS platform. Use these patterns before introducing new ones.

---

## Part 1: Go Handler Patterns

### HTTP API Handler Pattern

**Use for:** {service-name}, {service-name}, {service-name}, {service-name} Lambda handlers responding to API Gateway requests.

```go
func (h *Handler) handleCreateUser(ctx context.Context, req *events.APIGatewayProxyRequest) (*events.APIGatewayProxyResponse, error) {
  // 1. Parse request
  var payload CreateUserRequest
  if err := json.Unmarshal([]byte(req.Body), &payload); err != nil {
    return errorResponse(400, fmt.Errorf("invalid request: %w", err)), nil
  }

  // 2. Validate input (domain boundary)
  if err := validateEmail(payload.Email); err != nil {
    return errorResponse(400, err), nil
  }

  // 3. Call service (business logic)
  user, err := h.service.CreateUser(ctx, payload)
  if err != nil {
    // Log and return appropriate HTTP status
    h.logger.Error("CreateUser failed", "error", err)
    return errorResponse(500, err), nil
  }

  // 4. Return success response
  return jsonResponse(200, user), nil
}

// Helper functions
func jsonResponse(statusCode int, body interface{}) *events.APIGatewayProxyResponse {
  data, _ := json.Marshal(body)
  return &events.APIGatewayProxyResponse{
    StatusCode: statusCode,
    Body:       string(data),
    Headers:    map[string]string{"Content-Type": "application/json"},
  }
}

func errorResponse(statusCode int, err error) *events.APIGatewayProxyResponse {
  return jsonResponse(statusCode, map[string]string{"error": err.Error()})
}
```

**Key characteristics:**
- Parse → Validate → Service → Response
- Errors return HTTP status + JSON body (never panic)
- Logging at error boundary (input validation, service failures)
- No business logic in handler; delegate to service

### Event Consumer Pattern (SNS FIFO → SQS FIFO → Lambda)

**Use for:** {service-name}, {service-name}, {service-name} consumers processing domain events.

```go
func (h *Consumer) Handle(ctx context.Context, sqsEvent events.SQSEvent) error {
  for _, message := range sqsEvent.Records {
    // 1. Parse NOSTR event from SQS message
    event, err := parseDomainEvent(message.Body)
    if err != nil {
      h.logger.Error("Failed to parse event", "error", err)
      continue  // Skip malformed event (won't reprocess)
    }

    // 2. Check idempotency (has this event been processed?)
    processed, err := h.idempotency.Exists(ctx, event.ID)
    if err != nil {
      return err  // Retry entire batch (likely transient error)
    }
    if processed {
      continue  // Event already handled, skip it
    }

    // 3. Process event (apply to projection, call external APIs, etc.)
    if err := h.processEvent(ctx, event); err != nil {
      return fmt.Errorf("failed to process event %s: %w", event.ID, err)
    }

    // 4. Mark as processed (idempotency key)
    if err := h.idempotency.Set(ctx, event.ID); err != nil {
      return fmt.Errorf("failed to mark idempotency: %w", err)
    }
  }
  return nil
}

func (h *Consumer) processEvent(ctx context.Context, event DomainEvent) error {
  switch event.Kind {
  case 8801:  // UserCreated
    var payload UserCreated
    if err := json.Unmarshal(event.Content, &payload); err != nil {
      return err
    }
    return h.handleUserCreated(ctx, payload)
  case 8804:  // MembershipCreated
    // ...
  }
  return nil
}
```

**Key characteristics:**
- Parse → Idempotency check → Process → Record idempotency
- Return error to SQS (trigger retry); continue on malformed message
- Idempotency table prevents duplicate processing on retry
- Event-driven, stateless, safe to replay

---

## Part 2: Idempotency & Retry Patterns

### Idempotency Pattern (DynamoDB)

```go
// Store idempotency key after processing
type IdempotencyStore interface {
  Exists(ctx context.Context, eventID string) (bool, error)
  Set(ctx context.Context, eventID string) error
}

// Implementation
func (s *dynamoIdempotency) Set(ctx context.Context, eventID string) error {
  item := map[string]types.AttributeValue{
    "PK":        &types.AttributeValueMemberS{Value: "event#" + eventID},
    "processedAt": &types.AttributeValueMemberN{Value: fmt.Sprintf("%d", time.Now().Unix())},
    "expiresAt": &types.AttributeValueMemberN{Value: fmt.Sprintf("%d", time.Now().Add(30*24*time.Hour).Unix())},
  }
  _, err := s.client.PutItem(ctx, &dynamodb.PutItemInput{
    TableName: aws.String(s.tableName),
    Item:      item,
    TTL:       aws.Int64(int64(time.Now().Add(30 * 24 * time.Hour).Unix())),
  })
  return err
}

func (s *dynamoIdempotency) Exists(ctx context.Context, eventID string) (bool, error) {
  result, err := s.client.GetItem(ctx, &dynamodb.GetItemInput{
    TableName: aws.String(s.tableName),
    Key: map[string]types.AttributeValue{
      "PK": &types.AttributeValueMemberS{Value: "event#" + eventID},
    },
  })
  if err != nil {
    return false, err
  }
  return result.Item != nil, nil
}
```

**Key characteristics:**
- PK = event ID (globally unique)
- TTL = 30 days (can be garbage collected)
- Exists check before processing
- Set call after processing (guard with error check)
- Guarantees: if Set succeeds, event won't reprocess even if function retries

### Retry Pattern (Exponential Backoff)

```go
// Caller retries with exponential backoff
func retryWithBackoff(ctx context.Context, fn func() error, maxRetries int) error {
  for attempt := 0; attempt < maxRetries; attempt++ {
    err := fn()
    if err == nil {
      return nil  // Success
    }

    if attempt < maxRetries-1 {
      backoff := time.Duration(math.Pow(2, float64(attempt))) * time.Second
      select {
      case <-time.After(backoff):
        // Continue to next attempt
      case <-ctx.Done():
        return ctx.Err()
      }
    }
  }
  return fmt.Errorf("max retries exceeded")
}

// Usage
err := retryWithBackoff(ctx, func() error {
  return h.service.UpdateUser(ctx, userID, update)
}, 3)
```

**SQS/Lambda Retry (built-in):**
- Lambda function returns error → SQS re-delivers message
- Configurable max receive count (default 3)
- DLQ: messages after max retries go here (manual inspection)

---

## Part 3: Validation Patterns

### Input Validation (System Boundary)

```go
// {service-name} receives user input; validate here
func (h *Handler) handleCreateUser(ctx context.Context, req CreateUserRequest) (*User, error) {
  // Validate at boundary
  if err := validateCreateUserRequest(req); err != nil {
    return nil, fmt.Errorf("validation failed: %w", err)
  }

  // Pass to service (service can assume valid input)
  return h.service.CreateUser(ctx, req)
}

func validateCreateUserRequest(req CreateUserRequest) error {
  if req.Email == "" {
    return errors.New("email required")
  }
  if !strings.Contains(req.Email, "@") {
    return errors.New("invalid email format")
  }
  if len(req.Email) > 254 {
    return errors.New("email too long (max 254 chars)")
  }
  return nil
}
```

**Key characteristics:**
- Validate at system boundaries (user input, external API responses)
- Return descriptive errors for client feedback
- Service can trust validated input (no defensive checks inside)

### Parameterized Queries (DynamoDB)

```go
// ✅ Correct: Use expression attributes
result, err := client.GetItem(ctx, &dynamodb.GetItemInput{
  TableName: aws.String("users"),
  Key: map[string]types.AttributeValue{
    "PK": &types.AttributeValueMemberS{Value: "user#" + userID},
  },
})

// ✅ Correct: QueryBuilder with expression names/values
query := expression.Key("PK").Equal(expression.Value("user#" + userID)).
         And(expression.Key("email").Equal(expression.Value(email)))
expr, _ := expression.NewBuilder().WithKeyConditionExpression(query).Build()

result, err := client.Query(ctx, &dynamodb.QueryInput{
  TableName:                 aws.String("users"),
  KeyConditionExpression:    expr.KeyCondition(),
  ExpressionAttributeNames:  expr.Names(),
  ExpressionAttributeValues: expr.Values(),
})
```

---

## Part 4: Error Handling Patterns

### Structured Error Logging

```go
// Log contextual information (not secrets)
h.logger.Error("failed to create user",
  "user_id", userID,                    // safe: opaque ID
  "error", err,
  "retry_attempt", attempt,
)

// ❌ Never log: secrets
// h.logger.Error("auth failed", "password", req.Password)
// h.logger.Error("api call", "auth_token", token)
```

### Error Response Mapping

```go
// Map internal errors to HTTP status codes
func toHTTPStatus(err error) (int, string) {
  switch {
  case errors.Is(err, errValidation):
    return 400, "Invalid input"
  case errors.Is(err, errNotFound):
    return 404, "Resource not found"
  case errors.Is(err, errUnauthorized):
    return 401, "Unauthorized"
  case errors.Is(err, errForbidden):
    return 403, "Forbidden"
  default:
    return 500, "Internal server error"
  }
}
```

---

## Part 5: Async Patterns (TypeScript/React)

### API Call with Retry + Token Refresh

```typescript
async function apiCall(method: string, path: string, body?: unknown) {
  let retries = 0;
  const maxRetries = 3;

  while (retries < maxRetries) {
    const response = await fetch(`${API_URL}${path}`, {
      method,
      headers: {
        'Authorization': `Bearer ${await getToken()}`,
        'Content-Type': 'application/json',
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (response.status === 401) {
      // Token expired, refresh and retry
      await refreshToken();
      retries++;
      continue;
    }

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return response.json();
  }

  throw new Error('Max retries exceeded');
}

// Usage
try {
  const user = await apiCall('GET', '/api/users/me');
} catch (err) {
  console.error('Failed to fetch user:', err);
}
```

### React Suspense + Error Boundary

```typescript
function UserProfile() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<Spinner />}>
        <UserData userId={userId} />
      </Suspense>
    </ErrorBoundary>
  );
}

function UserData({ userId }: { userId: string }) {
  // Throw promise while loading
  const user = use(fetchUser(userId));
  return <div>{user.name}</div>;
}

class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return <div>Error: {this.state.error?.message}</div>;
    }
    return this.props.children;
  }
}
```

---

## Part 6: Concurrency Patterns

### Goroutine Sync (WaitGroup)

```go
// Wait for multiple operations to complete
func (h *Handler) syncMultipleSources(ctx context.Context, userID string) error {
  var wg sync.WaitGroup
  errs := make(chan error, 3)

  // Fetch from 3 sources in parallel
  wg.Add(3)

  go func() {
    defer wg.Done()
    if err := h.syncMemberships(ctx, userID); err != nil {
      errs <- fmt.Errorf("sync memberships: %w", err)
    }
  }()

  go func() {
    defer wg.Done()
    if err := h.syncPreferences(ctx, userID); err != nil {
      errs <- fmt.Errorf("sync preferences: %w", err)
    }
  }()

  go func() {
    defer wg.Done()
    if err := h.syncNotifications(ctx, userID); err != nil {
      errs <- fmt.Errorf("sync notifications: %w", err)
    }
  }()

  // Wait for all to complete
  wg.Wait()
  close(errs)

  // Collect errors
  var allErrs []error
  for err := range errs {
    allErrs = append(allErrs, err)
  }

  if len(allErrs) > 0 {
    return fmt.Errorf("sync failed: %w", errors.Join(allErrs...))
  }
  return nil
}
```

### Context Timeout (Deadline)

```go
// Handler enforces timeout
func (h *Handler) handleWithTimeout(ctx context.Context) error {
  ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
  defer cancel()

  // All downstream calls inherit 30s timeout
  return h.service.LongRunningOperation(ctx)
}

// Service respects deadline
func (s *Service) LongRunningOperation(ctx context.Context) error {
  select {
  case result := <-s.doAsyncWork():
    return result
  case <-ctx.Done():
    return fmt.Errorf("operation timeout: %w", ctx.Err())
  }
}
```

---

## Part 7: Caching Patterns

### In-Memory Cache (Thread-Safe)

```go
type Cache struct {
  mu    sync.RWMutex
  items map[string]CacheItem
  ttl   time.Duration
}

type CacheItem struct {
  value     interface{}
  expiresAt time.Time
}

func (c *Cache) Get(key string) (interface{}, bool) {
  c.mu.RLock()
  defer c.mu.RUnlock()

  item, ok := c.items[key]
  if !ok || time.Now().After(item.expiresAt) {
    return nil, false
  }
  return item.value, true
}

func (c *Cache) Set(key string, value interface{}) {
  c.mu.Lock()
  defer c.mu.Unlock()

  c.items[key] = CacheItem{
    value:     value,
    expiresAt: time.Now().Add(c.ttl),
  }
}
```

### Redis Cache (External)

```go
func (h *Handler) GetUserWithCache(ctx context.Context, userID string) (*User, error) {
  // Try cache first
  cached, err := h.redis.Get(ctx, "user:"+userID).Result()
  if err == nil {
    var user User
    json.Unmarshal([]byte(cached), &user)
    return &user, nil
  }

  // Cache miss or error, fetch from DB
  user, err := h.db.GetUser(ctx, userID)
  if err != nil {
    return nil, err
  }

  // Store in cache (fire-and-forget, don't block on cache write)
  data, _ := json.Marshal(user)
  h.redis.Set(ctx, "user:"+userID, data, 1*time.Hour)

  return user, nil
}
```

---

## Part 8: Pagination Pattern

```go
// Query with pagination
func (h *Handler) ListUsers(ctx context.Context, limit int, cursor string) (*UsersPage, error) {
  if limit > 100 {
    limit = 100  // Cap at 100 items per request
  }

  // Query limit+1 to detect if there's a next page
  users, err := h.db.ListUsers(ctx, limit+1, cursor)
  if err != nil {
    return nil, err
  }

  hasMore := len(users) > limit
  if hasMore {
    users = users[:limit]  // Trim to requested limit
  }

  // Return cursor for next page (last user's ID)
  var nextCursor string
  if hasMore && len(users) > 0 {
    nextCursor = users[len(users)-1].ID
  }

  return &UsersPage{
    Users:      users,
    HasMore:    hasMore,
    NextCursor: nextCursor,
  }, nil
}

// Client usage
type UsersPage struct {
  Users      []User
  HasMore    bool
  NextCursor string
}
```

---

## Part 9: Testing Patterns

### Table-Driven Tests (Go)

```go
func TestValidateEmail(t *testing.T) {
  tests := []struct {
    name    string
    email   string
    wantErr bool
  }{
    {"valid", "alice@example.com", false},
    {"missing @", "alice.example.com", true},
    {"empty", "", true},
    {"too long", strings.Repeat("a", 255) + "@example.com", true},
  }

  for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
      err := validateEmail(tt.email)
      if (err != nil) != tt.wantErr {
        t.Errorf("validateEmail(%q) = %v, want error=%v", tt.email, err, tt.wantErr)
      }
    })
  }
}
```

### React Testing Library

```typescript
import { render, screen, userEvent } from '@testing-library/react';
import { LoginForm } from './LoginForm';

test('user can log in with valid credentials', async () => {
  const handleLogin = vi.fn();
  render(<LoginForm onLogin={handleLogin} />);

  await userEvent.type(screen.getByLabelText(/email/i), 'alice@example.com');
  await userEvent.type(screen.getByLabelText(/password/i), 'Password123!');
  await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

  expect(handleLogin).toHaveBeenCalledWith({
    email: 'alice@example.com',
    password: 'Password123!',
  });
});
```

---

## Part 10: Anti-Patterns (Avoid These)

| ❌ Anti-Pattern | ✅ Better Approach |
|---|---|
| Panic in production | Return error, let caller decide |
| Silent error catch (`_ = fn()`) | Handle or return error explicitly |
| Large monolithic functions (>100 LOC) | Extract into focused functions |
| Hardcoded values in code | Environment variables or config |
| Calling sleep() for synchronization | Use channels, sync.Cond, wait strategies |
| Unversioned APIs | Version from day 1 (v1, v2) |
| Storing secrets in logs | Hash/redact before logging |
| Modifying shared state without locks | Use sync.Mutex, channels, or immutability |
| Nested callbacks (callback hell) | Use async/await, channels, or promises |
| Testing implementation details | Test user behavior/outcomes |

---

## Summary

**Key Principles:**

1. **Layers:** Boundary validation → Business logic → Data persistence
2. **Idempotency:** Always check before processing, record after success
3. **Errors:** Return explicitly, log at boundaries, map to HTTP status
4. **Concurrency:** Use sync primitives (WaitGroup, Mutex, Channel) correctly
5. **Caching:** Cheap, single-source-of-truth, TTL-based eviction
6. **Testing:** Table-driven, user-centric, fast, high coverage
7. **Async:** Retry with backoff, handle cancellation, use Suspense

Apply these patterns before introducing new ones. Consistency over novelty.
