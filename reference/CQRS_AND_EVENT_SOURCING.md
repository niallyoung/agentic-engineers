# CQRS & Event Sourcing — ERS Architecture Reference

Comprehensive guide to command-query responsibility segregation (CQRS) and event sourcing patterns used in the ERS platform. For architects, lead engineers, and planners designing new services or extending existing patterns.

---

## Part 1: Foundational Concepts

### CQRS: Command-Query Responsibility Segregation

Separates write operations (commands) from read operations (queries) into distinct code paths and services.

**Why CQRS for ERS:**
- Writes ({example-service}) publish domain events; reads ({example-service}) consume projections
- Scales independently: heavy write load doesn't block heavy read load
- Clear separation of concerns: command validation vs. query optimization
- Enables event-driven architecture and replay/projection rebuild

**Command Flow (Write Path):**
```
{service-name} (user action)
  → {example-service} (HTTP API)
  → validate input, apply business rules
  → publish domain event to {example-service} (Event Store)
  → return success response to {service-name}
```

**Query Flow (Read Path):**
```
{service-name} (user requests data)
  → {example-service} (HTTP API)
  → read from {service-name} projection (DynamoDB)
  → return denormalized data to {service-name}
```

**Key Principle:** Event Store ({example-service}) is the source of truth; projections ({service-name}, {example-service}) are derived read models built by consuming events. Never query the Event Store for application read operations—use projections instead.

---

## Part 2: Event Sourcing

Event Sourcing stores the complete history of state changes as immutable events. Rather than storing current state, every domain event is persisted. Current state is reconstructed by replaying events from the beginning.

### Domain Events vs. Commands

| Aspect | Command (20100-20199) | Domain Event (8801-8899) |
|--------|------------|--------|
| **Lifetime** | Ephemeral (request-scoped) | Permanent (stored forever) |
| **Storage** | Not stored in Event Store | Immutable log in DynamoDB |
| **Consumption** | Request/response only | Consumed by all projections |
| **Authority** | User request | Source of truth |
| **Example** | `CreateUser {email, name, phone}` | `UserCreated {userId, email, name, phone}` |

### Event Schema Versioning

All domain events follow **version "1.0"** as the launch baseline.

**Versioning Rules:**
- The `version` field lives **inside** the event's content JSON, not the NOSTR envelope
- Any breaking change to an event schema (removing fields, changing types) requires a new version
- **All previous versions must be supported permanently**
- The entire EventStore stream must be replayable at any time to rebuild projections

**Example: UserCreated Event**
```json
{
  "kind": 8801,
  "content": {
    "version": "1.0",
    "userId": "user_123",
    "email": "alice@example.com",
    "givenName": "Alice",
    "familyName": "Smith",
    "phone": "+61234567890",
    "created_at": "2026-04-24T12:34:56Z"
  },
  "pubkey": "",
  "sig": ""
}
```

**Adding a Non-Breaking Field (v1.0 compatible):**
If adding optional field `preferredLanguage`, keep version "1.0" — old events without it still parse correctly.

**Breaking Change (requires v1.1):**
If changing `email` type from string to object `{address, verified}`, create a v1.1 consumer that handles both formats.

### Event Store Design ({example-service})

**Role:** Immutable append-only log of all domain events. Single source of truth.

**Storage:** DynamoDB with S3 archive
- `PK`: `event#{eventId}` (globally unique, collision-resistant)
- `SK`: timestamp (for ordering within a partition)
- `GSI`: `entityId` → all events for a user/resource (rebuild projection for one entity)
- `content`: Full NOSTR event JSON (including nested content with schema version)
- `metadata`: `{eventIntegrityHash, EventType, EntityType}` (for validation + queries)

**Immutability Guarantee:**
- Events never modified (no UpdateItem on event record)
- Corrections handled via new events (e.g., `UserEmailCorrected` for a fix)
- DynamoDB TTL: none (events kept forever)

**API ({example-service}):**
- `POST /events` — Publish domain event ({example-service} only, SigV4 auth)
- `GET /events?entityId=user_123` — Query events for one entity
- `GET /events?kind=8801` — Query events by type (internal/batch operations)

---

## Part 3: Projection Pattern

Projections are read-optimized views built by consuming domain events. They denormalize data for fast queries.

### {service-name}: User & Organization Projections

