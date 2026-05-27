# SigV4 Client Skill

**Used by:** engineer
**Model:** claude-sonnet-4.6
**Effort:** low — copy implementation, inject at construction time, call from handlers.

Use this skill when implementing inter-service HTTP communication where the target API Gateway uses IAM authorization (not JWT).

## What This Role Does

- Implements an IAM SigV4-signed HTTP client for calling IAM-auth-protected API Gateways
- Forwards user context headers (`X-User-Id`, `X-User-Email`, `X-Correlation-Id`) for downstream auditing
- Grants the calling Lambda `execute-api:Invoke` permission on the target API in CDK

## What This Role Does Not Do

- Does not handle JWT authentication — that is the API Gateway's concern on the inbound side
- Does not implement retry logic — add a wrapper if needed for your service's resilience requirements
- Does not call services that use API key or basic auth — use the correct client for those

## Default Input

- AWS config (`aws.Config`) from `config.LoadDefaultConfig()`
- Target URL, HTTP method, request body
- User context: user ID, email, correlation ID

## Default Output

- Response body bytes, or error
- Signed HTTP request with `Authorization` header and `X-Amz-*` headers set by AWS SDK

## Auth Architecture

```
Frontend (JWT) → Gateway Lambda (validates JWT, signs with IAM)
                      ↓ SigV4 signed
               Backend API Gateway (IAM auth only)
                      ↓
               Backend Lambda (trusts IAM, reads X-User-* headers)
```

## Implementation

```go
package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	v4 "github.com/aws/aws-sdk-go-v2/aws/signer/v4"
)

type IAMSigningClient struct {
	cfg        aws.Config
	httpClient *http.Client
	signer     *v4.Signer
}

func NewIAMSigningClient(cfg aws.Config) *IAMSigningClient {
	return &IAMSigningClient{
		cfg:        cfg,
		httpClient: &http.Client{Timeout: 30 * time.Second},
		signer:     v4.NewSigner(),
	}
}

func (c *IAMSigningClient) SignedRequest(ctx context.Context, method, urlStr string, body []byte, userID, userEmail, correlationID string) ([]byte, error) {
	parsedURL, err := url.Parse(urlStr)
	if err != nil {
		return nil, fmt.Errorf("invalid URL: %w", err)
	}

	var reqBody io.Reader
	if body != nil {
		reqBody = bytes.NewReader(body)
	}

	req, err := http.NewRequestWithContext(ctx, method, urlStr, reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Host = parsedURL.Host
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	// Forward user context for downstream auditing
	if userID != "" {
		req.Header.Set("X-User-Id", userID)
	}
	if userEmail != "" {
		req.Header.Set("X-User-Email", userEmail)
	}
	if correlationID != "" {
		req.Header.Set("X-Correlation-Id", correlationID)
	}

	// SHA-256 hash of payload (required for SigV4)
	payload := body
	if payload == nil {
		payload = []byte{}
	}
	hash := sha256.Sum256(payload)
	payloadHash := hex.EncodeToString(hash[:])

	creds, err := c.cfg.Credentials.Retrieve(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to retrieve credentials: %w", err)
	}

	// Sign with service name "execute-api" for API Gateway
	err = c.signer.SignHTTP(ctx, creds, req, payloadHash, "execute-api", c.cfg.Region, time.Now())
	if err != nil {
		return nil, fmt.Errorf("failed to sign request: %w", err)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("API error %d: %s", resp.StatusCode, string(respBody))
	}

	return respBody, nil
}
```

## CDK Permissions

The calling Lambda needs `execute-api:Invoke` on the target API Gateway:

```go
// Preferred: use CDK grant method if available
targetApi.GrantInvoke(callerLambda)

// Explicit policy when grant method is unavailable:
callerLambda.AddToRolePolicy(awsiam.NewPolicyStatement(&awsiam.PolicyStatementProps{
	Actions:   jsii.Strings("execute-api:Invoke"),
	Resources: jsii.Strings(targetApiArn + "/*"),
}))
```

## User Context Headers

The calling service extracts from the inbound JWT claims and forwards as headers:

| Header | Source | Purpose |
|--------|--------|---------|
| `X-User-Id` | JWT `sub` claim | User identity for audit |
| `X-User-Email` | JWT `email` claim | Human-readable identity |
| `X-Correlation-Id` | Generated or propagated | Request tracing |

Backend services read these headers directly — they do not re-parse any JWT.

## Quality Checklist

- [ ] Service name is always `"execute-api"` for API Gateway SigV4 signing
- [ ] `IAMSigningClient` created once in `main()`, reused across invocations
- [ ] User context headers forwarded on every request (not just some)
- [ ] 30-second HTTP timeout set
- [ ] Backend API Gateway configured for IAM auth — not JWT, not open
- [ ] CDK permissions granted via `GrantInvoke` or explicit policy

## Escalation Rules

- If a backend service accepts JWT directly (bypassing IAM), escalate to lead-engineer — this violates the auth architecture
- If the 30-second timeout is too short for a specific call (e.g., long-running compute), document the exception and escalate to senior-engineer to review the interaction pattern
