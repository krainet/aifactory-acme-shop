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

## From a fixture to a real pull request

The scenario target `github` replays a fixture as a real pull request against the published
mirror (`<owner>/aifactory-acme-shop`, see `../../README.md`):

1. **Base.** Clone the mirror; its `main` equals this directory at the publishing commit, which is
   the tree `diff.patch` applies to.
2. **Branch.** Create a per-run branch, `scn/<run-id>/<fixture>` (for example
   `scn/20261004-0317/0001`), so concurrent runs never share a branch. The fixture's `head.ref` is
   documentation, not the branch name used.
3. **Patch.** `git apply fixtures/prs/<fixture>/diff.patch`, commit, push the branch.
4. **Pull request.** `gh pr create --base main --head <branch>` with `title` and `body` from
   `pr.yaml` (`--draft` when `draft: true`).
5. **Labels and comments.** The review trigger under test is injected with
   `gh pr edit --add-label aifactory:review` or `gh pr comment` (mentioning the App); the
   `aifactory:review` label exists in the mirror because the publisher creates it. Labels listed in
   `pr.yaml` are added the same way.
6. **Assertion.** The scenario waits for a review by the App's bot user (`<app-slug>[bot]`) and
   matches its findings against `expected.yaml`.
7. **Teardown.** Close the pull request and delete the branch; the mirror's `main` is never written
   by scenarios.

Real pull requests have new numbers and SHAs, so `number`, `base.sha` and `head.sha` in `pr.yaml`
and `event.json` only describe the frozen replay used by the offline (doubles) target.

## Reproducing `0001-search-and-quantity` against the running stack

Apply `diff.patch` to a copy of the tree, `docker compose up -d --build --wait`, then:

| Finding | Request | Observed |
|---------|---------|----------|
| SQL injection | `GET /products/search?q=zzz' OR 1=1 --` (URL-encoded) | every product is returned; `q=it's` answers 500 |
| Stale cart cache | add product 1, read the cart, `PUT /cart/{id}/items/1 {"quantity": 5}`, read the cart again | `X-Cache: hit` with `quantity: 1` |
| Missing cart line | `PUT /cart/{id}/items/2 {"quantity": 5}` for a line not in the cart | 500 instead of 404 |
