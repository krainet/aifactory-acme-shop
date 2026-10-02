# Shared helpers for the validation scripts. Requires bash, curl and python3.
# ACME_BASE_URL overrides the target; otherwise http://localhost:${ACME_WEB_PORT:-18080}.
set -euo pipefail

BASE_URL="${ACME_BASE_URL:-http://localhost:${ACME_WEB_PORT:-18080}}"
HTTP_TIMEOUT="${ACME_HTTP_TIMEOUT:-10}"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

pass() {
  echo "ok - $*"
}

# request METHOD PATH [JSON_BODY]: sets STATUS, BODY and HEADERS (lower-cased header lines).
request() {
  local method="$1" path="$2" body="${3:-}" header_file body_file
  header_file="$(mktemp)"
  body_file="$(mktemp)"
  local args=(-sS -X "$method" -o "$body_file" -D "$header_file" -w '%{http_code}'
              --max-time "$HTTP_TIMEOUT")
  if [[ -n "$body" ]]; then
    args+=(-H 'Content-Type: application/json' --data "$body")
  fi
  STATUS="$(curl "${args[@]}" "$BASE_URL$path")" || fail "$method $path: connection failed"
  BODY="$(cat "$body_file")"
  HEADERS="$(tr '[:upper:]' '[:lower:]' < "$header_file" | tr -d '\r')"
  rm -f "$header_file" "$body_file"
}

# expect_status CODE: the last request must have returned CODE.
expect_status() {
  [[ "$STATUS" == "$1" ]] || fail "expected HTTP $1, got $STATUS: $BODY"
}

# json EXPR: evaluate a Python expression over the last body bound to `d`.
json() {
  printf '%s' "$BODY" | python3 -c "import json, sys; d = json.load(sys.stdin); print($1)"
}

# cache_header: value of X-Cache in the last response (empty when absent).
cache_header() {
  printf '%s\n' "$HEADERS" | sed -n 's/^x-cache: *//p' | head -n 1
}

new_cart_id() {
  printf 'check-%s-%s' "$(date +%s)" "$RANDOM$RANDOM"
}
