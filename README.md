# Acme Shop

A small storefront for the (fictional) Acme company: a product catalog, shopping carts and orders.
It is aifactory's reference customer application and test fixture: the stack adapter starts it
from `stack.yaml`, the review agent reviews pull requests against it, and the scenario suite
validates it end to end.

## Architecture

| Service  | What it is                                    | Port (container) |
|----------|-----------------------------------------------|------------------|
| `web`    | FastAPI app (`acme_shop.main:app`, uvicorn)   | 8080 (published on the host as `ACME_WEB_PORT`, default 18080) |
| `db`     | PostgreSQL 16 (`postgres:16.15-alpine`)        | 5432 (internal)  |
| `cache`  | Redis 7 (`redis:7.4.11-alpine`)                | 6379 (internal)  |
| `worker` | RQ worker confirming orders in the background | none             |

- Reads of the catalog, a product and a cart go through a read-through Redis cache. Every cached
  response carries `X-Cache: hit|miss`; shared counters are exposed at `/cache/stats` (JSON) and
  `/metrics` (Prometheus text: `acme_cache_hits_total`, `acme_cache_misses_total`,
  `acme_cache_hit_ratio`). Cart writes invalidate the cart entry.
- Checkout turns a cart into a `pending` order and enqueues `acme_shop.jobs.confirm_order`; the
  worker marks it `confirmed`.
- The web container applies the schema and seed catalog (`acme-seed`, idempotent) before serving.

## API

| Method | Path                                   | Notes |
|--------|----------------------------------------|-------|
| GET    | `/healthz`                             | 200 when PostgreSQL and Redis answer, else 503 |
| GET    | `/products`, `/products/{id}`          | cached |
| GET    | `/cart/{cart_id}`                      | cached; `cart_id` matches `[A-Za-z0-9-]{1,64}` |
| POST   | `/cart/{cart_id}/items`                | body `{"product_id": 1, "quantity": 2}` (1-99) |
| DELETE | `/cart/{cart_id}/items/{product_id}`   | 204, or 404 when the line is absent |
| POST   | `/cart/{cart_id}/checkout`             | 202 with the pending order; 409 on an empty cart |
| GET    | `/orders/{id}`                         | order status |
| GET    | `/cache/stats`, `/metrics`             | cache counters |

## Run it

```bash
docker compose up -d --build --wait     # all four services healthy
scripts/smoke.sh                        # end-to-end HTTP smoke (needs bash, curl, python3)
scripts/check_cache.sh                  # proves a cache miss, then a hit, via the counters
docker compose down -v
```

Both scripts target `ACME_BASE_URL` (default `http://localhost:${ACME_WEB_PORT:-18080}`) and exit
non-zero on failure.

## Develop

```bash
uv sync --locked
uv run pytest -q
```

The unit tests use an in-memory store and fakeredis; PostgreSQL paths are exercised by
`scripts/smoke.sh` against the running stack. `.github/workflows/ci.yaml` is this repository's
own pipeline (a fixture inside aifactory; it only runs when acme-shop is its own repository).

## Published template repository (a mirror)

aifactory publishes this directory as its own public GitHub repository,
`<owner>/aifactory-acme-shop` (the name comes from `AF_EXAMPLE_REPOSITORY`), marked as a
**template**, so the review agent works on a real repository with real pull requests:

- `scripts/publish_example_repo.sh` in aifactory splits the history of `examples/acme-shop`
  (`git subtree split`), creates the repository when it is missing, force-pushes the split to its
  `main`, marks it as a template and creates the `aifactory:review` label. The aifactory workflow
  `publish-example.yaml` runs it on every push to aifactory's `main` that touches
  `examples/acme-shop/**`.
- The published repository is a **mirror**: its `main` is rebuilt and force-pushed on every
  publish, so never develop in it. Change `examples/acme-shop` in aifactory and publish again.
- The scenario target `github` (`scripts/scenario.py --target github` in aifactory) opens real
  pull requests against the mirror from the fixtures in `fixtures/prs/` (one branch per fixture,
  `diff.patch` applied, then `gh pr create`), lets the installed GitHub App review them, and closes
  them and deletes their branches afterwards. See `fixtures/prs/README.md`.
- "Use this template" gives anyone a copy (public or private) to point their own aifactory at.

## Fixtures for aifactory

`fixtures/prs/` holds pull requests against this code base, each with the unified diff, the
GitHub-shaped `pull_request` event, and `expected.yaml` listing what a competent reviewer must
find. See `fixtures/prs/README.md`.
