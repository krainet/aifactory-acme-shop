"""Background jobs executed by the RQ worker."""

from __future__ import annotations

import logging

from redis import Redis
from rq import Queue

from acme_shop.config import Settings
from acme_shop.postgres import PostgresStore
from acme_shop.store import Store

CONFIRM_ORDER_JOB = "acme_shop.jobs.confirm_order"
log = logging.getLogger(__name__)


class RqOrderQueue:
    """OrderQueue adapter: enqueues jobs by dotted path so the web never imports the worker."""

    def __init__(self, queue: Queue) -> None:
        self._queue = queue

    def enqueue_confirmation(self, order_id: int) -> None:
        self._queue.enqueue(CONFIRM_ORDER_JOB, order_id, job_timeout=60)


def make_queue(settings: Settings, connection: Redis) -> Queue:
    return Queue(settings.queue_name, connection=connection)


def default_store() -> Store:
    return PostgresStore(Settings.from_env().database_url)


def confirm_order(order_id: int, store: Store | None = None) -> bool:
    """Confirm a pending order (stands in for payment capture and the confirmation e-mail)."""
    target = store if store is not None else default_store()
    confirmed = target.confirm_order(order_id)
    if confirmed:
        log.info("order %s confirmed", order_id)
    else:
        log.warning("order %s not confirmed: missing or not pending", order_id)
    return confirmed
