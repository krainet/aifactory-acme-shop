"""Container health probes: `acme-healthcheck web|worker` exits 0 when healthy, 1 otherwise."""

from __future__ import annotations

import sys
import urllib.request

from redis import Redis
from redis.exceptions import RedisError
from rq import Worker

from acme_shop.config import Settings
from acme_shop.jobs import make_queue

WEB_HEALTH_URL = "http://127.0.0.1:8080/healthz"
PROBE_TIMEOUT_SECONDS = 3


def web_is_healthy(url: str = WEB_HEALTH_URL) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=PROBE_TIMEOUT_SECONDS) as response:  # noqa: S310
            return bool(response.status == 200)
    except OSError:
        return False


def worker_is_healthy(settings: Settings, connection: Redis | None = None) -> bool:
    """Healthy while a worker is registered for the queue; the key expires without heartbeats."""
    client = connection or Redis.from_url(settings.redis_url, socket_timeout=PROBE_TIMEOUT_SECONDS)
    try:
        return bool(Worker.all(connection=client, queue=make_queue(settings, client)))
    except (OSError, RedisError):
        return False


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    probes = {"web": web_is_healthy, "worker": lambda: worker_is_healthy(Settings.from_env())}
    if len(args) != 1 or args[0] not in probes:
        print("usage: acme-healthcheck web|worker", file=sys.stderr)
        return 2
    return 0 if probes[args[0]]() else 1


if __name__ == "__main__":
    sys.exit(main())
