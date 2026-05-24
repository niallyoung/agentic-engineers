# Future Memory API Design

**Status**: Design Specification (Not Implemented)  
**Version**: 1.0  
**Purpose**: Database API layer for scalable memory querying and cross-session analysis  
**Timeline**: Phase 3-4 future work (after file-based storage stabilizes)

---

## 1. Executive Summary

This document designs a future REST/GraphQL API layer for memory access. Currently, memory is file-based in `~/.agentic-engineers/{session_id}/memory/`. When scale demands, we will migrate to a database backend (PostgreSQL or SQLite) while maintaining the file API.

**Key Goals:**
- Queryable: Search across tasks, agents, phases, time ranges
- Scalable: Support 1000s of sessions, millions of events
- Composable: Combine queries (AND, OR, NOT operators)
- Consistent: Same schema as file-based storage
- Backward-compatible: File API still works during transition

---

## 2. Database Schema (PostgreSQL)

### 2.1 Core Tables

#### `sessions` Table

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(36) UNIQUE NOT NULL,
    harness VARCHAR(20) NOT NULL,  -- local, github, cloud
    user_id VARCHAR(100) NOT NULL,
    repository VARCHAR(200) NOT NULL,
    branch VARCHAR(200) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    phase VARCHAR(50),
    metadata JSONB NOT NULL DEFAULT '{}',
    config JSONB NOT NULL DEFAULT '{}',
    
    CONSTRAINT user_repo_time_unique UNIQUE (user_id, repository, created_at),
    INDEX sessions_user_id (user_id),
    INDEX sessions_repository (repository),
    INDEX sessions_created_at (created_at DESC)
);
```

#### `delegates` Table

```sql
CREATE TABLE delegates (
    id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(100) UNIQUE NOT NULL,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- engineer, senior_engineer, etc
    model VARCHAR(100) NOT NULL,
    effort VARCHAR(20) NOT NULL,  -- low, medium, high, max, epic
    estimated_hours INT NOT NULL,
    scope TEXT NOT NULL,
    context TEXT NOT NULL,
    success_criteria TEXT[] NOT NULL,  -- Array of criteria
    plan JSONB NOT NULL,  -- Array of plan steps
    status VARCHAR(20) DEFAULT 'pending',  -- pending, assigned, completed, failed
    payload JSONB NOT NULL,  -- Full DELEGATE YAML as JSON
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    delegated_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT effort_valid CHECK (effort IN ('low', 'medium', 'high', 'max', 'epic')),
    CONSTRAINT role_valid CHECK (role IN ('engineer', 'senior_engineer', 'lead_engineer', 'principal_engineer', 'security_engineer', 'quality_engineer', 'model_engineer')),
    
    INDEX delegates_session (session_id),
    INDEX delegates_role (role),
    INDEX delegates_effort (effort),
    INDEX delegates_status (status),
    INDEX delegates_created_at (created_at DESC),
    INDEX delegates_task_id (task_id)
);
```

#### `handbacks` Table

```sql
CREATE TABLE handbacks (
    id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(100) UNIQUE NOT NULL REFERENCES delegates(task_id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL,  -- complete, failed, partial, blocked
    deliverables TEXT[] NOT NULL,
    quality_score INT NOT NULL CHECK (quality_score >= 0 AND quality_score <= 100),
    tokens_in INT NOT NULL,
    tokens_out INT NOT NULL,
    effort_actual DECIMAL(5, 2),
    duration_minutes INT NOT NULL,
    test_passed INT,
    test_failed INT,
    test_coverage DECIMAL(5, 2),
    notes TEXT NOT NULL,
    payload JSONB NOT NULL,  -- Full HANDBACK YAML as JSON
    received_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT status_valid CHECK (status IN ('complete', 'failed', 'partial', 'blocked')),
    
    INDEX handbacks_session (session_id),
    INDEX handbacks_status (status),
    INDEX handbacks_quality_score (quality_score DESC),
    INDEX handbacks_received_at (received_at DESC),
    INDEX handbacks_task_id (task_id)
);
```

#### `execution_logs` Table

```sql
CREATE TABLE execution_logs (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    task_id VARCHAR(100) REFERENCES delegates(task_id) ON DELETE SET NULL,
    agent_type VARCHAR(50) NOT NULL,
    phase VARCHAR(50) NOT NULL,
    level VARCHAR(10) NOT NULL,  -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    message TEXT NOT NULL,
    context JSONB,
    metrics JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT level_valid CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    
    INDEX exec_logs_session (session_id, created_at DESC),
    INDEX exec_logs_task (task_id),
    INDEX exec_logs_agent_phase (agent_type, phase, created_at DESC),
    INDEX exec_logs_level (level),
    INDEX exec_logs_created_at (created_at DESC)
);
```

#### `thinking_outputs` Table

```sql
CREATE TABLE thinking_outputs (
    id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL REFERENCES delegates(task_id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    model VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    content_length INT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(task_id),
    INDEX thinking_session (session_id),
    INDEX thinking_task (task_id),
    INDEX thinking_created_at (created_at DESC)
);
```

#### `feedback` Table

```sql
CREATE TABLE feedback (
    id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL REFERENCES delegates(task_id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    reviewer VARCHAR(100) NOT NULL,
    reviewed BOOLEAN NOT NULL DEFAULT FALSE,
    reviewer_notes TEXT,
    improvements TEXT[],
    approve BOOLEAN,
    quality_score_feedback INT CHECK (quality_score_feedback >= 0 AND quality_score_feedback <= 100),
    payload JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    INDEX feedback_session (session_id),
    INDEX feedback_task (task_id),
    INDEX feedback_reviewer (reviewer),
    INDEX feedback_approve (approve),
    INDEX feedback_created_at (created_at DESC)
);
```

#### `metrics` Table (Aggregated)

```sql
CREATE TABLE metrics (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    metric_type VARCHAR(50) NOT NULL,  -- token_usage, quality, execution, cost
    role VARCHAR(50),
    model VARCHAR(100),
    date DATE NOT NULL,
    value_int INT,
    value_float DECIMAL(10, 2),
    value_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT metric_type_valid CHECK (metric_type IN ('token_usage', 'quality', 'execution', 'cost')),
    
    UNIQUE(session_id, metric_type, role, model, date),
    INDEX metrics_session_date (session_id, date DESC),
    INDEX metrics_type_date (metric_type, date DESC)
);
```

#### `timeline_events` Table

```sql
CREATE TABLE timeline_events (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    task_id VARCHAR(100) REFERENCES delegates(task_id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL,  -- delegate_created, handback_received, etc
    agent VARCHAR(100),
    details TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT event_type_valid CHECK (
        event_type IN ('session_created', 'delegate_created', 'handback_received', 
                      'task_complete', 'phase_transition', 'error_occurred', 'retry_triggered')
    ),
    
    INDEX timeline_session (session_id, created_at DESC),
    INDEX timeline_task (task_id, created_at DESC),
    INDEX timeline_event_type (event_type),
    INDEX timeline_created_at (created_at DESC)
);
```

#### `audit_log` Table (Append-only)

```sql
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    operation VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),  -- session, delegate, handback, etc
    entity_id VARCHAR(200),
    details TEXT,
    checksum VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    INDEX audit_session (session_id, created_at DESC),
    INDEX audit_operation (operation),
    INDEX audit_created_at (created_at DESC)
);
```

---

## 3. REST API Endpoints

### 3.1 Sessions

#### List Sessions
```
GET /api/v1/sessions
Query Parameters:
  - user_id: Filter by user
  - repository: Filter by repository
  - since: Start timestamp (ISO8601)
  - until: End timestamp (ISO8601)
  - limit: Max results (default 50)
  - offset: Pagination offset

Response:
{
  "sessions": [
    {
      "session_id": "771628bc-263c-4c9e-98c9-5f24a6418b95",
      "user": "niallyoung",
      "repository": "agentic-engineers",
      "branch": "main",
      "created_at": "2026-05-24T10:00:00Z",
      "completed_at": null,
      "phase": "design",
      "task_count": 5,
      "quality_avg": 88.5
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

#### Get Session Details
```
GET /api/v1/sessions/{session_id}

Response:
{
  "session_id": "771628bc-263c-4c9e-98c9-5f24a6418b95",
  "harness": "local",
  "user": "niallyoung",
  "repository": "agentic-engineers",
  "branch": "main",
  "created_at": "2026-05-24T10:00:00Z",
  "timeline": [
    {"timestamp": "2026-05-24T10:00:00Z", "event": "session_created"},
    {"timestamp": "2026-05-24T10:15:00Z", "event": "delegate_created", "task_id": "2026-05-24-task1"}
  ],
  "metrics": {
    "total_tasks": 5,
    "completed_tasks": 3,
    "failed_tasks": 0,
    "average_quality": 88.5,
    "total_tokens": 245000,
    "estimated_cost_usd": 18.50
  }
}
```

### 3.2 DELEGATEs

#### List DELEGATEs
```
GET /api/v1/delegates?session_id={sid}&role=senior_engineer&effort=high
Query Parameters:
  - session_id: Filter by session (required)
  - role: Filter by agent role
  - effort: Filter by effort level
  - status: Filter by status (pending, completed, failed)
  - since: Filter by creation date
  - limit: Max results

Response:
{
  "delegates": [
    {
      "task_id": "2026-05-24-task1",
      "role": "senior_engineer",
      "effort": "high",
      "scope": "...",
      "created_at": "2026-05-24T10:15:00Z",
      "status": "completed",
      "handback_quality": 92
    }
  ],
  "total": 5,
  "count": 5
}
```

#### Get DELEGATE Details
```
GET /api/v1/delegates/{task_id}

Response:
{
  "task_id": "2026-05-24-task1",
  "session_id": "771628bc-263c-4c9e-98c9-5f24a6418b95",
  "role": "senior_engineer",
  "model": "claude-sonnet-4.6",
  "effort": "high",
  "estimated_hours": 20,
  "scope": "...",
  "success_criteria": [...],
  "plan": [...],
  "created_at": "2026-05-24T10:15:00Z",
  "delegated_at": "2026-05-24T10:16:00Z",
  "payload": { ... }
}
```

### 3.3 HANDBACKs

#### List HANDBACKs with Filtering
```
GET /api/v1/handbacks?session_id={sid}&quality_score_min=80&status=complete
Query Parameters:
  - session_id: Required
  - status: complete, failed, partial, blocked
  - quality_score_min: Minimum quality score
  - quality_score_max: Maximum quality score
  - since: Filter by received date
  - limit: Max results

Response:
{
  "handbacks": [
    {
      "task_id": "2026-05-24-task1",
      "status": "complete",
      "quality_score": 92,
      "tokens_in": 45230,
      "tokens_out": 12847,
      "duration_minutes": 180,
      "received_at": "2026-05-24T12:40:00Z"
    }
  ],
  "total": 3,
  "average_quality": 91.3
}
```

#### Get HANDBACK Details
```
GET /api/v1/handbacks/{task_id}

Response: Full HANDBACK YAML as JSON
```

### 3.4 Execution Logs

#### Query Logs
```
GET /api/v1/logs?session_id={sid}&agent_type=engineer&level=ERROR
Query Parameters:
  - session_id: Required
  - task_id: Filter by task
  - agent_type: Filter by agent
  - phase: Filter by execution phase
  - level: DEBUG, INFO, WARNING, ERROR, CRITICAL
  - since: Start timestamp
  - until: End timestamp
  - search: Full-text search in message
  - limit: Max results (default 100)

Response:
{
  "logs": [
    {
      "timestamp": "2026-05-24T10:15:23.456Z",
      "agent_type": "engineer",
      "phase": "phase1",
      "level": "ERROR",
      "message": "Task failed: ...",
      "context": { ... }
    }
  ],
  "total": 42
}
```

### 3.5 Thinking Outputs

#### Get Thinking for Task
```
GET /api/v1/thinking/{task_id}

Response:
{
  "task_id": "2026-05-24-task1",
  "model": "claude-sonnet-4.6",
  "content": "# Chain-of-Thought...",
  "created_at": "2026-05-24T10:15:00Z"
}
```

### 3.6 Feedback

#### List Feedback
```
GET /api/v1/feedback?session_id={sid}&approve=true
Query Parameters:
  - session_id: Required
  - task_id: Filter by task
  - reviewer: Filter by reviewer
  - approve: true/false
  - since: Filter by date

Response:
{
  "feedback": [
    {
      "task_id": "2026-05-24-task1",
      "reviewer": "lead-engineer",
      "approve": true,
      "notes": "...",
      "created_at": "2026-05-24T13:00:00Z"
    }
  ]
}
```

### 3.7 Metrics

#### Get Token Usage
```
GET /api/v1/metrics/tokens?session_id={sid}

Response:
{
  "total_tokens": 245000,
  "by_role": {
    "engineer": 50000,
    "senior_engineer": 145000,
    "lead_engineer": 50000
  },
  "by_model": {
    "claude-haiku-4.5": 40000,
    "claude-sonnet-4.6": 200000,
    "claude-opus-4.7": 5000
  },
  "timeline": [
    {"date": "2026-05-24", "tokens": 50000},
    {"date": "2026-05-25", "tokens": 75000}
  ]
}
```

#### Get Quality Metrics
```
GET /api/v1/metrics/quality?session_id={sid}

Response:
{
  "average_quality": 88.5,
  "by_status": {
    "complete": 92.1,
    "partial": 65.0,
    "failed": 30.0
  },
  "by_role": {
    "engineer": 82.0,
    "senior_engineer": 91.0,
    "lead_engineer": 85.0
  }
}
```

#### Get Cost Analysis
```
GET /api/v1/metrics/cost?session_id={sid}

Response:
{
  "total_cost_usd": 18.50,
  "by_model": {
    "claude-haiku-4.5": {"cost": 0.32, "tokens": 40000},
    "claude-sonnet-4.6": {"cost": 18.0, "tokens": 200000},
    "claude-opus-4.7": {"cost": 0.375, "tokens": 5000}
  }
}
```

---

## 4. GraphQL Schema (Alternative)

```graphql
type Query {
  # Sessions
  sessions(
    userId: String
    repository: String
    since: DateTime
    limit: Int = 50
    offset: Int = 0
  ): SessionConnection!
  
  session(sessionId: UUID!): Session!
  
  # Delegates
  delegates(
    sessionId: UUID!
    role: AgentRole
    effort: Effort
    status: DelegateStatus
  ): DelegateConnection!
  
  delegate(taskId: String!): Delegate!
  
  # Handbacks
  handbacks(
    sessionId: UUID!
    status: HandbackStatus
    qualityScoreMin: Int
    qualityScoreMax: Int
  ): HandbackConnection!
  
  handback(taskId: String!): Handback!
  
  # Logs
  logs(
    sessionId: UUID!
    taskId: String
    agentType: String
    level: LogLevel
    since: DateTime
    search: String
  ): LogConnection!
  
  # Metrics
  tokenMetrics(sessionId: UUID!): TokenMetrics!
  qualityMetrics(sessionId: UUID!): QualityMetrics!
  costMetrics(sessionId: UUID!): CostMetrics!
}

type Session {
  sessionId: UUID!
  user: String!
  repository: String!
  branch: String!
  createdAt: DateTime!
  completedAt: DateTime
  phase: String
  delegates: [Delegate!]!
  handbacks: [Handback!]!
  timeline: [TimelineEvent!]!
  metrics: SessionMetrics!
}

type Delegate {
  taskId: String!
  role: AgentRole!
  model: String!
  effort: Effort!
  scope: String!
  createdAt: DateTime!
  status: DelegateStatus!
  handback: Handback
}

type Handback {
  taskId: String!
  status: HandbackStatus!
  qualityScore: Int!
  tokensIn: Int!
  tokensOut: Int!
  receivedAt: DateTime!
  delegate: Delegate!
  feedback: [Feedback!]!
}

enum LogLevel {
  DEBUG
  INFO
  WARNING
  ERROR
  CRITICAL
}

enum AgentRole {
  ENGINEER
  SENIOR_ENGINEER
  LEAD_ENGINEER
  PRINCIPAL_ENGINEER
  SECURITY_ENGINEER
  QUALITY_ENGINEER
  MODEL_ENGINEER
}

enum Effort {
  LOW
  MEDIUM
  HIGH
  MAX
  EPIC
}

enum DelegateStatus {
  PENDING
  ASSIGNED
  COMPLETED
  FAILED
}

enum HandbackStatus {
  COMPLETE
  FAILED
  PARTIAL
  BLOCKED
}

type TokenMetrics {
  totalTokens: Int!
  byRole: [RoleTokens!]!
  byModel: [ModelTokens!]!
  timeline: [DateTokens!]!
}

type RoleTokens {
  role: AgentRole!
  tokens: Int!
}

type ModelTokens {
  model: String!
  tokens: Int!
}

type DateTokens {
  date: Date!
  tokens: Int!
}
```

---

## 5. Migration Strategy

### 5.1 Phase-by-Phase Migration

**Phase 1: File-Based + Indexing** (Current/Now)
- Memory stored as files in `~/.agentic-engineers/{session_id}/memory/`
- Index files (`index.jsonl`) for fast lookups
- Query layer abstracts file I/O

**Phase 2: Database in Parallel** (3-6 months out)
- PostgreSQL/SQLite instance running alongside files
- Agents write to BOTH file and database
- Query layer chooses source (configurable)

**Phase 3: Database Primary** (6-12 months out)
- Read primarily from database
- File writes archived to S3/backup
- Query layer prefers database

**Phase 4: File Removal** (12+ months)
- Legacy files archived
- Database is authoritative source

### 5.2 Write-Through Cache

```python
class MemoryService:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.file_store = FileMemoryStore(session_id)
        self.db_store = Optional[DBMemoryStore]  # None until Phase 2
    
    def write_delegate(self, delegate: Dict):
        # Write to file (immediate)
        self.file_store.write_delegate(delegate)
        
        # Write to DB (if available)
        if self.db_store:
            self.db_store.write_delegate(delegate)
    
    def query_delegates(self, **filters):
        # If DB available, query it (faster)
        if self.db_store:
            return self.db_store.query_delegates(**filters)
        
        # Fall back to files
        return self.file_store.query_delegates(**filters)
```

### 5.3 Data Synchronization

If file and DB get out of sync:

```python
def reconcile_stores(session_id: str):
    """Ensure file and DB stores are in sync."""
    file_store = FileMemoryStore(session_id)
    db_store = DBMemoryStore()
    
    # Get all files
    file_delegates = file_store.list_all_delegates()
    
    # Get DB records
    db_delegates = db_store.query_delegates(session_id=session_id)
    db_task_ids = {d["task_id"] for d in db_delegates}
    
    # Find missing in DB
    for delegate in file_delegates:
        if delegate["task_id"] not in db_task_ids:
            # Write to DB
            db_store.write_delegate(session_id, delegate)
            logger.info(f"Synced delegate {delegate['task_id']} to DB")
```

---

## 6. Performance Targets

| Operation | File-Based | Database | Target |
|-----------|-----------|----------|--------|
| Write DELEGATE | 10ms | 50ms | <100ms |
| Read DELEGATE | 5ms | 20ms | <50ms |
| Query 100 tasks | 500ms | 50ms | <200ms |
| Search logs | 2s | 100ms | <500ms |
| Aggregate metrics | 1s | 50ms | <200ms |
| Cross-session query | N/A | 500ms | <1s |

---

## 7. Security & Access Control

### 7.1 API Authentication

```
Authorization: Bearer {jwt_token}

Claims:
  - sub: user_id
  - session_ids: [list of accessible sessions]
  - scope: read:memory, write:memory, admin:memory
```

### 7.2 Row-Level Security

Agents can only read/write their own session's memory:

```sql
-- PostgreSQL RLS policy
CREATE POLICY delegates_own_session ON delegates
    FOR SELECT
    USING (session_id = current_user_session_id());
```

### 7.3 Audit Trail

All API calls logged to `audit_log` table:

```json
{
  "operation": "GET /api/v1/handbacks",
  "user": "niallyoung",
  "session_id": "771628bc-263c-4c9e-98c9-5f24a6418b95",
  "timestamp": "2026-05-24T14:30:00Z",
  "parameters": {"quality_score_min": 80},
  "result_count": 3
}
```

---

## 8. Monitoring & Observability

### 8.1 Metrics

```
memory_api.request.count
memory_api.request.duration_ms
memory_api.query.count (by query type)
memory_api.error.count (by error type)
database.connection_pool.active
database.query.duration_ms
```

### 8.2 Alerting

- Query latency > 1s → Alert
- Error rate > 1% → Alert
- Database connection pool > 80% → Alert
- Audit log size > 10GB → Alert (archive)

---

## 9. Example Implementation Timeline

- **Week 1-2**: Database design + schema creation
- **Week 3-4**: REST API endpoints (read-only)
- **Week 5-6**: Write endpoints + validation
- **Week 7-8**: GraphQL layer
- **Week 9-10**: Authentication + authorization
- **Week 11-12**: Migration tools + testing
- **Week 13-16**: Performance tuning + rollout

---

## 10. Backward Compatibility

File-based API continues to work:

```python
# Old API (still works)
memory = MemoryManager(session_id)
delegates = memory.delegates.query(role="engineer")

# New API (future)
delegates = api_client.query_delegates(
    session_id=session_id,
    role="engineer"
)
```

---

## References

- `docs/MEMORY-ARCHITECTURE.md` — Architecture overview
- `docs/MEMORY-STORAGE-SCHEMA.yaml` — File storage schema
- `docs/MEMORY-STORAGE-INTEGRATION.md` — Integration guide
- PostgreSQL documentation: https://www.postgresql.org/docs/
- GraphQL specification: https://spec.graphql.org/
