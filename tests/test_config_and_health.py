from __future__ import annotations

import fakeredis
import pytest
from acme_shop import healthcheck
from acme_shop.catalog import CATALOG
from acme_shop.config import DEFAULT_QUEUE_NAME, Settings
from acme_shop.jobs import make_queue
from acme_shop.seed import schema_sql
from rq import Worker


def test_settings_defaults_and_overrides() -> None:
    assert Settings.from_env({}) == Settings()
    custom = Settings.from_env({"ACME_CACHE_TTL_SECONDS": "5", "ACME_QUEUE_NAME": "q"})
    assert (custom.cache_ttl_seconds, custom.queue_name) == (5, "q")


@pytest.mark.parametrize("ttl", ["0", "-1", "soon"])
def test_settings_reject_invalid_ttl(ttl: str) -> None:
    with pytest.raises(ValueError):
        Settings.from_env({"ACME_CACHE_TTL_SECONDS": ttl})


def test_worker_probe_needs_a_registered_worker(redis: fakeredis.FakeRedis) -> None:
    settings = Settings()
    assert healthcheck.worker_is_healthy(settings, redis) is False
    worker = Worker([make_queue(settings, redis)], connection=redis)
    worker.register_birth()
    assert healthcheck.worker_is_healthy(settings, redis) is True


def test_web_probe_fails_when_nothing_listens() -> None:
    assert healthcheck.web_is_healthy("http://127.0.0.1:9/healthz") is False


def test_healthcheck_cli_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    assert healthcheck.main([]) == 2
    assert healthcheck.main(["db"]) == 2
    monkeypatch.setattr(healthcheck, "web_is_healthy", lambda: True)
    assert healthcheck.main(["web"]) == 0


def test_seed_data_is_consistent() -> None:
    skus = [product.sku for product in CATALOG]
    assert len(skus) == len(set(skus))
    assert all(product.price_cents > 0 for product in CATALOG)
    for table in ("products", "cart_items", "orders", "order_items"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in schema_sql()
    assert DEFAULT_QUEUE_NAME == "orders"