**What it stores:**
- User master record: `{userId, email, phone, givenName, familyName, appAccess, ...}`
- Organization record: `{orgId, orgName, ...}`
- Membership projections: `{userId, orgId, role, joinedAt, ...}`

**How it's built:**
1. Consumer listens to SNS FIFO topic ({example-service} publishes here after storing event)
2. Receives events (UserCreated 8801, UserUpdated 8802, MembershipCreated 8804, etc.)
3. Applies event to DynamoDB using idempotent write:
   - Check idempotency key (event ID) — if already processed, skip
   - Apply the event (UpdateItem or PutItem)
   - Store idempotency key to prevent re-processing

**Example: Process UserCreated Event**
```go
// Consumer receives event
event := DomainEvent{Kind: 8801, Content: UserCreated{...}}

// Check idempotency
if h.idempotency.Exists(ctx, event.ID) {
  return nil  // Already processed
}

// Apply event to projection
user := User{
  UserID:    event.Content.UserID,
  Email:     event.Content.Email,
  Phone:     event.Content.Phone,
  CreatedAt: event.Content.CreatedAt,
}
if err := h.members.PutUser(ctx, user); err != nil {
  return err  // Retry (SQS will re-deliver)
}

// Mark as processed
return h.idempotency.Set(ctx, event.ID)
```

**Idempotency Pattern:**
- DynamoDB table: `PK=eventId`, `TTL=30 days` (can be garbage collected)
- Before processing: `GetItem(eventId)` — if exists, skip
- After processing: `PutItem(eventId, processedAt)` — marks event as handled
- Guarantees: If consumer crashes after PutItem, replay won't re-apply the event

### {example-service}: Cognito Identity Projection

**What it stores:**
- Cognito user attributes: `{email, phone, givenName, familyName, appAccess}`
- Source of truth for app login
- Mirrors {service-name} (single-source-of-truth is {service-name}; {example-service} keeps Cognito in sync)

**How it's built:**
1. Consumer receives UserCreated, UserUpdated events
2. Calls Cognito AdminCreateUser / AdminUpdateUser
3. Stores idempotency key to prevent duplicate accounts

**Special Behavior: Replay Mode**
When rebuilding from scratch (`REPLAY_MODE=true`):
- Idempotency checks are **skipped**
- Side-effecting calls (AdminCreateUser, email sends) are **skipped** (only update local projection)
- Full stream is replayed, projections rebuilt from scratch

---

## Part 4: Event Flow Architecture

### Publishing Events

**1. Command Handler publishes domain event:**
```go
// {example-service}/handlers.go
func (h *Handler) handleCreateUser(ctx context.Context, req CreateUserRequest) (*UserResponse, error) {
  // Validate input
  if err := validateEmail(req.Email); err != nil {
    return nil, err
  }
  
  // Generate user ID
  userID := uuid.New().String()
  
  // Create domain event
  event := DomainEvent{
    Kind:    8801,  // UserCreated
    Content: UserCreated{
      Version:   "1.0",
      UserID:    userID,
      Email:     req.Email,
      Phone:     req.Phone,
      GivenName: req.GivenName,
      CreatedAt: time.Now(),
    },
  }
  
  // Publish to Event Store (FIRST — before external calls)
  if err := h.eventClient.Publish(ctx, event); err != nil {
    return nil, fmt.Errorf("failed to publish event: %w", err)
  }
  
  // Now apply side effects (Cognito, etc.) — best effort
  // If these fail, event is already in the log; consumers will handle it
  if appAccess {
    // Create Cognito account (idempotent consumer will also do this)
  }
  
  return &UserResponse{UserID: userID}, nil
}
```

**Key Principle:** Publish the event to Event Store **FIRST**, before external API calls. This ensures the event log is always the authoritative record. If external calls fail, the event is still logged; consumers will process it.

### Event Propagation

```
{example-service} (stores to DynamoDB)
  ↓
  SNS FIFO topic ({example-service} publishes after storing)
  ↓
  ┌─────────────────────┬──────────────────┬──────────────────┐
  ▼                     ▼                  ▼
SQS FIFO              SQS FIFO           SQS FIFO
({service-name})         ({example-service})     ({service-name})
  ↓                     ↓                  ↓
Lambda consumer    Lambda consumer    Lambda consumer
  ↓                     ↓                  ↓
DynamoDB            Cognito user       SES send email
(projection)        (idempotent)       (idempotent)
```

