"""Persistence port. The web app and the worker depend on this protocol, not on PostgreSQL."""

from __future__ import annotations

from typing import Protocol

from acme_shop.models import Cart, Order, Product


class Store(Protocol):
    def ping(self) -> None: ...

    def list_products(self) -> list[Product]: ...

    def get_product(self, product_id: int) -> Product | None: ...

    def get_cart(self, cart_id: str) -> Cart: ...

    def add_item(self, cart_id: str, product_id: int, quantity: int) -> None: ...

    def remove_item(self, cart_id: str, product_id: int) -> bool:
        """Return False when the cart had no such line."""
        ...

    def create_order(self, cart_id: str) -> Order | None:
        """Turn the cart into a pending order and empty the cart; None when the cart is empty."""
        ...

    def get_order(self, order_id: int) -> Order | None: ...

    def confirm_order(self, order_id: int) -> bool:
        """Mark a pending order confirmed; False when it does not exist or is not pending."""
        ...
