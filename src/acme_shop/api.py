"""HTTP routes. Every cached read reports `X-Cache: hit|miss` so clients can observe the cache."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from acme_shop import __version__
from acme_shop.metrics import render_metrics
from acme_shop.models import CART_ID_PATTERN, AddItem
from acme_shop.service import EmptyCartError, Shop, UnknownProductError

router = APIRouter()
CartPath = Annotated[str, Path(pattern=CART_ID_PATTERN)]
log = logging.getLogger(__name__)


def get_shop(request: Request) -> Shop:
    shop: Shop = request.app.state.shop
    return shop


ShopDep = Annotated[Shop, Depends(get_shop)]


def _cached(response: Response, payload: tuple[Any, str]) -> Any:
    value, status = payload
    response.headers["X-Cache"] = status
    return value


@router.get("/healthz")
def healthz(shop: ShopDep) -> JSONResponse:
    """Ready only when both PostgreSQL and Redis answer; the compose healthcheck polls this."""
    try:
        shop.store.ping()
        shop.cache.ping()
    except Exception as exc:  # any dependency failure means "not ready", never a 500
        log.warning("health check failed: %s", type(exc).__name__)
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return JSONResponse({"status": "ok", "version": __version__})


@router.get("/products")
def list_products(shop: ShopDep, response: Response) -> Any:
    return _cached(response, shop.list_products())


@router.get("/products/{product_id}")
def get_product(product_id: int, shop: ShopDep, response: Response) -> Any:
    product = _cached(response, shop.get_product(product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    return product


@router.get("/cart/{cart_id}")
def get_cart(cart_id: CartPath, shop: ShopDep, response: Response) -> Any:
    return _cached(response, shop.get_cart(cart_id))


@router.post("/cart/{cart_id}/items", status_code=201)
def add_item(cart_id: CartPath, item: AddItem, shop: ShopDep) -> dict[str, Any]:
    try:
        shop.add_item(cart_id, item.product_id, item.quantity)
    except UnknownProductError:
        raise HTTPException(status_code=404, detail="product not found") from None
    cart, _ = shop.get_cart(cart_id)
    return cart


@router.delete("/cart/{cart_id}/items/{product_id}", status_code=204)
def remove_item(cart_id: CartPath, product_id: int, shop: ShopDep) -> Response:
    if not shop.remove_item(cart_id, product_id):
        raise HTTPException(status_code=404, detail="item not in cart")
    return Response(status_code=204)


@router.post("/cart/{cart_id}/checkout", status_code=202)
def checkout(cart_id: CartPath, shop: ShopDep) -> dict[str, Any]:
    try:
        order = shop.checkout(cart_id)
    except EmptyCartError:
        raise HTTPException(status_code=409, detail="cart is empty") from None
    return order.model_dump(mode="json")


@router.get("/orders/{order_id}")
def get_order(order_id: int, shop: ShopDep) -> dict[str, Any]:
    order = shop.store.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order.model_dump(mode="json")


@router.get("/cache/stats")
def cache_stats(shop: ShopDep) -> dict[str, float | int]:
    return shop.cache.stats().to_public()


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(shop: ShopDep) -> str:
    return render_metrics(shop.cache.stats())


def create_app(shop: Shop) -> FastAPI:
    app = FastAPI(title="Acme Shop", version=__version__)
    app.state.shop = shop
    app.include_router(router)
    return app
