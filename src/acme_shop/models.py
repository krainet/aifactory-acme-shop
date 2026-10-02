"""API and domain models."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_QUANTITY = 99
CART_ID_PATTERN = r"^[A-Za-z0-9-]{1,64}$"
Quantity = Annotated[int, Field(ge=1, le=MAX_QUANTITY)]
OrderStatus = Literal["pending", "confirmed"]


class Product(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    sku: str
    name: str
    description: str
    price_cents: int


class CartLine(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_id: int
    name: str
    quantity: int
    unit_price_cents: int

    @property
    def subtotal_cents(self) -> int:
        return self.quantity * self.unit_price_cents


class Cart(BaseModel):
    model_config = ConfigDict(frozen=True)

    cart_id: str
    lines: tuple[CartLine, ...] = ()

    @property
    def total_cents(self) -> int:
        return sum(line.subtotal_cents for line in self.lines)

    def to_public(self) -> dict[str, object]:
        lines = [line.model_dump() | {"subtotal_cents": line.subtotal_cents} for line in self.lines]
        return {"cart_id": self.cart_id, "lines": lines, "total_cents": self.total_cents}


class AddItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int
    quantity: Quantity = 1


class Order(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    cart_id: str
    total_cents: int
    status: OrderStatus
    created_at: datetime
    confirmed_at: datetime | None = None
