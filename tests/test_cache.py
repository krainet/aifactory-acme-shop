from __future__ import annotations

import fakeredis
from acme_shop.cache import Cache, CacheStats


def test_first_lookup_misses_and_second_hits(redis: fakeredis.FakeRedis) -> None:
    cache = Cache(redis, ttl_seconds=60)
    loads: list[int] = []

    def loader() -> dict[str, int]:
        loads.append(1)
        return {"value": 7}

    assert cache.get_or_load("k", loader) == ({"value": 7}, "miss")
    assert cache.get_or_load("k", loader) == ({"value": 7}, "hit")
    assert len(loads) == 1
    assert cache.stats() == CacheStats(hits=1, misses=1)


def test_none_is_not_cached(redis: fakeredis.FakeRedis) -> None:
    cache = Cache(redis, ttl_seconds=60)
    assert cache.get_or_load("absent", lambda: None) == (None, "miss")
    assert cache.get_or_load("absent", lambda: None) == (None, "miss")
    assert cache.stats().misses == 2


def test_values_expire_with_the_configured_ttl(redis: fakeredis.FakeRedis) -> None:
    Cache(redis, ttl_seconds=42).get_or_load("k", lambda: 1)
    assert 0 < redis.ttl("acme:cache:k") <= 42


def test_invalidate_forces_a_reload(redis: fakeredis.FakeRedis) -> None:
    cache = Cache(redis, ttl_seconds=60)
    cache.get_or_load("k", lambda: 1)
    cache.invalidate("k")
    cache.invalidate()
    assert cache.get_or_load("k", lambda: 2) == (2, "miss")


def test_hit_ratio_handles_zero_lookups() -> None:
    assert CacheStats(hits=0, misses=0).hit_ratio == 0.0
    assert CacheStats(hits=3, misses=1).to_public() == {"hits": 3, "misses": 1, "hit_ratio": 0.75}
