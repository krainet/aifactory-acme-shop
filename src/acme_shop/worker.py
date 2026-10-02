"""RQ worker entry point: `acme-worker` processes the order queue."""

from __future__ import annotations

import logging

from redis import Redis
from rq import Worker

from acme_shop.config import Settings
from acme_shop.jobs import make_queue


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    settings = Settings.from_env()
    connection = Redis.from_url(settings.redis_url)
    worker = Worker([make_queue(settings, connection)], connection=connection)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
