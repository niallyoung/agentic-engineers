---
name: test-integration-orchestration
description: Run integration tests with ERS service mocking (DynamoDB, SNS, Lambda)
type: skill
version: 1.0
track: testing
---

# test-integration-orchestration

Execute integration tests for ERS services using AWS service mocks (LocalStack, testcontainers,
or go mock libraries). Tests real service interactions without hitting live AWS.

## Usage

```
/test-integration-orchestration service_path=/home/user/git/ers/{service-name}
/test-integration-orchestration service_path={example-service} mock_sns=true mock_dynamodb=true
/test-integration-orchestration service_path={example-service} environment=staging
```

## Input

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `service_path` | str | required | Path to service root |
| `environment` | str | `test` | Target environment context |
| `test_filter` | str | null | Filter by test name pattern |
| `mock_dynamodb` | bool | true | Mock DynamoDB with local instance |
| `mock_sns` | bool | true | Mock SNS/SQS for event fanout |
| `mock_eventbridge` | bool | true | Mock EventBridge rules |
| `timeout_sec` | int | 120 | Max test execution time |

## Output

```json
{
  "service": "{service-name}",
  "environment": "test",
  "integration_tests": 15,
  "passed": 13,
  "failed": 2,
  "skipped": 0,
  "failed_tests": [
    {
      "name": "TestEventConsumer_UserCreated_MissingPhone",
      "file": "consumers/user_created_test.go:112",
      "error": "DynamoDB put failed: ConditionalCheckFailedException"
    }
  ],
  "mocks_used": ["DynamoDB", "SNS", "SQS"],
  "mock_setup_time_sec": 8.2,
  "execution_time_sec": 42.5,
  "coverage_additional_percent": 12.3,
  "gate_result": "WARN"
}
```

## Implementation

### Step 1: Detect Integration Tests

```pseudo
func find_integration_tests(service_path):
  # Go: look for build tags or file name conventions
  integration_files = find(service_path, "*_integration_test.go")
  
  # Also find tests tagged with //go:build integration
  tagged_files = grep(service_path, "//go:build integration", "*.go")
  
  # {service-name} pattern: consumer tests are integration tests
  consumer_tests = find(service_path + "/consumers", "*_test.go")
  
  return dedupe(integration_files + tagged_files + consumer_tests)
```

### Step 2: Set Up Mock Infrastructure

#### DynamoDB Mock (Go — aws-sdk-go-v2)

ERS services use `aws-sdk-go-v2`. Mock via `smithy-go/testing` or real LocalStack:

```pseudo
func setup_dynamodb_mock(service_path):
  # Option A: LocalStack (preferred for full fidelity)
  if localstack_available():
    start_localstack_container()
    endpoint = "http://localhost:4566"
    create_test_tables(endpoint, service_path + "/cdk/tables.json")
    return MockConfig{ endpoint: endpoint, type: "localstack" }
  
  # Option B: In-memory mock (go-mock-dynamodb or custom)
  else:
    return MockConfig{ type: "in-memory", mock: NewDynamoDBMock() }
```

ERS DynamoDB tables to create for tests:
- `{service-name}{ENV}` — members projection table
- `{example-service}-{ENV}` — event store table  
- `{service-name}{ENV}` — idempotency tracking

#### SNS/SQS Mock

```pseudo
func setup_sns_mock():
  if localstack_available():
    create_sns_topic("{service-name}{ENV}.fifo")
    create_sqs_queue("{service-name}{ENV}.fifo")
    subscribe_queue_to_topic()
    return SQSEndpoint("http://localhost:4566")
  
  else:
    # Use go channel-based mock
    return InMemorySNSMock()
```

### Step 3: Seed Test Fixtures

```pseudo
func seed_test_fixtures(service_path, dynamodb_endpoint):
  fixture_file = service_path + "/testdata/fixtures.json"
  if exists(fixture_file):
    load fixtures and PUT each item to DynamoDB
  
  # {service-name} standard fixtures:
  # - 2 active members, 1 admin, 1 disabled
  # - 2 membership records
  # - 3 category records
  seed_standard_ers_fixtures(dynamodb_endpoint)
```

### Step 4: Execute Integration Tests

