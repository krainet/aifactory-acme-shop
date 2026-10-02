from __future__ import annotations

import fakeredis
import pytest
from acme_shop import jobs
from acme_shop.config import Settings
from acme_shop.postgres import PostgresStore
from fakes import InMemoryStore
from rq import Queue


def test_confirm_order_confirms_a_pending_order_once(store: InMemoryStore) -> None:
    store.add_item("c", 1, 1)
    order = store.create_order("c")
    assert order is not None
    assert jobs.confirm_order(order.id, store=store) is True
    assert jobs.confirm_order(order.id, store=store) is False
    assert jobs.confirm_order(999, store=store) is False


def test_confirm_order_defaults_to_the_configured_store(
    monkeypatch: pytest.MonkeyPatch, store: InMemoryStore
) -> None:
    monkeypatch.setattr(jobs, "default_store", lambda: store)
    assert jobs.confirm_order(1) is False


def test_default_store_reads_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACME_DATABASE_URL", "postgresql://u:p@db:5432/x")
    assert isinstance(jobs.default_store(), PostgresStore)


def test_rq_queue_enqueues_the_job_by_dotted_path(redis: fakeredis.FakeRedis) -> None:
    queue = jobs.make_queue(Settings(queue_name="orders-test"), redis)
    jobs.RqOrderQueue(queue).enqueue_confirmation(7)
    [job] = Queue("orders-test", connection=redis).get_jobs()
    assert job.func_name == jobs.CONFIRM_ORDER_JOB
    assert job.args == (7,)
