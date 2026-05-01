# Lambda Handler Skill

**Used by:** engineer
**Model:** claude-sonnet-4-6
**Effort:** medium — two archetypes cover most cases; adapt routing and dependency injection to your service.

Use this skill when creating or modifying Lambda functions for Go microservices on AWS.

## What This Role Does

- Scaffolds Lambda `main()` with dependency injection and AWS SDK client setup
- Implements HTTP API handlers (routing, JWT claim extraction, structured error responses)
- Implements SQS event consumer handlers (message unwrapping, idempotency, event routing)
- Ensures AWS clients are created once in `main()` and reused across invocations

## What This Role Does Not Do

- Does not provision CDK infrastructure (see `cdk-stack.md`)
- Does not design event schemas or allocate event kind numbers
- Does not write business logic — delegates to domain functions/services

## Default Input

- Handler archetype: HTTP API or Event Consumer
- Routes or event kinds to handle
- AWS services needed (DynamoDB, SQS, SSM, etc.)

## Default Output

- `lambda/<name>/main.go` with handler struct, `main()`, and route/event dispatch

## Two Archetypes

### Type A: HTTP API Handler

Single Lambda behind API Gateway with JWT authorizer. Receives HTTP requests, routes to handlers.

```go
package main

import (
	"context"
	"os"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/config"
)

func main() {
	cfg, err := config.LoadDefaultConfig(context.Background())
	if err != nil {
		panic("unable to load SDK config: " + err.Error())
	}

	// Dependency injection — create clients once, reuse across invocations
	iamClient := NewIAMSigningClient(cfg)
	appName := os.Getenv("APP_NAME")

	handler := &Handler{
		iamClient: iamClient,
		appName:   appName,
	}

	lambda.Start(handler.Route)
}

// Route dispatches based on HTTP method + path
func (h *Handler) Route(ctx context.Context, req events.APIGatewayV2HTTPRequest) (events.APIGatewayV2HTTPResponse, error) {
	// Extract user context from JWT claims (set by API Gateway authorizer)
	userID := req.RequestContext.Authorizer.JWT.Claims["sub"]
	userEmail := req.RequestContext.Authorizer.JWT.Claims["email"]

	switch req.RouteKey {
	case "POST /commands/CreateItem":
		return h.handleCreateItem(ctx, req, userID, userEmail)
	case "GET /queries/ListItems":
		return h.handleListItems(ctx, req, userID)
	default:
		return respond(404, `{"error":"not found"}`)
	}
}

func respond(status int, body string) (events.APIGatewayV2HTTPResponse, error) {
	return events.APIGatewayV2HTTPResponse{
		StatusCode: status,
		Headers:    map[string]string{"Content-Type": "application/json"},
		Body:       body,
	}, nil
}
```

### Type B: Event Consumer

Lambda triggered by SQS FIFO queue. Processes domain events with idempotency tracking.

```go
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
)

const (
	StatusProcessing = "PROCESSING"
	StatusCompleted  = "COMPLETED"
	StatusFailed     = "FAILED"
)

func main() {
	cfg, err := config.LoadDefaultConfig(context.Background())
	if err != nil {
		panic("unable to load SDK config: " + err.Error())
	}
	ddbClient := dynamodb.NewFromConfig(cfg)

	handler := &EventConsumer{
		ddb:              ddbClient,
		tableName:        os.Getenv("TABLE_NAME"),
		idempotencyTable: os.Getenv("IDEMPOTENCY_TABLE"),
	}

	lambda.Start(handler.HandleSQSEvent)
}

func (h *EventConsumer) HandleSQSEvent(ctx context.Context, sqsEvent events.SQSEvent) error {
	for _, record := range sqsEvent.Records {
		// Unwrap SNS envelope from SQS message
		var snsEnvelope struct {
			Message string `json:"Message"`
		}
		if err := json.Unmarshal([]byte(record.Body), &snsEnvelope); err != nil {
			return fmt.Errorf("failed to unmarshal SNS envelope: %w", err)
		}

		// Parse domain event
		var event DomainEvent
		if err := json.Unmarshal([]byte(snsEnvelope.Message), &event); err != nil {
			return fmt.Errorf("failed to unmarshal domain event: %w", err)
		}

		// Idempotency check — skip if already processed
		alreadyProcessed, err := h.isAlreadyProcessed(ctx, event.ID)
		if err != nil {
			return fmt.Errorf("failed to check idempotency for event %s: %w", event.ID, err)
		}
		if alreadyProcessed {
			log.Printf("Skipping duplicate event %s (kind %d)", event.ID, event.Kind)
			continue
		}

		// Mark as processing
		if err := h.setIdempotencyStatus(ctx, event.ID, StatusProcessing); err != nil {
			return fmt.Errorf("failed to mark event %s as processing: %w", event.ID, err)
		}

		// Route by event kind
		var procErr error
		switch event.Kind {
		case KindItemCreated:
			procErr = h.handleItemCreated(ctx, event)
		case KindItemUpdated:
			procErr = h.handleItemUpdated(ctx, event)
		default:
			log.Printf("Unknown event kind %d, skipping", event.Kind)
		}

		// Update idempotency status
		if procErr != nil {
			_ = h.setIdempotencyStatus(ctx, event.ID, StatusFailed)
			return fmt.Errorf("failed to process event %s: %w", event.ID, procErr)
		}
		if err := h.setIdempotencyStatus(ctx, event.ID, StatusCompleted); err != nil {
			return fmt.Errorf("failed to mark event %s as completed: %w", event.ID, err)
		}
	}
	return nil
}
```

## Quality Checklist

- [ ] AWS clients created in `main()`, passed to handler struct — never created per-invocation
- [ ] Dependency injection via interfaces (not concrete types) for testability
- [ ] `context.Context` propagated through all calls
- [ ] Event consumers implement idempotency (see `event-consumer.md`)
- [ ] HTTP handlers extract user context from JWT claims (not re-validated in Lambda)
- [ ] Structured JSON errors with appropriate HTTP status codes
- [ ] Structured logging: event ID, kind, correlation ID
- [ ] No `panic()` in production code paths

## Escalation Rules

- If the handler needs to call another internal service with IAM auth, use the SigV4 client (see `sigv4-client.md`)
- If idempotency logic is complex (replay mode, conditional skips), escalate to senior-engineer
- If CDK infrastructure changes are needed alongside handler changes, coordinate with the CDK stack (see `cdk-stack.md`)
