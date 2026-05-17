# Distributed Caching Layer — Deployment Guide

**Version**: 1.0  
**Date**: 2026-05-17  
**Audience**: Platform engineers, SREs

---

## 1. Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | ≥ 3.9 |
| redis-py | ≥ 4.0 (only for `RedisBackend`) |
| Redis server | ≥ 6.2 |

Install the Python dependency:

```bash
pip install "redis>=4.0"
```

---

## 2. Quick Start

### 2.1 LRU-only (no Redis)

```python
from src.cache import CacheManager

cache = CacheManager(namespace="myservice", default_ttl=300)
cache.set("user:42", {"name": "Alice"})
value = cache.get("user:42")   # {"name": "Alice"}
cache.close()
```

### 2.2 Redis primary with LRU fallback

```python
from src.cache import CacheManager, RedisBackend, LRUBackend

redis_backend = RedisBackend(
    host="redis.internal",
    port=6379,
    password="s3cr3t",
    socket_timeout=0.5,
)
lru_fallback = LRUBackend(capacity=5_000)

cache = CacheManager(
    namespace="myservice",
    primary=redis_backend,
    fallback=lru_fallback,
    default_ttl=600,
)
```

### 2.3 Context-manager pattern

```python
with CacheManager(namespace="job", primary=redis_backend) as cache:
    cache.set("result:99", heavy_computation())
    return cache.get("result:99")
```

---

## 3. Configuration Reference

### CacheManager

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `namespace` | `str` | `"default"` | Key prefix for isolation |
| `primary` | `_CacheBackend` | `LRUBackend()` | Primary backend |
| `fallback` | `_CacheBackend \| None` | `None` | Fallback backend |
| `default_ttl` | `int \| None` | `None` | Default TTL in seconds |
| `metrics` | `CacheMetrics` | new instance | Prometheus counters |

### RedisBackend

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `host` | `str` | `"localhost"` | Redis hostname |
| `port` | `int` | `6379` | Redis port |
| `db` | `int` | `0` | Redis database index |
| `password` | `str \| None` | `None` | Redis AUTH password |
| `socket_timeout` | `float` | `1.0` | Socket timeout in seconds |
| `redis_client` | `Any` | `None` | Inject pre-built client |

### LRUBackend

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `capacity` | `int` | `1000` | Maximum number of entries |

---

## 4. Redis Server Setup

### 4.1 Minimal redis.conf

```
bind 127.0.0.1
port 6379
requirepass <strong-password>
maxmemory 512mb
maxmemory-policy allkeys-lru
save ""
```

### 4.2 Docker

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 512mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

### 4.3 Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          args:
            - redis-server
            - --requirepass
            - $(REDIS_PASSWORD)
            - --maxmemory
            - 512mb
            - --maxmemory-policy
            - allkeys-lru
          env:
            - name: REDIS_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: redis-secret
                  key: password
          ports:
            - containerPort: 6379
```

---

## 5. Observability

### 5.1 Metrics

The `CacheMetrics` object on each `CacheManager` instance exposes five counters:

```python
print(cache.metrics.hits.value)      # total hits
print(cache.metrics.misses.value)    # total misses
print(cache.metrics.errors.value)    # backend errors
print(cache.metrics.fallbacks.value) # fallback activations
print(cache.metrics.evictions.value) # LRU evictions (not wired by default)
```

To wire into Prometheus, replace `_Counter` with `prometheus_client.Counter` at startup:

```python
from prometheus_client import Counter
from src.cache import CacheMetrics, _Counter

class PrometheusCounter:
    def __init__(self, name, description, labels):
        self._c = Counter(name, description, labels)
        self._labels = labels

    def inc(self, amount=1.0):
        self._c.inc(amount)

    @property
    def value(self):
        return self._c._value.get()
```

### 5.2 Recommended Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| High miss rate | `cache_misses / (cache_hits + cache_misses) > 0.5` | Warning |
| Frequent fallbacks | `rate(cache_fallback_total[5m]) > 1` | Critical |
| Backend errors | `rate(cache_errors_total[1m]) > 0` | Warning |

---

## 6. Running Tests

```bash
# All cache tests
pytest tests/test_cache.py -v

# With coverage report
pytest tests/test_cache.py --cov=src/cache --cov-report=term-missing

# Performance benchmarks only
pytest tests/test_cache.py -v -k "Performance"
```

Expected output:
```
tests/test_cache.py::TestPerformance::test_lru_hit_latency_sub_millisecond PASSED
tests/test_cache.py::TestPerformance::test_redis_hit_latency_sub_5ms PASSED
tests/test_cache.py::TestPerformance::test_lru_set_latency_sub_millisecond PASSED
```

---

## 7. Security Checklist

- [ ] Redis `requirepass` set in production
- [ ] Redis not exposed on public network interfaces
- [ ] Cache keys do not contain unsanitised user input
- [ ] `socket_timeout` set to prevent indefinite blocking (recommended: ≤ 1 s)
- [ ] Secrets passed via environment variables, not hardcoded

---

## 8. Troubleshooting

| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| `CacheBackendError: redis-py is not installed` | Missing dependency | `pip install redis` |
| All gets return `None` after restart | LRU is in-process (non-persistent) | Use Redis backend for persistence |
| High fallback rate | Redis connection issues | Check Redis health; increase `socket_timeout` |
| `CacheBackendError: Redis SET failed: WRONGTYPE` | Key collision with non-string type | Flush namespace or change namespace prefix |
| Memory pressure on Redis | TTLs too long or no `maxmemory` | Set `maxmemory` and `maxmemory-policy allkeys-lru` |
