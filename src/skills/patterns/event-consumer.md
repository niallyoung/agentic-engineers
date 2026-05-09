# Event Consumer Skill

**Used by:** senior-engineer
**Model:** claude-sonnet-4-6
**Effort:** high — involves idempotency design, SQS/SNS wiring, CDK infrastructure, and event routing.

Use this skill when building or modifying event-driven consumers that process domain events from an SNS FIFO → SQS FIFO pipeline.

## What This Role Does

- Implements Lambda event consumers with DynamoDB-backed idempotency
- Unwraps SNS envelope from SQS messages and parses domain event payloads
- Routes events by kind to the appropriate handler
- Provisions the SQS FIFO queue, dead-letter queue, and SNS subscription in CDK

## What This Role Does Not Do

- Does not publish domain events — that is the event store's responsibility
- Does not design event schemas or allocate event kind numbers — escalate to lead-engineer
- Does not implement projection queries — that is a separate read-model concern

## Default Input

- Event kinds to handle (numeric constants from your platform's event registry)
- SNS FIFO topic ARN (imported from SSM)
- Consumer name (used as idempotency partition key)

## Default Output

- Lambda handler implementing `HandleSQSEvent`
- DynamoDB idempotency tracking (PROCESSING → COMPLETED/FAILED)
- CDK stack with SQS FIFO + DLQ + SNS subscription + Lambda event source

## Event Flow

```
event-store (DynamoDB + S3) → DDB Stream → dispatcher → SNS FIFO
                                                          ↓
                                                     SQS FIFO queues
                                                          ↓
                                          your-consumer, other-consumers
```

## Domain Event Structure

Events follow the NOSTR event model:

```go
type NostrEvent struct {
	ID        string     `json:"id"`
	PubKey    string     `json:"pubkey"`
	CreatedAt int64      `json:"created_at"`
	Kind      int        `json:"kind"`
	Tags      [][]string `json:"tags"`
	Content   string     `json:"content"`  // JSON-encoded domain payload
	Sig       string     `json:"sig"`
}
```

## Idempotency Pattern

Every event consumer MUST track processed events to guarantee exactly-once semantics:

```go
// DynamoDB idempotency table schema
// PK: eventID (event ID)
// SK: consumerName (e.g., "your-consumer")
// Attributes: status (PROCESSING|COMPLETED|FAILED), ttl, processedAt

func (h *EventConsumer) isAlreadyProcessed(ctx context.Context, eventID string) (bool, error) {
	result, err := h.ddb.GetItem(ctx, &dynamodb.GetItemInput{
		TableName: &h.idempotencyTable,
		Key: map[string]dbtypes.AttributeValue{
			"PK": &dbtypes.AttributeValueMemberS{Value: eventID},
			"SK": &dbtypes.AttributeValueMemberS{Value: h.consumerName},
		},
	})
	if err != nil {
		return false, fmt.Errorf("idempotency check failed: %w", err)
	}
	if result.Item == nil {
		return false, nil
	}
	// Only skip if COMPLETED — retry PROCESSING and FAILED
	var status string
	if err := attributevalue.Unmarshal(result.Item["status"], &status); err != nil {
		return false, fmt.Errorf("failed to unmarshal idempotency status: %w", err)
	}
	return status == StatusCompleted, nil
}

func (h *EventConsumer) setIdempotencyStatus(ctx context.Context, eventID, status string) error {
	ttl := time.Now().Add(30 * 24 * time.Hour).Unix() // 30-day TTL
	_, err := h.ddb.PutItem(ctx, &dynamodb.PutItemInput{
		TableName: &h.idempotencyTable,
		Item: map[string]dbtypes.AttributeValue{
			"PK":          &dbtypes.AttributeValueMemberS{Value: eventID},
			"SK":          &dbtypes.AttributeValueMemberS{Value: h.consumerName},
			"status":      &dbtypes.AttributeValueMemberS{Value: status},
			"processedAt": &dbtypes.AttributeValueMemberS{Value: time.Now().Format(time.RFC3339)},
			"ttl":         &dbtypes.AttributeValueMemberN{Value: fmt.Sprintf("%d", ttl)},
		},
	})
	if err != nil {
		return fmt.Errorf("failed to set idempotency status: %w", err)
	}
	return nil
}
```

## SQS Message Unwrapping

Events arrive in SQS wrapped in an SNS envelope:

```go
// SQS message body contains SNS notification JSON
var snsEnvelope struct {
	Message string `json:"Message"`
}
if err := json.Unmarshal([]byte(sqsRecord.Body), &snsEnvelope); err != nil {
	return fmt.Errorf("failed to unmarshal SNS envelope: %w", err)
}

// SNS Message contains the domain event JSON
var event NostrEvent
if err := json.Unmarshal([]byte(snsEnvelope.Message), &event); err != nil {
	return fmt.Errorf("failed to unmarshal domain event: %w", err)
}

// Event Content contains domain-specific payload
var content YourEventContent
if err := json.Unmarshal([]byte(event.Content), &content); err != nil {
	return fmt.Errorf("failed to unmarshal event content: %w", err)
}
```

## CDK Infrastructure

```go
// SQS FIFO queue with SNS FIFO subscription
queue := awssqs.NewQueue(stack, jsii.String("EventQueue"), &awssqs.QueueProps{
	QueueName: jsii.String(appName + "-events.fifo"),
	Fifo:      jsii.Bool(true),
	ContentBasedDeduplication: jsii.Bool(true),
	VisibilityTimeout: awscdk.Duration_Seconds(jsii.Number(120)),
	DeadLetterQueue: &awssqs.DeadLetterQueue{
		MaxReceiveCount: jsii.Number(3),
		Queue: dlq,
	},
})

// Subscribe to SNS FIFO topic (imported via SSM)
topicArn := awsssm.StringParameter_ValueForStringParameter(stack, jsii.String("TopicArn"),
	jsii.String("/"+envName+"-your-event-store/SNSTopicArn"),
)
topic := awssns.Topic_FromTopicArn(stack, jsii.String("EventTopic"), topicArn)
topic.AddSubscription(awssns_subscriptions.NewSqsSubscription(queue, ...))

// Lambda event source mapping
lambda.AddEventSource(awslambdaeventsources.NewSqsEventSource(queue, &awslambdaeventsources.SqsEventSourceProps{
	BatchSize: jsii.Number(1),  // Process one event at a time for ordering
}))
```

## Quality Checklist

- [ ] FIFO queues used for ordering guarantees
- [ ] Batch size 1 for strict ordering within a message group
- [ ] Dead-letter queue after 3 failed attempts
- [ ] 30-day TTL on idempotency records
- [ ] SNS envelope unwrapped before parsing domain event
- [ ] Event ID, kind, and correlation ID logged for every event
- [ ] Errors returned from handler (not swallowed) to trigger SQS retry
- [ ] Replay mode (`REPLAY_MODE=true`) skips idempotency checks if required

## Escalation Rules

- If a new event kind is needed, escalate to lead-engineer to allocate a kind number in the platform registry
- If a consumer needs to be replayable (projection rebuild), escalate to senior-engineer to design replay mode safely (especially for side-effecting handlers like email or external API calls)
- If the DLQ fills up, escalate immediately — messages in DLQ represent data loss risk
