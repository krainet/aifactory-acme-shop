"""ASGI entry point: `uvicorn acme_shop.main:app`."""

from __future__ import annotations

from fastapi import FastAPI
from redis import Redis

from acme_shop.api import create_app
from acme_shop.cache import Cache
from acme_shop.config import Settings
from acme_shop.jobs import RqOrderQueue, make_queue
from acme_shop.postgres import PostgresStore
from acme_shop.service import Shop


def build_app(settings: Settings) -> FastAPI:
    redis = Redis.from_url(settings.redis_url)
    shop = Shop(
        store=PostgresStore(settings.database_url),
        cache=Cache(redis, settings.cache_ttl_seconds),
        queue=RqOrderQueue(make_queue(settings, redis)),
    )
    return create_app(shop)


app = build_app(Settings.from_env())
