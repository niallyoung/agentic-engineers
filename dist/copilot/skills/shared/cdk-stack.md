# CDK Stack Skill

**Used by:** engineer
**Model:** claude-sonnet-4-6
**Effort:** medium — boilerplate is standardized; adapt stack types and cross-stack props to your service.

Use this skill when creating or modifying AWS CDK infrastructure for Go microservices.

## What This Role Does

- Scaffolds CDK entry point (`cdk/cdk.go`) and stack wrappers
- Implements 3-tier stack architecture (infra → core → application)
- Wires cross-stack references, stack dependencies, and permissions boundaries
- Defines common constructs: HTTP API + Lambda, SQS event consumer, DynamoDB table

## What This Role Does Not Do

- Does not write application Lambda logic (see `lambda-handler.md`)
- Does not design event schemas or CQRS boundaries (escalate to senior-engineer)
- Does not manage Cognito user pools or OAuth2 configuration

## Default Input

- Service name and environment variables (APP_NAME, ENV_NAME, AWS_ACCOUNT, AWS_REGION)
- Stack type(s) needed: HTTP API, event consumer, DynamoDB, or combination

## Default Output

- `cdk/cdk.go` entry point with permissions boundary
- One or more stack files under `cdk/stacks/`

## Entry Point Pattern (standardized)

Every service has `cdk/cdk.go` as the CDK app entry point:

```go
package main

import (
	"os"

	"github.com/aws/aws-cdk-go/awscdk/v2"
	"github.com/aws/aws-cdk-go/awscdk/v2/awsiam"
	"github.com/aws/jsii-runtime-go"

	"github.com/your-org/your-service/cdk/stacks"
)

func main() {
	defer jsii.Close()

	app := awscdk.NewApp(nil)
	appName := os.Getenv("APP_NAME")
	env := &awscdk.Environment{
		Account: jsii.String(os.Getenv("AWS_ACCOUNT")),
		Region:  jsii.String(os.Getenv("AWS_REGION")),
	}

	// NewMyStack returns *stacks.MyStack (a wrapper struct with a Stack awscdk.Stack field
	// for cross-stack references). Access the embedded CDK stack via stack.Stack.
	stack := stacks.NewMyStack(app, appName+"-MyStack", stacks.MyStackProps{
		StackProps: awscdk.StackProps{Env: env},
		AppName:    appName,
		EnvName:    os.Getenv("ENV_NAME"),
	})
	applyBoundary(stack.Stack)

	app.Synth(nil)
}

func applyBoundary(stack awscdk.Stack) {
	awsiam.PermissionsBoundary_Of(stack).Apply(
		awsiam.ManagedPolicy_FromManagedPolicyName(
			stack, jsii.String("CDKBoundary"), jsii.String("CDKPermissionsBoundary"),
		),
	)
}
```

## 3-Tier Stack Architecture

```
Infrastructure (DynamoDB, S3, SNS topics)
  → Core (idempotency tracking, event dispatch)
    → Application (API Gateway, Lambda, consumers)
```

Stacks are wired with `AddDependency()` and cross-stack props:

```go
infraStack := stacks.NewDDBStack(app, appName+"-DDBStack", ...)
apiStack := stacks.NewAPIStack(app, appName+"-APIStack", stacks.APIStackProps{
	TableName: infraStack.TableName,  // cross-stack reference
	TableArn:  infraStack.TableArn,
})
apiStack.AddDependency(infraStack.Stack, jsii.String("DDB"))
```

## Common Stack Types

### HTTP API + Lambda Stack
```go
// API Gateway V2 with JWT authorizer + Lambda
httpApi := awsapigatewayv2.NewHttpApi(stack, jsii.String("API"), ...)
authorizer := awsapigatewayv2authorizers.NewHttpJwtAuthorizer(...)
// Routes: AddRoutes with JWT authorizer
// Custom domain: NewDomainName + NewApiMapping
// SSM export: /{appName}/APIUrl
```

### Event Consumer Stack (SQS FIFO → Lambda)
```go
// SQS FIFO queue subscribes to SNS FIFO topic
// Lambda triggered by SQS with batch size 1
// Idempotency table for exactly-once processing
queue := awssqs.NewQueue(stack, jsii.String("Queue"), &awssqs.QueueProps{
	Fifo: jsii.Bool(true),
	ContentBasedDeduplication: jsii.Bool(true),
})
topic.AddSubscription(awssns_subscriptions.NewSqsSubscription(queue, ...))
```

### DynamoDB Single-Table Stack
```go
// Single table design with PK + SK
table := awsdynamodb.NewTable(stack, jsii.String("Table"), &awsdynamodb.TableProps{
	PartitionKey: &awsdynamodb.Attribute{Name: jsii.String("PK"), Type: awsdynamodb.AttributeType_STRING},
	SortKey:      &awsdynamodb.Attribute{Name: jsii.String("SK"), Type: awsdynamodb.AttributeType_STRING},
	BillingMode:  awsdynamodb.BillingMode_PAY_PER_REQUEST,
	RemovalPolicy: awscdk.RemovalPolicy_RETAIN,
})
```

## Quality Checklist

- [ ] `jsii.String()` / `jsii.Number()` / `jsii.Bool()` used for all CDK types
- [ ] Permissions boundary applied via `applyBoundary()` on every stack
- [ ] Environment variables loaded via `os.Getenv()` — not hardcoded
- [ ] Service discovery exported to SSM: `/{appName}/APIUrl`
- [ ] Other services' SSM params imported: `/{envName}-{service}/Key`
- [ ] One CDK stack per logical component
- [ ] Stack dependencies declared with `AddDependency()`
- [ ] Lambda runtime: `PROVIDED_AL2023`
- [ ] Go CDK v2 (`github.com/aws/aws-cdk-go/awscdk/v2`)

## Escalation Rules

- If a stack requires permissions that exceed the CDKPermissionsBoundary, escalate to lead-engineer or platform team
- If cross-account access is needed, escalate — this requires SCP and trust policy changes outside CDK
