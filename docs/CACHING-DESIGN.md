# Distributed Caching Layer — Architecture Design

**Version**: 1.0  
**Date**: 2026-05-17  
**Author**: Senior Engineer Agent  
**Status**: Approved

---

## 1. Overview

This document describes the architecture of the distributed caching layer introduced for the agentic-engineers platform. The layer provides low-latency key/value caching backed by Redis, with an in-process LRU fallback for environments where Redis is unavailable.

---

## 2. Goals

| Goal | Target |
|------|--------|
| Cache-hit latency | < 1 ms (local LRU), < 5 ms (Redis) |
| Availability | Graceful degradation to LRU when Redis is down |
| Consistency | TTL-based expiry; explicit invalidation API |
| Observability | Hit/miss/error counters exposed via Prometheus metrics |
| Testability | 100 % unit-test coverage; no live Redis required in CI |

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
└───────────────────────┬─────────────────────────────────┘
                        │  get / set / delete / flush
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  CacheManager (facade)                   │
│  • Namespace prefixing                                   │
│  • Serialisation (JSON)                                  │
│  • Metrics instrumentation                               │
└────────────┬──────────────────────────┬─────────────────┘
             │ primary                  │ fallback
             ▼                          ▼
┌────────────────────┐      ┌───────────────────────────┐
│   RedisBackend     │      │      LRUBackend            │
│  (redis-py async)  │      │  (collections.OrderedDict) │
│  TTL via EXPIRE    │      │  TTL via timestamp check   │
│  Cluster-aware     │      │  Max 1 000 entries         │
└────────────────────┘      └───────────────────────────┘
```

### 3.1 CacheManager

The public API surface. Responsibilities:

- **Namespace prefixing** — every key is stored as `{namespace}:{key}` to isolate tenants/services.
- **Serialisation** — values are JSON-encoded before storage and decoded on retrieval.
- **Fallback logic** — on any `RedisBackend` exception, the manager transparently retries against `LRUBackend` and increments the `cache_fallback_total` counter.
- **Metrics** — wraps every operation with hit/miss/error Prometheus counters.

### 3.2 RedisBackend

- Uses `redis-py` (sync) with connection-pool reuse.
- `set` maps to `SET key value EX ttl`.
- `delete` maps to `DEL key`.
- `flush_namespace` uses `SCAN` + batched `DEL` to avoid blocking the server.
- Connection errors propagate as `CacheBackendError` so `CacheManager` can fall back.

### 3.3 LRUBackend

- Pure-Python, zero dependencies.
- Evicts the least-recently-used entry when the capacity limit (default 1 000) is reached.
- TTL is enforced lazily on `get` (expired entries are treated as misses and removed).

---

## 4. Key Design Decisions & Trade-offs

### 4.1 Sync vs Async

| Option | Pros | Cons |
|--------|------|------|
| Sync (chosen) | Simple integration; no event-loop coupling | Blocks thread on network I/O |
| Async | Non-blocking | Requires `asyncio` throughout call stack |

**Decision**: Sync for v1. The platform's hot paths are CPU-bound (LLM calls dominate latency). A thread-pool executor wrapper can be added in v2 if needed.

### 4.2 Serialisation

JSON was chosen over pickle for security (no arbitrary code execution on deserialisation) and cross-language compatibility. The trade-off is that only JSON-serialisable types are supported; callers must serialise complex objects before caching.

### 4.3 Fallback Granularity

Fallback is per-operation (not per-connection). This means a flapping Redis connection results in mixed storage — some keys in Redis, some in LRU. This is acceptable because the cache is a performance optimisation, not a source of truth.

### 4.4 Namespace Flushing

`flush_namespace` on `RedisBackend` uses `SCAN` (non-blocking) rather than `KEYS` (blocking). On large keyspaces this is slower but safe for production use.

---

## 5. Metrics

All metrics are labelled with `namespace` and `backend` (`redis` | `lru`).

| Metric | Type | Description |
|--------|------|-------------|
| `cache_hits_total` | Counter | Successful cache retrievals |
| `cache_misses_total` | Counter | Cache misses (key absent or expired) |
| `cache_errors_total` | Counter | Backend errors (triggers fallback) |
| `cache_fallback_total` | Counter | Operations served by LRU after Redis error |
| `cache_evictions_total` | Counter | LRU capacity evictions |

---

## 6. Security Considerations

- Redis should be deployed inside the private network with `requirepass` set.
- Keys must not contain user-controlled data without sanitisation (namespace injection).
- JSON deserialisation is safe; pickle is explicitly not used.

---

## 7. Future Work

- Async interface (`AsyncCacheManager`) backed by `aioredis`.
- Cache-aside decorator (`@cached(ttl=60)`).
- Multi-tier: L1 (in-process LRU) → L2 (Redis) → L3 (remote Redis cluster).
- Distributed invalidation via Redis Pub/Sub.
