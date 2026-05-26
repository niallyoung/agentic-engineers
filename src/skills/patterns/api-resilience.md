# API Resilience Skill

**Used by:** senior-engineer
**Model:** claude-sonnet-4.6
**Effort:** medium — implement once per frontend API client; adjust retry parameters to match your SLA.

Use this skill when building or modifying API client code in frontend applications that call backend HTTP services.

## What This Role Does

- Implements resilient API client wrappers with exponential backoff, token refresh, and maintenance-mode handling
- Wires the client into frontend state management (optimistic updates, delayed refetch)
- Ensures all API calls go through the resilience layer — no raw `fetch` calls in application code

## What This Role Does Not Do

- Does not design the backend API contract (that is the engineer's concern)
- Does not implement auth flows — expects a `getToken` / `refreshToken` callback pair from the auth module
- Does not configure CDK or Lambda infrastructure

## Default Input

- Base URL of the API gateway
- Token getter: `() => string`
- Token refresher: `() => Promise<void>` (optional)

## Default Output

- An `ApiService` class with `get`, `post`, `put`, `delete` methods
- An optimistic-update hook pattern for CQRS/ES eventual consistency

## Pattern

All frontend API calls use a resilience wrapper with:
1. **Exponential backoff** — 5 attempts with 1s, 2s, 4s, 8s delays
2. **Token refresh** — Automatic 401 retry with token refresh (once)
3. **Maintenance mode** — 503 handling with Retry-After and custom UX

## Implementation

```typescript
export class MaintenanceError extends Error {
  public retryAfter: number | null;
  constructor(message: string, retryAfter: number | null = null) {
    super(message);
    this.name = 'MaintenanceError';
    this.retryAfter = retryAfter;
  }
}

export class ApiService {
  public baseUrl: string;
  private getToken: () => string;
  private refreshToken: (() => Promise<void>) | null;
  private isRefreshing = false;
  private refreshPromise: Promise<void> | null = null;

  constructor(baseUrl: string, getToken: () => string, refreshToken?: () => Promise<void>) {
    this.baseUrl = baseUrl;
    this.getToken = getToken;
    this.refreshToken = refreshToken || null;
  }

  private async attempt<T>(endpoint: string, options: RequestInit = {}, isTokenRetry = false): Promise<T> {
    const token = this.getToken();
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      // 401: refresh token and retry once
      if (response.status === 401 && !isTokenRetry && this.refreshToken) {
        if (!this.isRefreshing) {
          this.isRefreshing = true;
          this.refreshPromise = this.refreshToken().finally(() => {
            this.isRefreshing = false;
            this.refreshPromise = null;
          });
        }
        await this.refreshPromise;
        return this.attempt<T>(endpoint, options, true);
      }

      // 503: maintenance mode with structured error
      if (response.status === 503) {
        const retryAfter = parseInt(response.headers.get('Retry-After') || '', 10) || null;
        let message = 'Service temporarily unavailable';
        try { message = ((await response.json()) as {message?: string}).message || message; } catch {}
        throw new MaintenanceError(message, retryAfter);
      }

      // Other errors: try to parse body for message
      let errorMessage: string | undefined;
      try { const body = await response.json() as {error?: string; message?: string}; errorMessage = body.error || body.message; } catch {}
      throw new Error(errorMessage || `HTTP ${response.status}: ${response.statusText}`);
    }

    // No-content or non-JSON response — return undefined
    if (response.status === 204 || !response.headers.get('Content-Type')?.includes('application/json')) {
      return undefined as unknown as T;
    }
    return await response.json() as T;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const MAX_ATTEMPTS = 5;
    let lastError: Error | null = null;

    for (let i = 1; i <= MAX_ATTEMPTS; i++) {
      try {
        return await this.attempt<T>(endpoint, options);
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        if (error instanceof MaintenanceError) throw error;  // don't retry maintenance
        lastError = error;
        if (i < MAX_ATTEMPTS) {
          const delay = Math.pow(2, i - 1) * 1000;
          await new Promise(r => setTimeout(r, delay));
        }
      }
    }
    throw new Error(lastError?.message || 'Request failed');
  }

  async get<T = unknown>(endpoint: string): Promise<T> { return this.request<T>(endpoint, { method: 'GET' }); }
  async post<T = unknown>(endpoint: string, data: unknown): Promise<T> { return this.request<T>(endpoint, { method: 'POST', body: JSON.stringify(data) }); }
  async put<T = unknown>(endpoint: string, data: unknown): Promise<T> { return this.request<T>(endpoint, { method: 'PUT', body: JSON.stringify(data) }); }
  async delete<T = unknown>(endpoint: string): Promise<T> { return this.request<T>(endpoint, { method: 'DELETE' }); }
}
```

## Optimistic Update Hook Pattern

For CQRS/ES eventual consistency, combine API calls with optimistic UI updates:

```typescript
const updateItem = async (id: string, request: UpdateItemRequest) => {
  setError(null);
  await commandApi.post(`/commands/UpdateItem`, { itemId: id, ...request });

  // Optimistic update — only include defined fields
  const updates: Partial<Item> = { updatedAt: new Date().toISOString() };
  if (request.name !== undefined) updates.name = request.name;
  // ...only spread defined fields to avoid clobbering with undefined

  setItems(prev => optimisticUpdate(prev, 'item_id', id, updates));
  scheduleRefetch(fetchItems);  // delayed refetch for eventual consistency
};
```

## Quality Checklist

- [ ] All API calls go through `ApiService` — no raw `fetch` in application code
- [ ] `MaintenanceError` is never retried — it has its own UX flow
- [ ] Token refresh uses a singleton promise (no concurrent refreshes)
- [ ] Optimistic updates only spread defined fields (never overwrite with `undefined`)
- [ ] `scheduleRefetch` delays 2-3 seconds for CQRS event propagation
- [ ] One `ApiService` instance per API gateway endpoint

## Escalation Rules

- If the backend changes auth scheme (e.g., from Bearer to cookie), escalate to lead-engineer to review the auth module boundary
- If retry budget is insufficient for your SLA, escalate retry parameters with data (e.g., p99 latency from monitoring)
