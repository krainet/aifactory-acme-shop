"""Apply the schema and upsert the seed catalog: `acme-seed` (idempotent)."""

from __future__ import annotations

import logging
from importlib.resources import files

import psycopg

from acme_shop.catalog import CATALOG
from acme_shop.config import Settings

log = logging.getLogger(__name__)

UPSERT_PRODUCT = (
    "INSERT INTO products (sku, name, description, price_cents) VALUES (%s, %s, %s, %s)"
    " ON CONFLICT (sku) DO UPDATE SET name = EXCLUDED.name,"
    " description = EXCLUDED.description, price_cents = EXCLUDED.price_cents"
)


def schema_sql() -> str:
    return files("acme_shop").joinpath("sql/schema.sql").read_text(encoding="utf-8")


def seed(database_url: str) -> int:
    """Return the number of catalog products after seeding."""
    with psycopg.connect(database_url) as conn:
        conn.execute(schema_sql())
        with conn.cursor() as cur:
            cur.executemany(UPSERT_PRODUCT, [tuple(product) for product in CATALOG])
            cur.execute("SELECT count(*) FROM products")
            row = cur.fetchone()
    return int(row[0]) if row else 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    count = seed(Settings.from_env().database_url)
    log.info("seed complete: %d products", count)


if __name__ == "__main__":
    main()
