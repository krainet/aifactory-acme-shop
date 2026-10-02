"""PostgreSQL implementation of the Store port (psycopg 3, one connection per call)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from acme_shop.models import MAX_QUANTITY, Cart, CartLine, Order, Product


class PostgresStore:
    def __init__(self, database_url: str) -> None:
        self._url = database_url

    @contextmanager
    def _cursor(self) -> Iterator[psycopg.Cursor[dict[str, object]]]:
        with psycopg.connect(self._url, row_factory=dict_row) as conn, conn.cursor() as cur:
            yield cur

    def ping(self) -> None:
        with self._cursor() as cur:
            cur.execute("SELECT 1")

    def list_products(self) -> list[Product]:
        with self._cursor() as cur:
            cur.execute("SELECT id, sku, name, description, price_cents FROM products ORDER BY id")
            return [Product.model_validate(row) for row in cur.fetchall()]

    def get_product(self, product_id: int) -> Product | None:
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, sku, name, description, price_cents FROM products WHERE id = %s",
                (product_id,),
            )
            row = cur.fetchone()
        return Product.model_validate(row) if row else None

    def get_cart(self, cart_id: str) -> Cart:
        with self._cursor() as cur:
            cur.execute(
                "SELECT ci.product_id, p.name, ci.quantity, p.price_cents AS unit_price_cents"
                " FROM cart_items ci JOIN products p ON p.id = ci.product_id"
                " WHERE ci.cart_id = %s ORDER BY ci.product_id",
                (cart_id,),
            )
            lines = tuple(CartLine.model_validate(row) for row in cur.fetchall())
        return Cart(cart_id=cart_id, lines=lines)

    def add_item(self, cart_id: str, product_id: int, quantity: int) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (%s, %s, %s)"
                " ON CONFLICT (cart_id, product_id)"
                " DO UPDATE SET quantity = LEAST(cart_items.quantity + EXCLUDED.quantity, %s)",
                (cart_id, product_id, quantity, MAX_QUANTITY),
            )

    def remove_item(self, cart_id: str, product_id: int) -> bool:
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM cart_items WHERE cart_id = %s AND product_id = %s",
                (cart_id, product_id),
            )
            return cur.rowcount > 0

    def create_order(self, cart_id: str) -> Order | None:
        with self._cursor() as cur:
            cur.execute(
                "WITH lines AS ("
                "  DELETE FROM cart_items WHERE cart_id = %(cart)s RETURNING product_id, quantity"
                "), priced AS ("
                "  SELECT l.product_id, l.quantity, p.price_cents"
                "  FROM lines l JOIN products p ON p.id = l.product_id"
                "), new_order AS ("
                "  INSERT INTO orders (cart_id, total_cents, status)"
                "  SELECT %(cart)s, SUM(quantity * price_cents), 'pending' FROM priced"
                "  HAVING COUNT(*) > 0"
                "  RETURNING id, cart_id, total_cents, status, created_at, confirmed_at"
                "), items AS ("
                "  INSERT INTO order_items (order_id, product_id, quantity, price_cents)"
                "  SELECT o.id, pr.product_id, pr.quantity, pr.price_cents"
                "  FROM new_order o CROSS JOIN priced pr"
                ") SELECT id, cart_id, total_cents, status, created_at, confirmed_at"
                " FROM new_order",
                {"cart": cart_id},
            )
            row = cur.fetchone()
        return Order.model_validate(row) if row else None

    def get_order(self, order_id: int) -> Order | None:
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, cart_id, total_cents, status, created_at, confirmed_at"
                " FROM orders WHERE id = %s",
                (order_id,),
            )
            row = cur.fetchone()
        return Order.model_validate(row) if row else None

    def confirm_order(self, order_id: int) -> bool:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE orders SET status = 'confirmed', confirmed_at = now()"
                " WHERE id = %s AND status = 'pending'",
                (order_id,),
            )
            return cur.rowcount > 0
