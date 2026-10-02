"""Read-through JSON cache on Redis with shared hit/miss counters.

The counters live in Redis (not in process memory) so every web process reports the same numbers
and `/cache/stats` measures the real hit ratio of the deployment.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from redis import Redis

KEY_PREFIX = "acme:cache:"
HITS_KEY = "acme:stats:cache_hits"
MISSES_KEY = "acme:stats:cache_misses"
CacheStatus = Literal["hit", "miss"]


@dataclass(frozen=True)
class CacheStats:
    hits: int
    misses: int

    @property
    def hit_ratio(self) -> float:
        lookups = self.hits + self.misses
        return round(self.hits / lookups, 4) if lookups else 0.0

    def to_public(self) -> dict[str, float | int]:
        return {"hits": self.hits, "misses": self.misses, "hit_ratio": self.hit_ratio}


class Cache:
    def __init__(self, client: Redis, ttl_seconds: int) -> None:
        self._redis = client
        self._ttl = ttl_seconds

    def get_or_load(self, key: str, loader: Callable[[], Any]) -> tuple[Any, CacheStatus]:
        """Return the cached JSON value for `key`, loading and storing it on a miss."""
        raw = self._redis.get(KEY_PREFIX + key)
        if raw is not None:
            self._redis.incr(HITS_KEY)
            return json.loads(raw), "hit"
        self._redis.incr(MISSES_KEY)
        value = loader()
        if value is not None:
            self._redis.set(KEY_PREFIX + key, json.dumps(value), ex=self._ttl)
        return value, "miss"

    def invalidate(self, *keys: str) -> None:
        if keys:
            self._redis.delete(*(KEY_PREFIX + key for key in keys))

    def stats(self) -> CacheStats:
        hits, misses = self._redis.mget(HITS_KEY, MISSES_KEY)
        return CacheStats(hits=int(hits or 0), misses=int(misses or 0))

    def ping(self) -> None:
        self._redis.ping()
