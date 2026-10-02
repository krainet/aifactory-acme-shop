"""Prometheus text exposition of the cache counters."""

from __future__ import annotations

from acme_shop.cache import CacheStats


def render_metrics(stats: CacheStats) -> str:
    lines = [
        "# HELP acme_cache_hits_total Cache lookups served from Redis.",
        "# TYPE acme_cache_hits_total counter",
        f"acme_cache_hits_total {stats.hits}",
        "# HELP acme_cache_misses_total Cache lookups that fell through to PostgreSQL.",
        "# TYPE acme_cache_misses_total counter",
        f"acme_cache_misses_total {stats.misses}",
        "# HELP acme_cache_hit_ratio Hits divided by lookups since the counters started.",
        "# TYPE acme_cache_hit_ratio gauge",
        f"acme_cache_hit_ratio {stats.hit_ratio}",
    ]
    return "\n".join(lines) + "\n"
