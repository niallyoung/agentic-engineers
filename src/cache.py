"""
Distributed caching layer with Redis backend and LRU fallback.

Public API
----------
CacheManager   — high-level facade (namespace, serialisation, metrics, fallback)
RedisBackend   — Redis-backed store (requires redis-py)
LRUBackend     — In-process LRU store (zero dependencies)
CacheBackendError — raised by backends on unrecoverable errors
"""

from __future__ import annotations

import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CacheBackendError(Exception):
    """Raised by a backend when it cannot fulfil a request."""


# ---------------------------------------------------------------------------
# Metrics stub (local metrics tracking only)
# ---------------------------------------------------------------------------


class _Counter:
    """In-memory counter for local metrics tracking."""

    def __init__(self) -> None:
        self._value: float = 0.0

    def inc(self, amount: float = 1.0) -> None:
        self._value += amount

    @property
    def value(self) -> float:
        return self._value


@dataclass
class CacheMetrics:
    """In-process counters for cache observability."""

    hits: _Counter = field(default_factory=_Counter)
    misses: _Counter = field(default_factory=_Counter)
    errors: _Counter = field(default_factory=_Counter)
    fallbacks: _Counter = field(default_factory=_Counter)
    evictions: _Counter = field(default_factory=_Counter)


# ---------------------------------------------------------------------------
# Backend protocol
# ---------------------------------------------------------------------------


class _CacheBackend:
    """Abstract interface that every backend must implement."""

    def get(self, key: str) -> Optional[str]:
        raise NotImplementedError

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def flush_namespace(self, prefix: str) -> int:
        """Delete all keys whose name starts with *prefix*. Returns count."""
        raise NotImplementedError

    def close(self) -> None:
        """Release any held resources."""


# ---------------------------------------------------------------------------
# LRU Backend
# ---------------------------------------------------------------------------