**Why SNS → SQS → Lambda:**
- **SNS FIFO:** Ordered delivery (all events for one entityId delivered in order)
- **SQS FIFO:** Queue isolation per consumer ({service-name} failures don't block {example-service})
- **Lambda:** Stateless consumer, scales independently, retries on failure
- **DLQ:** Events that fail after max retries go to DLQ for manual inspection

---

## Part 5: Replay & Projection Rebuild

### Full Replay Scenario

When rebuilding projections from scratch:

```bash
# Set replay mode on consumers
export REPLAY_MODE=true

# Consumers skip idempotency checks, reprocess all events
# Consumers skip side effects (Cognito calls, email sends)
```

**Replay Flow:**
1. Clear projection tables ({service-name}, {example-service} partial data)
2. Deploy consumers with `REPLAY_MODE=true`
3. Consumers read Event Store from beginning, apply all events
4. After replay completes, deploy with `REPLAY_MODE=false` to resume normal operation

### Single-Entity Rebuild

To rebuild projection for one user (after data corruption):

```bash
# Query Event Store for one entity
GET /events?entityId=user_123

# Replay only those events through consumer
# Or manually update DynamoDB projection
```

### Guarantees

- **Deterministic:** Replaying the same event stream produces identical state
- **Idempotent:** Replaying an event twice produces same result as replaying once
- **Ordered:** Events for same entity always processed in order (FIFO)
- **Durable:** Event Store is immutable; projections can be discarded and rebuilt

---

## Part 6: Adding a New Projection Service

**Scenario:** You need a new read model (e.g., analytics dashboard, audit log).

### Step 1: Define the Event Set

Determine which domain events your projection needs to consume:

```
Analytics Dashboard needs:
  - UserCreated (8801): track sign-ups per day
  - MembershipCreated (8804): track membership growth
  - PreferenceChanged (8807): track user preferences
```

### Step 2: Create Consumer Service

```go
// New service: {service-name}/lambda/api/main.go
func main() {
  // Event Store client (IAM SigV4 signed)
  eventClient := NewEventStoreClient()
  
  // DynamoDB analytics projection
  analyticsDB := NewAnalyticsDB()
  
  // SQS consumer handler
  handler := NewConsumer(eventClient, analyticsDB)
  
  lambda.Start(handler.Handle)
}

func (h *Consumer) Handle(ctx context.Context, sqsEvent events.SQSEvent) error {
  for _, msg := range sqsEvent.Records {
    event := parseDomainEvent(msg.Body)
    
    // Check idempotency
    if h.idempotency.Exists(ctx, event.ID) {
      continue
    }
    
    // Apply event to analytics projection
    switch event.Kind {
    case 8801: // UserCreated
      h.recordSignup(ctx, event.Content.UserID, event.CreatedAt)
    case 8804: // MembershipCreated
      h.recordMembership(ctx, event.Content.MembershipID, event.Content.OrgID)
    // ... other events
    }
    
    // Mark processed
    h.idempotency.Set(ctx, event.ID)
  }
  return nil
}
```

### Step 3: Deploy Infrastructure

**CDK Stack ({service-name}/cdk/stacks/analytics.ts):**
```typescript
// Event Store SQS consumer
const analyticsQueue = new sqs.Queue(this, 'AnalyticsQueue', {
  fifo: true,
  contentBasedDeduplication: true,
  visibilityTimeout: cdk.Duration.seconds(60),
});

// Dead letter queue for failed events
const analyticsQueueDLQ = new sqs.Queue(this, 'AnalyticsDLQ', { fifo: true });
analyticsQueue.deadLetterQueue = { queue: analyticsQueueDLQ, maxReceiveCount: 3 };

// SNS subscription ({example-service} publishes here)
const eventTopic = sns.Topic.fromTopicArn(...);
eventTopic.addSubscription(new subs.SqsSubscription(analyticsQueue));

// Lambda consumer
const analyticsFunction = new lambda.Function(this, 'AnalyticsConsumer', {...});
analyticsQueue.grantConsumeMessages(analyticsFunction);

// DynamoDB analytics table
const analyticsTable = new dynamodb.Table(this, 'AnalyticsProjection', {
  partitionKey: { name: 'pk', type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
  ttl: { attribute: 'expiresAt', enabled: true },
});
analyticsTable.grantReadWriteData(analyticsFunction);
```

### Step 4: Handle Initial Backfill

On first deployment, your projection is empty. Options:

**Option A: Consume from sns-fifo from deployment forward**
- Fast to deploy
- But you miss historical data
- Later backfill: manually re-run consumer against Event Store

**Option B: Backfill before consuming live**
```bash
# Backfill phase
export BACKFILL_MODE=true
# Consumer queries Event Store, replays all events
# After backfill, deploy with BACKFILL_MODE=false to consume live SNS
```

---

## Part 7: Cross-Service Event Dependencies

### Event Order Guarantees

**Within a single entity (e.g., one user):**
- Events are ordered by creation timestamp
- FIFO SQS ensures delivery in order
- SNS-to-SQS preserves order for same partition key (entityId)

**Across entities (e.g., different users):**
- No ordering guarantee
- Parallel processing is safe (user A's events process independently from user B's)

**Example: User joins membership**
```
UserCreated (8801) → MembershipCreated (8804) → MembershipActivated (8805)
```
All three events share the same entityId (userId), so they're delivered in order.

### Handling Missing Events

If a consumer crashes before idempotency is recorded:

```
Consumer receives UserCreated (8801)
  ↓
Process event
  ↓
*** CRASH BEFORE idempotency.Set() ***
  ↓
SQS re-delivers UserCreated (8801)
  ↓
Consumer reprocesses (idempotent: DynamoDB write is idempotent)
  ↓
idempotency.Set() succeeds
```

**Guarantee:** Final state is correct because:
1. Event Store records event once (immutable)
2. DynamoDB operations are idempotent
3. Idempotency table prevents duplicate processing

---

## Part 8: Anti-Patterns & Common Mistakes

| ❌ Anti-Pattern | ✅ Correct Approach |
|---|---|
| Publishing command instead of domain event | Domain events only (commands are request-response) |
| Storing mutable state in Event Store | Events immutable; corrections via new events |
| Querying Event Store for application reads | Use projections ({service-name}, {example-service}) |
| Consuming events without idempotency | Always check idempotency before processing |
| Skipping side effects during replay | Intentional: REPLAY_MODE=true disables side effects |
| Adding required fields to events | Only add optional fields; required fields break old events |
| Processing events out of order | Use FIFO + entityId as partition key to guarantee order |
| Deleting events from Event Store | Never delete; append correcting events instead |

---

## Part 9: Debugging & Observability

### Tracing an Event Through the System

**Scenario:** User reports signup failed; you need to verify if event was created.

```bash
# 1. Check Event Store for UserCreated event
curl -H "Authorization: Bearer $(aws sts get-session-token)" \
  https://{example-service}.example.com/events?entityId=user_123

# 2. Check projection ({service-name})
curl https://{example-service}.example.com/users/user_123

# 3. Check Cognito ({example-service} projection)
aws cognito-idp admin-get-user --username user_123

# 4. Check consumer logs (CloudWatch)
aws logs tail /aws/lambda/{service-name}
```

### DLQ Inspection

If events fail after max retries (3 re-deliveries):

```bash
# Receive message from {service-name} DLQ
aws sqs receive-message --queue-url https://...{service-name}

# Inspect event
jq .Body message.json | base64 -D | jq .

# Fix and manually process
curl -X POST https://{example-service}.example.com/admin/replay-dlq?queueName={service-name}
```

### Event Integrity Checking

Verify event hash collision detection:

```bash
# Event Store stores integrity hash
metadata.EventIntegrityHash = SHA256(JSON(event.content))

# On resubmission, compute hash and compare
if computedHash != storedHash {
  return 409 Conflict  // Collision detected
}
```

---

## Part 10: Migration & Schema Evolution

### Adding a new event type

1. Allocate event kind (8800-8899 range)
2. Define schema with version "1.0"
3. Update consumers to handle new kind
4. Deploy new consumers BEFORE publishing events

### Renaming a field (breaking change)

```
UserCreated v1.0: { email, givenName, familyName }
UserCreated v1.1: { email, firstName, lastName }  // renamed fields
```

Consumer must handle both:
```go
func (h *Consumer) parseUserCreated(content []byte) (User, error) {
  var base struct{ Version string }
  json.Unmarshal(content, &base)
  
  switch base.Version {
  case "1.0":
    var v1 UserCreatedV1
    json.Unmarshal(content, &v1)
    return User{Email: v1.Email, FirstName: v1.GivenName}, nil
  case "1.1":
    var v11 UserCreatedV11
    json.Unmarshal(content, &v11)
    return User{Email: v11.Email, FirstName: v11.FirstName}, nil
  }
}
```

### Removing a field (non-breaking)

```
UserCreated: { email, phone, unused_legacy_field }
```

Just stop writing the field; old events still contain it but consumers ignore it. No version bump needed.

---

## Part 11: Testing Event-Sourced Services

### Unit Testing Event Consumers

```go
func TestUserCreatedProjection(t *testing.T) {
  // Arrange: Create domain event
  event := DomainEvent{
    Kind: 8801,
    Content: UserCreated{
      UserID: "user_123",
      Email:  "alice@example.com",
    },
  }
  
  // Act: Process event
  consumer := NewConsumer(mockDB, mockIdempotency)
  err := consumer.Handle(ctx, event)
  
  // Assert: Verify user was projected
  user, err := mockDB.GetUser(ctx, "user_123")
  if user.Email != "alice@example.com" {
    t.Fatal("projection failed")
  }
}

func TestIdempotencyPreventsDoubleProcessing(t *testing.T) {
  event := DomainEvent{Kind: 8801, ID: "event_123"}
  
  // First processing
  consumer.Handle(ctx, event)  // User created
  
  // Second processing (idempotency prevents update)
  consumer.Handle(ctx, event)  // Skipped
  
  // Assert: Only one user in DB
  users, _ := mockDB.ListUsers(ctx)
  if len(users) != 1 {
    t.Fatal("idempotency failed")
  }
}
```

### Integration Testing Event Store

```go
func TestEventStorePublishAndRetrieve(t *testing.T) {
  // Publish event
  event := DomainEvent{Kind: 8801, Content: UserCreated{...}}
  err := eventClient.Publish(ctx, event)
  if err != nil {
    t.Fatal(err)
  }
  
  // Query Event Store
  events, err := eventClient.GetByEntityID(ctx, "user_123")
  if len(events) != 1 || events[0].Kind != 8801 {
    t.Fatal("event not stored")
  }
}
```

### E2E Testing ({service-name} → {example-service} → {example-service} → {service-name})

```typescript
// playwright test
test('signup creates user in projection', async ({ page }) => {
  // Signup via {service-name}
  await page.fill('input[name=email]', 'alice@example.com');
  await page.fill('input[name=password]', 'Password123!');
  await page.click('button:has-text("Sign up")');
  
  // Wait for projection (poll {example-service} until user appears)
  const user = await waitForUser('alice@example.com', { timeout: 5000 });
  expect(user.email).toBe('alice@example.com');
});
```

---

## Summary

**Event Sourcing + CQRS = Scalable, auditable, replaying architecture**

1. **Command → Domain Event → Event Store** ({example-service} publishes)
2. **Event Store → SNS FIFO → SQS FIFO → Lambda** (distributed event propagation)
3. **Lambda Consumer → DynamoDB Projection** (idempotent processing)
4. **{example-service} reads Projections** (fast reads)
5. **Full replay possible anytime** (REPLAY_MODE=true)

**Key Guarantees:**
- Events immutable (source of truth)
- Processing idempotent (safe retries)
- Ordered per entity (FIFO)
- Deterministic (replaying produces same state)
- Auditable (full history)

---

## Appendix: Event Kind Reference

| Kind | Event | Domain | Consumers |
|------|-------|--------|-----------|
| 8801 | UserCreated | {example-service} | {service-name}, {example-service}, {service-name} |
| 8802 | UserUpdated | {example-service} | {service-name}, {example-service} |
| 8803 | UserDeleted | {example-service} | {service-name}, {example-service} |
| 8804-8806 | Membership* | {example-service} | {service-name} |
| 8807 | PreferenceChanged | {example-service} | {service-name} |
| 8808 | EmailChanged | {example-service} | {service-name}, {example-service}, {service-name} |
| 8809 | PhoneChanged | {example-service} | {service-name} |
| 8811-8813 | Category* | {example-service} | {service-name} |
| 8814-8816 | Group* | {example-service} | {service-name} |
| 8817-8819 | CalendarEvent* | {example-service} | {service-name} |
| 8820 | ResendInvitation | {example-service} | {service-name} |
| 8821 | ResetPassword | {example-service} | {service-name} |

Commands (20100-20199) are HTTP-only request/response; not stored in Event Store.
