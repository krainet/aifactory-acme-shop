# Pull request fixtures

Each directory is one pull request against this repository, frozen as files so tests can replay
it without a code host:

| File            | Content |
|-----------------|---------|
| `pr.yaml`       | title, body, author, base/head refs and SHAs, changed files, line counts |
| `diff.patch`    | `git diff <base>..<head>`, paths relative to the acme-shop root; applies cleanly to the current tree |
| `event.json`    | the GitHub `pull_request` webhook payload (`action: opened`) for this PR, trimmed to the documented fields consumers read |
| `expected.yaml` | findings a reviewer must report (path, HEAD line, anchor text, severity, keywords), non-findings, acceptance rule |

The payload shape follows the GitHub docs for the `pull_request` webhook event and the pull
request object ("Get a pull request"); API URLs (`url`, `*_url` on api hosts) are omitted.
The HEAD version of a file is obtained by applying `diff.patch` to a copy of the acme-shop tree.

| Fixture | What it changes | Expected findings |
|---------|-----------------|-------------------|
| `0001-search-and-quantity` | adds product search and a cart quantity update | SQL injection (critical), stale cart cache (high), 500 on a missing cart line (medium) |

## Reproducing `0001-search-and-quantity` against the running stack

Apply `diff.patch` to a copy of the tree, `docker compose up -d --build --wait`, then:

| Finding | Request | Observed |
|---------|---------|----------|
| SQL injection | `GET /products/search?q=zzz' OR 1=1 --` (URL-encoded) | every product is returned; `q=it's` answers 500 |
| Stale cart cache | add product 1, read the cart, `PUT /cart/{id}/items/1 {"quantity": 5}`, read the cart again | `X-Cache: hit` with `quantity: 1` |
| Missing cart line | `PUT /cart/{id}/items/2 {"quantity": 5}` for a line not in the cart | 500 instead of 404 |