class LRUBackend(_CacheBackend):
    """
    In-process LRU cache with optional per-entry TTL.

    Thread-safety: NOT thread-safe. Wrap with a lock if shared across threads.
    """

    def __init__(self, capacity: int = 1_000) -> None:
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self._capacity = capacity
        # OrderedDict: key → (value_str, expires_at | None)
        self._store: OrderedDict[str, tuple[str, Optional[float]]] = OrderedDict()
        self.eviction_count: int = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_expired(self, expires_at: Optional[float]) -> bool:
        return expires_at is not None and time.monotonic() >= expires_at

    def _evict_expired(self) -> None:
        """Remove all expired entries (lazy GC)."""
        expired = [k for k, (_, exp) in self._store.items() if self._is_expired(exp)]
        for k in expired:
            del self._store[k]

    # ------------------------------------------------------------------
    # Backend API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[str]:
        if key not in self._store:
            return None
        value, expires_at = self._store[key]
        if self._is_expired(expires_at):
            del self._store[key]
            return None
        # Move to end (most-recently-used)
        self._store.move_to_end(key)
        return value

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        expires_at = (time.monotonic() + ttl) if ttl is not None else None
        if key in self._store:
            self._store.move_to_end(key)
            self._store[key] = (value, expires_at)
            return
        # Evict LRU entry if at capacity
        if len(self._store) >= self._capacity:
            self._store.popitem(last=False)
            self.eviction_count += 1
        self._store[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def flush_namespace(self, prefix: str) -> int:
        keys = [k for k in list(self._store) if k.startswith(prefix)]
        for k in keys:
            del self._store[k]
        return len(keys)

    def close(self) -> None:
        self._store.clear()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        return len(self._store)

    @property
    def capacity(self) -> int:
        return self._capacity


# ---------------------------------------------------------------------------
# Redis Backend
# ---------------------------------------------------------------------------


class RedisBackend(_CacheBackend):
    """
    Redis-backed cache store.

    Parameters
    ----------
    host, port, db, password, socket_timeout:
        Passed directly to ``redis.Redis``.
    redis_client:
        Inject a pre-built client (useful for testing with fakeredis).
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        socket_timeout: float = 1.0,
        redis_client: Any = None,
    ) -> None:
        if redis_client is not None:
            self._redis = redis_client
        else:
            try:
                import redis  # type: ignore[import]
            except ImportError as exc:
                raise CacheBackendError(
                    "redis-py is not installed. Run: pip install redis"
                ) from exc
            self._redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                socket_timeout=socket_timeout,
                decode_responses=True,
            )

    # ------------------------------------------------------------------
    # Backend API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[str]:
        try:
            return self._redis.get(key)
        except Exception as exc:
            raise CacheBackendError(f"Redis GET failed: {exc}") from exc

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        try:
            if ttl is not None:
                self._redis.set(key, value, ex=ttl)
            else:
                self._redis.set(key, value)
        except Exception as exc:
            raise CacheBackendError(f"Redis SET failed: {exc}") from exc

    def delete(self, key: str) -> None:
        try:
            self._redis.delete(key)
        except Exception as exc:
            raise CacheBackendError(f"Redis DEL failed: {exc}") from exc

    def flush_namespace(self, prefix: str) -> int:
        """Use SCAN to find and delete all keys with the given prefix."""
        try:
            deleted = 0
            cursor = 0
            pattern = f"{prefix}*"
            while True:
                cursor, keys = self._redis.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    self._redis.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break
            return deleted
        except Exception as exc:
            raise CacheBackendError(f"Redis SCAN/DEL failed: {exc}") from exc

    def close(self) -> None:
        try:
            self._redis.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# CacheManager (public facade)
# ---------------------------------------------------------------------------


class CacheManager:
    """
    High-level caching facade with namespace isolation, JSON serialisation,
    automatic fallback to LRU, and in-process metrics.

    Parameters
    ----------
    namespace:
        String prefix applied to every key (e.g. ``"session"``).
    primary:
        Primary backend (default: ``LRUBackend``).
    fallback:
        Fallback backend used when *primary* raises ``CacheBackendError``.
        Pass ``None`` to disable fallback.
    default_ttl:
        Default TTL in seconds applied when ``ttl`` is not specified in
        ``set()``. ``None`` means no expiry.
    metrics:
        ``CacheMetrics`` instance. A fresh one is created if not provided.
    """

    def __init__(
        self,
        namespace: str = "default",
        primary: Optional[_CacheBackend] = None,
        fallback: Optional[_CacheBackend] = None,
        default_ttl: Optional[int] = None,
        metrics: Optional[CacheMetrics] = None,
    ) -> None:
        self._namespace = namespace
        self._primary: _CacheBackend = primary if primary is not None else LRUBackend()
        self._fallback: Optional[_CacheBackend] = fallback
        self._default_ttl = default_ttl
        self.metrics: CacheMetrics = metrics if metrics is not None else CacheMetrics()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _full_key(self, key: str) -> str:
        return f"{self._namespace}:{key}"

    def _serialise(self, value: Any) -> str:
        return json.dumps(value)

    def _deserialise(self, raw: str) -> Any:
        return json.loads(raw)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value by key.

        Returns the deserialised value, or ``None`` on a miss.
        Falls back to the LRU backend if the primary raises an error.
        """
        full_key = self._full_key(key)
        try:
            raw = self._primary.get(full_key)
            if raw is None:
                self.metrics.misses.inc()
                return None
            self.metrics.hits.inc()
            return self._deserialise(raw)
        except CacheBackendError:
            self.metrics.errors.inc()
            return self._fallback_get(full_key)

    def _fallback_get(self, full_key: str) -> Optional[Any]:
        if self._fallback is None:
            return None
        self.metrics.fallbacks.inc()
        try:
            raw = self._fallback.get(full_key)
            if raw is None:
                self.metrics.misses.inc()
                return None
            self.metrics.hits.inc()
            return self._deserialise(raw)
        except CacheBackendError:
            self.metrics.errors.inc()
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Store a value under *key*.

        Parameters
        ----------
        ttl:
            Time-to-live in seconds. Overrides ``default_ttl`` when provided.

        Returns
        -------
        bool
            ``True`` on success, ``False`` if both primary and fallback failed.
        """
        full_key = self._full_key(key)
        effective_ttl = ttl if ttl is not None else self._default_ttl
        raw = self._serialise(value)
        try:
            self._primary.set(full_key, raw, effective_ttl)
            return True
        except CacheBackendError:
            self.metrics.errors.inc()
            return self._fallback_set(full_key, raw, effective_ttl)

    def _fallback_set(self, full_key: str, raw: str, ttl: Optional[int]) -> bool:
        if self._fallback is None:
            return False
        self.metrics.fallbacks.inc()
        try:
            self._fallback.set(full_key, raw, ttl)
            return True
        except CacheBackendError:
            self.metrics.errors.inc()
            return False

    def delete(self, key: str) -> None:
        """Remove a single key from the cache (best-effort on both backends)."""
        full_key = self._full_key(key)
        try:
            self._primary.delete(full_key)
        except CacheBackendError:
            self.metrics.errors.inc()
        if self._fallback is not None:
            try:
                self._fallback.delete(full_key)
            except CacheBackendError:
                self.metrics.errors.inc()

    def flush(self) -> int:
        """
        Delete all keys belonging to this namespace.

        Returns the total number of keys removed across both backends.
        """
        prefix = f"{self._namespace}:"
        total = 0
        try:
            total += self._primary.flush_namespace(prefix)
        except CacheBackendError:
            self.metrics.errors.inc()
        if self._fallback is not None:
            try:
                total += self._fallback.flush_namespace(prefix)
            except CacheBackendError:
                self.metrics.errors.inc()
        return total

    def close(self) -> None:
        """Release resources held by both backends."""
        self._primary.close()
        if self._fallback is not None:
            self._fallback.close()

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "CacheManager":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
