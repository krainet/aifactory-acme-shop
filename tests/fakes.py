"""Test doubles: an in-memory Store and a queue that records enqueued confirmations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from acme_shop.catalog import CATALOG
from acme_shop.models import MAX_QUANTITY, Cart, CartLine, Order, Product


@dataclass
class InMemoryStore:
    products: dict[int, Product] = field(default_factory=dict)
    carts: dict[str, dict[int, int]] = field(default_factory=dict)
    orders: dict[int, Order] = field(default_factory=dict)
    reads: int = 0
    healthy: bool = True

    def ping(self) -> None:
        if not self.healthy:
            raise ConnectionError("database down")

    def list_products(self) -> list[Product]:
        self.reads += 1
        return [self.products[key] for key in sorted(self.products)]

    def get_product(self, product_id: int) -> Product | None:
        self.reads += 1
        return self.products.get(product_id)

    def get_cart(self, cart_id: str) -> Cart:
        self.reads += 1
        items = self.carts.get(cart_id, {})
        lines = tuple(
            CartLine(
                product_id=pid,
                name=self.products[pid].name,
                quantity=qty,
                unit_price_cents=self.products[pid].price_cents,
            )
            for pid, qty in sorted(items.items())
        )
        return Cart(cart_id=cart_id, lines=lines)

    def add_item(self, cart_id: str, product_id: int, quantity: int) -> None:
        items = self.carts.setdefault(cart_id, {})
        items[product_id] = min(items.get(product_id, 0) + quantity, MAX_QUANTITY)

    def remove_item(self, cart_id: str, product_id: int) -> bool:
        return self.carts.get(cart_id, {}).pop(product_id, None) is not None

    def create_order(self, cart_id: str) -> Order | None:
        cart = self.get_cart(cart_id)
        if not cart.lines:
            return None
        self.carts.pop(cart_id)
        order_id = len(self.orders) + 1
        order = Order(
            id=order_id,
            cart_id=cart_id,
            total_cents=cart.total_cents,
            status="pending",
            created_at=datetime.now(UTC),
        )
        self.orders[order_id] = order
        return order

    def get_order(self, order_id: int) -> Order | None:
        return self.orders.get(order_id)

    def confirm_order(self, order_id: int) -> bool:
        order = self.orders.get(order_id)
        if order is None or order.status != "pending":
            return False
        confirmed_at = datetime.now(UTC)
        self.orders[order_id] = order.model_copy(
            update={"status": "confirmed", "confirmed_at": confirmed_at}
        )
        return True


@dataclass
class RecordingQueue:
    enqueued: list[int] = field(default_factory=list)

    def enqueue_confirmation(self, order_id: int) -> None:
        self.enqueued.append(order_id)


def seeded_store() -> InMemoryStore:
    products = {
        index: Product(id=index, **item._asdict()) for index, item in enumerate(CATALOG, start=1)
    }
    return InMemoryStore(products=products)
