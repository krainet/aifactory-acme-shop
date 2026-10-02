"""Runtime configuration, read once from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_DATABASE_URL = "postgresql://acme:acme@localhost:5432/acme_shop"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"
DEFAULT_CACHE_TTL_SECONDS = 300
DEFAULT_QUEUE_NAME = "orders"


@dataclass(frozen=True)
class Settings:
    database_url: str = DEFAULT_DATABASE_URL
    redis_url: str = DEFAULT_REDIS_URL
    cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS
    queue_name: str = DEFAULT_QUEUE_NAME

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        source = os.environ if env is None else env
        ttl = int(source.get("ACME_CACHE_TTL_SECONDS", DEFAULT_CACHE_TTL_SECONDS))
        if ttl <= 0:
            raise ValueError("ACME_CACHE_TTL_SECONDS must be a positive integer")
        return cls(
            database_url=source.get("ACME_DATABASE_URL", DEFAULT_DATABASE_URL),
            redis_url=source.get("ACME_REDIS_URL", DEFAULT_REDIS_URL),
            cache_ttl_seconds=ttl,
            queue_name=source.get("ACME_QUEUE_NAME", DEFAULT_QUEUE_NAME),
        )
