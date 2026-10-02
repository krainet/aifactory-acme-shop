"""Use cases: the only place that knows which cache keys a write must invalidate."""

from __future__ import annotations

from typing import Any, Protocol

from acme_shop.cache import Cache, CacheStatus
from acme_shop.models import Order
from acme_shop.store import Store

PRODUCTS_KEY = "products"


class UnknownProductError(LookupError):
    pass


class EmptyCartError(ValueError):
    pass


class OrderQueue(Protocol):
    def enqueue_confirmation(self, order_id: int) -> None: ...


def product_key(product_id: int) -> str:
    return f"product:{product_id}"


def cart_key(cart_id: str) -> str:
    return f"cart:{cart_id}"


class Shop:
    def __init__(self, store: Store, cache: Cache, queue: OrderQueue) -> None:
        self.store = store
        self.cache = cache
        self.queue = queue

    def list_products(self) -> tuple[list[dict[str, Any]], CacheStatus]:
        def load() -> list[dict[str, Any]]:
            return [product.model_dump() for product in self.store.list_products()]

        return self.cache.get_or_load(PRODUCTS_KEY, load)

    def get_product(self, product_id: int) -> tuple[dict[str, Any] | None, CacheStatus]:
        def load() -> dict[str, Any] | None:
            product = self.store.get_product(product_id)
            return product.model_dump() if product else None

        return self.cache.get_or_load(product_key(product_id), load)

    def get_cart(self, cart_id: str) -> tuple[dict[str, Any], CacheStatus]:
        return self.cache.get_or_load(
            cart_key(cart_id), lambda: self.store.get_cart(cart_id).to_public()
        )

    def add_item(self, cart_id: str, product_id: int, quantity: int) -> None:
        if self.store.get_product(product_id) is None:
            raise UnknownProductError(product_id)
        self.store.add_item(cart_id, product_id, quantity)
        self.cache.invalidate(cart_key(cart_id))

    def remove_item(self, cart_id: str, product_id: int) -> bool:
        removed = self.store.remove_item(cart_id, product_id)
        self.cache.invalidate(cart_key(cart_id))
        return removed

    def checkout(self, cart_id: str) -> Order:
        order = self.store.create_order(cart_id)
        if order is None:
            raise EmptyCartError(cart_id)
        self.cache.invalidate(cart_key(cart_id))
        self.queue.enqueue_confirmation(order.id)
        return order
