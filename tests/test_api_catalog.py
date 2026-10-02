from __future__ import annotations

from fakes import InMemoryStore
from fastapi.testclient import TestClient


def test_healthz_reports_ok(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_healthz_is_unavailable_when_the_database_is_down(
    client: TestClient, store: InMemoryStore
) -> None:
    store.healthy = False
    response = client.get("/healthz")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_product_list_is_served_from_cache_on_the_second_request(
    client: TestClient, store: InMemoryStore
) -> None:
    first = client.get("/products")
    second = client.get("/products")
    assert first.headers["X-Cache"] == "miss"
    assert second.headers["X-Cache"] == "hit"
    assert first.json() == second.json()
    assert len(first.json()) == len(store.products)
    assert store.reads == 1


def test_product_detail_and_missing_product(client: TestClient) -> None:
    detail = client.get("/products/1")
    assert detail.status_code == 200
    assert detail.json()["sku"] == "ACME-ANV-001"
    assert client.get("/products/9999").status_code == 404
    assert client.get("/products/not-a-number").status_code == 422


def test_cache_stats_and_metrics_report_the_counters(client: TestClient) -> None:
    client.get("/products/2")
    client.get("/products/2")
    assert client.get("/cache/stats").json() == {"hits": 1, "misses": 1, "hit_ratio": 0.5}
    metrics = client.get("/metrics")
    assert metrics.headers["content-type"].startswith("text/plain")
    assert "acme_cache_hits_total 1\n" in metrics.text
    assert "acme_cache_misses_total 1\n" in metrics.text
    assert "acme_cache_hit_ratio 0.5\n" in metrics.text
