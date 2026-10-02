#!/usr/bin/env bash
# End-to-end smoke test against a running web service: health, catalog, cart, checkout, and the
# worker confirming the order. Exits non-zero on the first failure.
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

CONFIRM_TIMEOUT_SECONDS="${ACME_CONFIRM_TIMEOUT:-30}"
CART="$(new_cart_id)"

request GET /healthz
expect_status 200
[[ "$(json 'd["status"]')" == ok ]] || fail "healthz status is not ok: $BODY"
pass "healthz"

request GET /products
expect_status 200
PRODUCT_ID="$(json 'd[0]["id"]')"
[[ "$(json 'len(d)')" -ge 1 ]] || fail "catalog is empty (seed did not run?)"
pass "catalog lists $(json 'len(d)') products"

request GET "/products/$PRODUCT_ID"
expect_status 200
pass "product $PRODUCT_ID detail ($(json 'd["sku"]'))"

request GET /products/999999
expect_status 404
pass "unknown product is 404"

request POST "/cart/$CART/items" "{\"product_id\": $PRODUCT_ID, \"quantity\": 2}"
expect_status 201
[[ "$(json 'd["lines"][0]["quantity"]')" == 2 ]] || fail "cart quantity is not 2: $BODY"
pass "added 2 x product $PRODUCT_ID to cart $CART"

request DELETE "/cart/$CART/items/$PRODUCT_ID"
expect_status 204
request GET "/cart/$CART"
[[ "$(json 'len(d["lines"])')" == 0 ]] || fail "cart not empty after remove: $BODY"
pass "removed item, cart is empty"

request POST "/cart/$CART/checkout"
expect_status 409
pass "checkout of an empty cart is rejected"

request POST "/cart/$CART/items" "{\"product_id\": $PRODUCT_ID, \"quantity\": 1}"
expect_status 201
request POST "/cart/$CART/checkout"
expect_status 202
ORDER_ID="$(json 'd["id"]')"
pass "checkout created order $ORDER_ID (pending)"

deadline=$((SECONDS + CONFIRM_TIMEOUT_SECONDS))
while :; do
  request GET "/orders/$ORDER_ID"
  expect_status 200
  [[ "$(json 'd["status"]')" == confirmed ]] && break
  (( SECONDS < deadline )) || fail "order $ORDER_ID not confirmed by the worker in ${CONFIRM_TIMEOUT_SECONDS}s"
  sleep 1
done
pass "worker confirmed order $ORDER_ID"
echo "smoke: PASS ($BASE_URL)"
