# Contributing

- **Run the app:** `docker compose up -d --build --wait` (serves on `http://localhost:18080`; stop with `docker compose down -v`).
- **Run the checks:** `uv sync --locked && uv run pytest -q`, then `scripts/smoke.sh` and `scripts/check_cache.sh` against the running stack.
- **Open issues:** use the Issues tab of this repository on GitHub.