**Go with build tags:**
```bash
cd {service_path}
DYNAMODB_ENDPOINT=http://localhost:4566 \
SNS_ENDPOINT=http://localhost:4566 \
ENV_NAME=test \
go test ./... -tags integration -v -timeout 120s 2>&1
```

**Go consumer tests (no build tag):**
```bash
cd {service_path}/consumers
DYNAMODB_ENDPOINT=http://localhost:4566 \
go test ./... -v -timeout 120s 2>&1
```

**ERS pattern — if Makefile has integration target:**
```bash
make test-integration ENV_NAME=test
```

### Step 5: Event Consumer Test Pattern

ERS event consumers ({service-name}, {example-service}, {service-name}) follow this integration test structure:

```pseudo
for each consumer (UserCreated, UserUpdated, MembershipCreated, etc.):
  1. Publish test event to mock SNS topic
  2. Trigger Lambda handler with mock SQS event body
  3. Verify DynamoDB state change (item created/updated/deleted)
  4. Check idempotency: re-publish same event, verify no duplicate
  5. Check REPLAY_MODE: skip idempotency check, reprocess cleanly
```

Test scenario: `TestEventConsumer_UserCreated`
```go
// Pseudo-code for what the integration test verifies:
event := nostr.Event{Kind: 8801, Content: `{"id":"user-1","email":"test@example.com"}`}
handler.HandleUserCreated(event)
// Assert: DynamoDB contains user record
// Assert: idempotency record created
// Re-run: same event → no error, no duplicate
```

### Step 6: Parse Results

```pseudo
func parse_go_integration_results(output):
  passed = count("--- PASS:" in output)
  failed = count("--- FAIL:" in output)
  skipped = count("--- SKIP:" in output)
  
  failures = extract_failures(output)  # same as unit test parsing
  
  execution_time = extract_total_time(output)
  
  return IntegrationResult{passed, failed, skipped, failures, execution_time}
```

### Step 7: Teardown

```pseudo
func teardown(mock_config):
  if mock_config.type == "localstack":
    stop_localstack_container()
  clear_test_fixtures()
  reset_environment_vars()
```

### Step 8: Gate Decision

```pseudo
gate_result = "PASS"

if mock_setup_failed:
  gate_result = "BLOCK"  # can't run integration tests at all
  return

if failed > 0:
  gate_result = "WARN"  # integration failures = warn (flaky infra possible)
  if failed / total > 0.2:  # >20% failure rate
    gate_result = "BLOCK"
```

## ERS-Specific Integration Points

### {service-name} Consumer Tests

```bash
# Test all event consumers:
cd /home/user/git/ers/{service-name}
DYNAMODB_ENDPOINT=http://localhost:4566 go test ./consumers/... -v
```

Consumers to test: UserCreated, UserUpdated, UserDeleted, MembershipCreated,
MembershipUpdated, MembershipCancelled, PreferenceChanged, CategoryCreated,
GroupCreated, CalendarEventCreated (events 8801–8819)

### {example-service} Store Tests

```bash
cd /home/user/git/ers/{example-service}
# Tests: StoreEvent, GetEvents, ReplayEvents, PaginatedQuery
go test ./... -v -timeout 60s
```

### {example-service} Handler Tests

```bash
cd /home/user/git/ers/{example-service}
# Tests: route commands → publish events, validate JWT scopes
go test ./... -v
```

Key integration: {example-service} calls {example-service} (SigV4), then {example-service}/{service-name}.
Mock both downstream services in integration tests.

## LocalStack Quick Start

```bash
# Start LocalStack for ERS testing
docker run -d \
  -p 4566:4566 \
  -e SERVICES=dynamodb,sns,sqs,ssm \
  --name {service-name} \
  localstack/localstack:latest

# Wait for ready
until curl -s http://localhost:4566/_localstack/health | grep -q '"dynamodb": "available"'; do
  sleep 1
done
```

## Integration

- Runs after `test-unit-orchestration` (slower, ~30-120s per service)
- Failed consumers feed directly to `issue-diagnostic-engine`
- Mock configs reused by `test-business-logic` for state machine testing
- `quality-gate-orchestration` runs this in parallel with security scans

## Success Criteria

- Set up DynamoDB + SNS mocks without hitting AWS
- Run all event consumer tests for {service-name} (>10 tests)
- Verify idempotency behavior
- Report failures with precise error messages
