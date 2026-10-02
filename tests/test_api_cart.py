from __future__ import annotations

from fakes import InMemoryStore, RecordingQueue
from fastapi.testclient import TestClient

CART = "cart-1"


def add(client: TestClient, product_id: int, quantity: int = 1) -> int:
    response = client.post(
        f"/cart/{CART}/items", json={"product_id": product_id, "quantity": quantity}
    )
    return response.status_code


def test_empty_cart(client: TestClient) -> None:
    response = client.get(f"/cart/{CART}")
    assert response.json() == {"cart_id": CART, "lines": [], "total_cents": 0}


def test_adding_an_item_invalidates_the_cached_cart(client: TestClient) -> None:
    client.get(f"/cart/{CART}")
    assert client.get(f"/cart/{CART}").headers["X-Cache"] == "hit"
    assert add(client, 1, 2) == 201
    cart = client.get(f"/cart/{CART}")
    assert cart.headers["X-Cache"] == "hit"  # the POST response already reloaded it
    assert cart.json()["lines"][0]["quantity"] == 2
    assert cart.json()["total_cents"] == 2 * 12999


def test_quantities_accumulate_and_are_capped(client: TestClient) -> None:
    assert add(client, 3, 60) == 201
    assert add(client, 3, 60) == 201
    assert client.get(f"/cart/{CART}").json()["lines"][0]["quantity"] == 99


def test_add_rejects_bad_input(client: TestClient) -> None:
    assert add(client, 9999) == 404
    assert add(client, 1, 0) == 422
    assert add(client, 1, 100) == 422
    assert client.post("/cart/bad id!/items", json={"product_id": 1}).status_code == 422
    assert client.post(f"/cart/{CART}/items", json={"product_id": 1, "x": 1}).status_code == 422


def test_remove_item_and_missing_item(client: TestClient) -> None:
    add(client, 1)
    client.get(f"/cart/{CART}")
    assert client.delete(f"/cart/{CART}/items/1").status_code == 204
    after = client.get(f"/cart/{CART}")
    assert after.headers["X-Cache"] == "miss"
    assert after.json()["lines"] == []
    assert client.delete(f"/cart/{CART}/items/1").status_code == 404


def test_checkout_creates_a_pending_order_and_enqueues_confirmation(
    client: TestClient, queue: RecordingQueue, store: InMemoryStore
) -> None:
    add(client, 5, 3)
    response = client.post(f"/cart/{CART}/checkout")
    assert response.status_code == 202
    order = response.json()
    assert order["status"] == "pending"
    assert order["total_cents"] == 3 * 799
    assert queue.enqueued == [order["id"]]
    assert client.get(f"/cart/{CART}").json()["lines"] == []
    assert client.get(f"/orders/{order['id']}").json()["status"] == "pending"
    store.confirm_order(order["id"])
    assert client.get(f"/orders/{order['id']}").json()["status"] == "confirmed"


def test_checkout_of_an_empty_cart_conflicts(client: TestClient, queue: RecordingQueue) -> None:
    assert client.post(f"/cart/{CART}/checkout").status_code == 409
    assert queue.enqueued == []


def test_unknown_order(client: TestClient) -> None:
    assert client.get("/orders/42").status_code == 404
