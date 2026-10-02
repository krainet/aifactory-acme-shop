"""Shared fixtures: in-memory store, fakeredis-backed cache, recording queue, HTTP client."""

from __future__ import annotations

from collections.abc import Iterator

import fakeredis
import pytest
from acme_shop.api import create_app
from acme_shop.cache import Cache
from acme_shop.service import Shop
from fakes import InMemoryStore, RecordingQueue, seeded_store
from fastapi.testclient import TestClient


@pytest.fixture
def redis() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis()


@pytest.fixture
def store() -> InMemoryStore:
    return seeded_store()


@pytest.fixture
def queue() -> RecordingQueue:
    return RecordingQueue()


@pytest.fixture
def shop(store: InMemoryStore, redis: fakeredis.FakeRedis, queue: RecordingQueue) -> Shop:
    return Shop(store=store, cache=Cache(redis, ttl_seconds=60), queue=queue)


@pytest.fixture
def client(shop: Shop) -> Iterator[TestClient]:
    with TestClient(create_app(shop)) as test_client:
        yield test_client
