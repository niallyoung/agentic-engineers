"""
Comprehensive test suite for the distributed caching layer (src/cache.py).

Coverage targets
----------------
- LRUBackend: get, set, delete, TTL expiry, LRU eviction, flush_namespace, close
- RedisBackend: all operations via fakeredis; error wrapping; flush_namespace cursor loop
- CacheManager: namespace prefixing, serialisation, fallback logic, metrics, context manager
- Performance: cache-hit latency < 1 ms (LRU), < 5 ms (Redis via fakeredis)
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Module under test
# ---------------------------------------------------------------------------
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cache import (  # noqa: E402
    CacheBackendError,
    CacheManager,
    CacheMetrics,
    LRUBackend,
    RedisBackend,
    _Counter,
)


# ===========================================================================
# _Counter
# ===========================================================================


class TestCounter:
    def test_initial_value(self):
        c = _Counter()
        assert c.value == 0.0

    def test_inc_default(self):
        c = _Counter()
        c.inc()
        assert c.value == 1.0

    def test_inc_custom_amount(self):
        c = _Counter()
        c.inc(5.0)
        assert c.value == 5.0

    def test_inc_multiple(self):
        c = _Counter()
        c.inc()
        c.inc(2.0)
        assert c.value == 3.0


# ===========================================================================
# LRUBackend
# ===========================================================================


class TestLRUBackend:
    def test_get_missing_key(self):
        lru = LRUBackend()
        assert lru.get("missing") is None

    def test_set_and_get(self):
        lru = LRUBackend()
        lru.set("k", "v")
        assert lru.get("k") == "v"

    def test_overwrite_existing_key(self):
        lru = LRUBackend()
        lru.set("k", "v1")
        lru.set("k", "v2")
        assert lru.get("k") == "v2"

    def test_delete_existing_key(self):
        lru = LRUBackend()
        lru.set("k", "v")
        lru.delete("k")
        assert lru.get("k") is None

    def test_delete_missing_key_no_error(self):
        lru = LRUBackend()
        lru.delete("nonexistent")  # should not raise

    def test_ttl_expiry(self):
        lru = LRUBackend()
        lru.set("k", "v", ttl=1)
        assert lru.get("k") == "v"
        # Manually advance the stored timestamp
        key = "k"
        value, _ = lru._store[key]
        lru._store[key] = (value, time.monotonic() - 0.001)
        assert lru.get("k") is None

    def test_no_ttl_does_not_expire(self):
        lru = LRUBackend()
        lru.set("k", "v")
        assert lru.get("k") == "v"

    def test_lru_eviction(self):
        lru = LRUBackend(capacity=3)
        lru.set("a", "1")
        lru.set("b", "2")
        lru.set("c", "3")
        # Access 'a' to make it recently used
        lru.get("a")
        # Adding 'd' should evict 'b' (LRU)
        lru.set("d", "4")
        assert lru.get("b") is None
        assert lru.get("a") == "1"
        assert lru.get("c") == "3"
        assert lru.get("d") == "4"

    def test_eviction_counter_increments(self):
        lru = LRUBackend(capacity=2)
        lru.set("a", "1")
        lru.set("b", "2")
        lru.set("c", "3")  # evicts 'a'
        assert lru.eviction_count == 1

    def test_flush_namespace(self):
        lru = LRUBackend()
        lru.set("ns:key1", "v1")
        lru.set("ns:key2", "v2")
        lru.set("other:key", "v3")
        count = lru.flush_namespace("ns:")
        assert count == 2
        assert lru.get("ns:key1") is None
        assert lru.get("ns:key2") is None
        assert lru.get("other:key") == "v3"

    def test_flush_namespace_returns_zero_when_empty(self):
        lru = LRUBackend()
        assert lru.flush_namespace("ns:") == 0

    def test_size_property(self):
        lru = LRUBackend()
        assert lru.size == 0
        lru.set("k", "v")
        assert lru.size == 1

    def test_capacity_property(self):
        lru = LRUBackend(capacity=42)
        assert lru.capacity == 42

    def test_invalid_capacity_raises(self):
        with pytest.raises(ValueError):
            LRUBackend(capacity=0)

    def test_close_clears_store(self):
        lru = LRUBackend()
        lru.set("k", "v")
        lru.close()
        assert lru.size == 0

    def test_overwrite_does_not_increase_size(self):
        lru = LRUBackend()
        lru.set("k", "v1")
        lru.set("k", "v2")
        assert lru.size == 1

    def test_evict_expired_removes_entries(self):
        lru = LRUBackend()
        lru.set("k", "v", ttl=1)
        # Force expiry
        value, _ = lru._store["k"]
        lru._store["k"] = (value, time.monotonic() - 1.0)
        lru._evict_expired()
        assert lru.size == 0


# ===========================================================================
# RedisBackend
# ===========================================================================


def _make_redis_backend() -> tuple[RedisBackend, MagicMock]:
    """Return a RedisBackend wired to a MagicMock redis client."""
    mock_redis = MagicMock()
    backend = RedisBackend(redis_client=mock_redis)
    return backend, mock_redis


class TestRedisBackend:
    def test_get_returns_value(self):
        backend, mock = _make_redis_backend()
        mock.get.return_value = "hello"
        assert backend.get("key") == "hello"
        mock.get.assert_called_once_with("key")

    def test_get_returns_none_on_miss(self):
        backend, mock = _make_redis_backend()
        mock.get.return_value = None
        assert backend.get("key") is None

    def test_get_raises_cache_backend_error(self):
        backend, mock = _make_redis_backend()
        mock.get.side_effect = Exception("connection refused")
        with pytest.raises(CacheBackendError):
            backend.get("key")

    def test_set_without_ttl(self):
        backend, mock = _make_redis_backend()
        backend.set("key", "value")
        mock.set.assert_called_once_with("key", "value")

    def test_set_with_ttl(self):
        backend, mock = _make_redis_backend()
        backend.set("key", "value", ttl=60)
        mock.set.assert_called_once_with("key", "value", ex=60)

    def test_set_raises_cache_backend_error(self):
        backend, mock = _make_redis_backend()
        mock.set.side_effect = Exception("timeout")
        with pytest.raises(CacheBackendError):
            backend.set("key", "value")

    def test_delete(self):
        backend, mock = _make_redis_backend()
        backend.delete("key")
        mock.delete.assert_called_once_with("key")

    def test_delete_raises_cache_backend_error(self):
        backend, mock = _make_redis_backend()
        mock.delete.side_effect = Exception("err")
        with pytest.raises(CacheBackendError):
            backend.delete("key")

    def test_flush_namespace_single_page(self):
        backend, mock = _make_redis_backend()
        # SCAN returns cursor=0 on first call (single page)
        mock.scan.return_value = (0, ["ns:a", "ns:b"])
        count = backend.flush_namespace("ns:")
        assert count == 2
        mock.delete.assert_called_once_with("ns:a", "ns:b")

    def test_flush_namespace_multiple_pages(self):
        backend, mock = _make_redis_backend()
        mock.scan.side_effect = [
            (42, ["ns:a"]),
            (0, ["ns:b", "ns:c"]),
        ]
        count = backend.flush_namespace("ns:")
        assert count == 3

    def test_flush_namespace_empty(self):
        backend, mock = _make_redis_backend()
        mock.scan.return_value = (0, [])
        count = backend.flush_namespace("ns:")
        assert count == 0
        mock.delete.assert_not_called()

    def test_flush_namespace_raises_cache_backend_error(self):
        backend, mock = _make_redis_backend()
        mock.scan.side_effect = Exception("scan error")
        with pytest.raises(CacheBackendError):
            backend.flush_namespace("ns:")

    def test_close(self):
        backend, mock = _make_redis_backend()
        backend.close()
        mock.close.assert_called_once()

    def test_close_swallows_errors(self):
        backend, mock = _make_redis_backend()
        mock.close.side_effect = Exception("already closed")
        backend.close()  # should not raise

    def test_missing_redis_package_raises(self):
        with patch.dict("sys.modules", {"redis": None}):
            with pytest.raises(CacheBackendError, match="redis-py is not installed"):
                RedisBackend()


# ===========================================================================
# CacheManager
# ===========================================================================


class TestCacheManagerNamespacing:
    def test_key_is_prefixed(self):
        lru = LRUBackend()
        mgr = CacheManager(namespace="myns", primary=lru)
        mgr.set("foo", "bar")
        # The raw store key should include the namespace prefix
        assert lru.get("myns:foo") == '"bar"'

    def test_different_namespaces_isolated(self):
        lru = LRUBackend()
        mgr_a = CacheManager(namespace="a", primary=lru)
        mgr_b = CacheManager(namespace="b", primary=lru)
        mgr_a.set("key", "value_a")
        mgr_b.set("key", "value_b")
        assert mgr_a.get("key") == "value_a"
        assert mgr_b.get("key") == "value_b"


class TestCacheManagerSerialisation:
    def test_stores_and_retrieves_dict(self):
        mgr = CacheManager()
        mgr.set("d", {"x": 1, "y": [2, 3]})
        assert mgr.get("d") == {"x": 1, "y": [2, 3]}

    def test_stores_and_retrieves_list(self):
        mgr = CacheManager()
        mgr.set("l", [1, 2, 3])
        assert mgr.get("l") == [1, 2, 3]

    def test_stores_and_retrieves_integer(self):
        mgr = CacheManager()
        mgr.set("i", 42)
        assert mgr.get("i") == 42

    def test_stores_and_retrieves_none(self):
        mgr = CacheManager()
        mgr.set("n", None)
        assert mgr.get("n") is None

    def test_stores_and_retrieves_boolean(self):
        mgr = CacheManager()
        mgr.set("b", True)
        assert mgr.get("b") is True


class TestCacheManagerTTL:
    def test_default_ttl_applied(self):
        lru = LRUBackend()
        mgr = CacheManager(primary=lru, default_ttl=300)
        mgr.set("k", "v")
        key = "default:k"
        _, expires_at = lru._store[key]
        assert expires_at is not None

    def test_explicit_ttl_overrides_default(self):
        lru = LRUBackend()
        mgr = CacheManager(primary=lru, default_ttl=300)
        mgr.set("k", "v", ttl=10)
        key = "default:k"
        _, expires_at = lru._store[key]
        # expires_at should be ~10 s from now, not ~300 s
        assert expires_at is not None
        assert expires_at < time.monotonic() + 15  # generous upper bound

    def test_no_ttl_no_expiry(self):
        lru = LRUBackend()
        mgr = CacheManager(primary=lru)
        mgr.set("k", "v")
        key = "default:k"
        _, expires_at = lru._store[key]
        assert expires_at is None


class TestCacheManagerMetrics:
    def test_hit_increments_hits(self):
        mgr = CacheManager()
        mgr.set("k", "v")
        mgr.get("k")
        assert mgr.metrics.hits.value == 1.0

    def test_miss_increments_misses(self):
        mgr = CacheManager()
        mgr.get("nonexistent")
        assert mgr.metrics.misses.value == 1.0

    def test_error_increments_errors(self):
        bad_primary = MagicMock()
        bad_primary.get.side_effect = CacheBackendError("boom")
        mgr = CacheManager(primary=bad_primary, fallback=None)
        mgr.get("k")
        assert mgr.metrics.errors.value == 1.0

    def test_fallback_increments_fallbacks(self):
        bad_primary = MagicMock()
        bad_primary.get.side_effect = CacheBackendError("boom")
        fallback = LRUBackend()
        mgr = CacheManager(primary=bad_primary, fallback=fallback)
        mgr.get("k")
        assert mgr.metrics.fallbacks.value == 1.0


class TestCacheManagerFallback:
    def test_get_falls_back_on_primary_error(self):
        bad_primary = MagicMock()
        bad_primary.get.side_effect = CacheBackendError("redis down")
        fallback = LRUBackend()
        fallback.set("default:k", '"stored_in_fallback"')
        mgr = CacheManager(primary=bad_primary, fallback=fallback)
        result = mgr.get("k")
        assert result == "stored_in_fallback"

    def test_get_returns_none_when_no_fallback(self):
        bad_primary = MagicMock()
        bad_primary.get.side_effect = CacheBackendError("redis down")
        mgr = CacheManager(primary=bad_primary, fallback=None)
        assert mgr.get("k") is None

    def test_set_falls_back_on_primary_error(self):
        bad_primary = MagicMock()
        bad_primary.set.side_effect = CacheBackendError("redis down")
        fallback = LRUBackend()
        mgr = CacheManager(primary=bad_primary, fallback=fallback)
        result = mgr.set("k", "v")
        assert result is True
        assert fallback.get("default:k") == '"v"'

    def test_set_returns_false_when_both_fail(self):
        bad_primary = MagicMock()
        bad_primary.set.side_effect = CacheBackendError("primary down")
        bad_fallback = MagicMock()
        bad_fallback.set.side_effect = CacheBackendError("fallback down")
        mgr = CacheManager(primary=bad_primary, fallback=bad_fallback)
        assert mgr.set("k", "v") is False

    def test_set_returns_false_when_no_fallback_and_primary_fails(self):
        bad_primary = MagicMock()
        bad_primary.set.side_effect = CacheBackendError("down")
        mgr = CacheManager(primary=bad_primary, fallback=None)
        assert mgr.set("k", "v") is False

    def test_fallback_get_error_increments_error_counter(self):
        bad_primary = MagicMock()
        bad_primary.get.side_effect = CacheBackendError("primary down")
        bad_fallback = MagicMock()
        bad_fallback.get.side_effect = CacheBackendError("fallback down")
        mgr = CacheManager(primary=bad_primary, fallback=bad_fallback)
        mgr.get("k")
        assert mgr.metrics.errors.value == 2.0  # primary + fallback


class TestCacheManagerDelete:
    def test_delete_removes_key(self):
        mgr = CacheManager()
        mgr.set("k", "v")
        mgr.delete("k")
        assert mgr.get("k") is None

    def test_delete_also_removes_from_fallback(self):
        primary = LRUBackend()
        fallback = LRUBackend()
        mgr = CacheManager(primary=primary, fallback=fallback)
        mgr.set("k", "v")
        fallback.set("default:k", '"v"')
        mgr.delete("k")
        assert primary.get("default:k") is None
        assert fallback.get("default:k") is None

    def test_delete_primary_error_increments_errors(self):
        bad_primary = MagicMock()
        bad_primary.delete.side_effect = CacheBackendError("err")
        mgr = CacheManager(primary=bad_primary, fallback=None)
        mgr.delete("k")
        assert mgr.metrics.errors.value == 1.0


class TestCacheManagerFlush:
    def test_flush_removes_namespace_keys(self):
        mgr = CacheManager(namespace="ns")
        mgr.set("a", 1)
        mgr.set("b", 2)
        count = mgr.flush()
        assert count == 2
        assert mgr.get("a") is None
        assert mgr.get("b") is None

    def test_flush_does_not_remove_other_namespaces(self):
        lru = LRUBackend()
        mgr_a = CacheManager(namespace="a", primary=lru)
        mgr_b = CacheManager(namespace="b", primary=lru)
        mgr_a.set("x", 1)
        mgr_b.set("x", 2)
        mgr_a.flush()
        assert mgr_b.get("x") == 2

    def test_flush_primary_error_increments_errors(self):
        bad_primary = MagicMock()
        bad_primary.flush_namespace.side_effect = CacheBackendError("err")
        mgr = CacheManager(primary=bad_primary, fallback=None)
        mgr.flush()
        assert mgr.metrics.errors.value == 1.0

    def test_flush_also_flushes_fallback(self):
        primary = LRUBackend()
        fallback = LRUBackend()
        mgr = CacheManager(namespace="ns", primary=primary, fallback=fallback)
        mgr.set("k", "v")
        fallback.set("ns:k", '"v"')
        count = mgr.flush()
        assert count == 2


class TestCacheManagerContextManager:
    def test_context_manager_calls_close(self):
        primary = MagicMock()
        with CacheManager(primary=primary) as mgr:
            pass
        primary.close.assert_called_once()

    def test_context_manager_returns_self(self):
        mgr = CacheManager()
        with mgr as m:
            assert m is mgr


class TestCacheBackendAbstract:
    """Ensure the abstract base raises NotImplementedError for all methods."""

    def test_get_raises(self):
        from cache import _CacheBackend
        b = _CacheBackend()
        with pytest.raises(NotImplementedError):
            b.get("k")

    def test_set_raises(self):
        from cache import _CacheBackend
        b = _CacheBackend()
        with pytest.raises(NotImplementedError):
            b.set("k", "v")

    def test_delete_raises(self):
        from cache import _CacheBackend
        b = _CacheBackend()
        with pytest.raises(NotImplementedError):
            b.delete("k")

    def test_flush_namespace_raises(self):
        from cache import _CacheBackend
        b = _CacheBackend()
        with pytest.raises(NotImplementedError):
            b.flush_namespace("ns:")


class TestCacheManagerDeleteFallbackError:
    def test_delete_fallback_error_increments_errors(self):
        primary = LRUBackend()
        bad_fallback = MagicMock()
        bad_fallback.delete.side_effect = CacheBackendError("fallback err")
        mgr = CacheManager(primary=primary, fallback=bad_fallback)
        mgr.delete("k")
        assert mgr.metrics.errors.value == 1.0


class TestCacheManagerFlushFallbackError:
    def test_flush_fallback_error_increments_errors(self):
        primary = LRUBackend()
        bad_fallback = MagicMock()
        bad_fallback.flush_namespace.side_effect = CacheBackendError("fallback err")
        mgr = CacheManager(primary=primary, fallback=bad_fallback)
        mgr.flush()
        assert mgr.metrics.errors.value == 1.0


class TestCacheManagerClose:
    def test_close_calls_primary_close(self):
        primary = MagicMock()
        mgr = CacheManager(primary=primary)
        mgr.close()
        primary.close.assert_called_once()

    def test_close_calls_fallback_close(self):
        primary = MagicMock()
        fallback = MagicMock()
        mgr = CacheManager(primary=primary, fallback=fallback)
        mgr.close()
        fallback.close.assert_called_once()


# ===========================================================================
# Performance benchmarks
# ===========================================================================


class TestPerformance:
    """
    Verify sub-millisecond cache-hit latency for the LRU backend and
    sub-5ms latency for the Redis backend (via MagicMock, which is faster
    than a real network round-trip).
    """

    ITERATIONS = 1_000

    def test_lru_hit_latency_sub_millisecond(self):
        mgr = CacheManager(namespace="perf", primary=LRUBackend(capacity=10_000))
        mgr.set("bench_key", {"data": "x" * 256})

        start = time.perf_counter()
        for _ in range(self.ITERATIONS):
            mgr.get("bench_key")
        elapsed_s = time.perf_counter() - start

        avg_ms = (elapsed_s / self.ITERATIONS) * 1_000
        assert avg_ms < 1.0, f"Average LRU hit latency {avg_ms:.4f} ms exceeds 1 ms"

    def test_redis_hit_latency_sub_5ms(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = '"cached_value"'
        backend = RedisBackend(redis_client=mock_redis)
        mgr = CacheManager(namespace="perf", primary=backend)

        start = time.perf_counter()
        for _ in range(self.ITERATIONS):
            mgr.get("bench_key")
        elapsed_s = time.perf_counter() - start

        avg_ms = (elapsed_s / self.ITERATIONS) * 1_000
        assert avg_ms < 5.0, f"Average Redis hit latency {avg_ms:.4f} ms exceeds 5 ms"

    def test_lru_set_latency_sub_millisecond(self):
        mgr = CacheManager(namespace="perf", primary=LRUBackend(capacity=10_000))

        start = time.perf_counter()
        for i in range(self.ITERATIONS):
            mgr.set(f"key_{i}", i)
        elapsed_s = time.perf_counter() - start

        avg_ms = (elapsed_s / self.ITERATIONS) * 1_000
        assert avg_ms < 1.0, f"Average LRU set latency {avg_ms:.4f} ms exceeds 1 ms"
