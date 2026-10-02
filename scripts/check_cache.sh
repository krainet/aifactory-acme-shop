#!/usr/bin/env bash
# Proves the Redis cache works: a fresh key is a miss, the repeat is a hit, and the shared
# counters at /cache/stats move accordingly. Exits non-zero on failure.
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

CART="$(new_cart_id)"

stats() {
  request GET /cache/stats
  expect_status 200
  json "d['hits'], d['misses']"
}

# A never-seen cart id has no cache entry, so its first read must miss and the second must hit.
read -r hits0 misses0 < <(stats | tr -d '(),')

request GET "/cart/$CART"
expect_status 200
[[ "$(cache_header)" == miss ]] || fail "first read of cart $CART: expected X-Cache miss, got '$(cache_header)'"
pass "first read is a miss"

request GET "/cart/$CART"
expect_status 200
[[ "$(cache_header)" == hit ]] || fail "second read of cart $CART: expected X-Cache hit, got '$(cache_header)'"
pass "second read is a hit"

read -r hits1 misses1 < <(stats | tr -d '(),')
(( misses1 >= misses0 + 1 )) || fail "miss counter did not increase ($misses0 -> $misses1)"
(( hits1 >= hits0 + 1 )) || fail "hit counter did not increase ($hits0 -> $hits1)"
pass "counters moved: hits $hits0 -> $hits1, misses $misses0 -> $misses1"

request GET /metrics
expect_status 200
grep -q '^acme_cache_hit_ratio ' <<< "$BODY" || fail "/metrics has no acme_cache_hit_ratio"
pass "metrics: $(grep '^acme_cache_hit_ratio ' <<< "$BODY")"

echo "check_cache: PASS ($BASE_URL)"
