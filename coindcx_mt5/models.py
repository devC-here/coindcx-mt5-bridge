from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum

class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market_order"
    LIMIT = "limit_order"

def decimal_text(value: Decimal | str | int | float, field: str) -> str:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be a decimal number") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError(f"{field} must be greater than zero")
    return format(number, "f")

@dataclass(frozen=True)
class OrderRequest:
    market: str
    side: Side
    order_type: OrderType
    quantity: Decimal | str | int | float
    price: Decimal | str | int | float | None = None

    def __post_init__(self) -> None:
        if not self.market or not self.market.strip():
            raise ValueError("market is required")
        decimal_text(self.quantity, "quantity")
        if self.order_type is OrderType.LIMIT and self.price is None:
            raise ValueError("price is required for a limit order")
        if self.price is not None:
            decimal_text(self.price, "price")

    def payload(self, timestamp_ms: int) -> dict[str, object]:
        payload: dict[str, object] = {"side": self.side.value, "order_type": self.order_type.value,
            "market": self.market, "total_quantity": decimal_text(self.quantity, "quantity"), "timestamp": timestamp_ms}
        if self.order_type is OrderType.LIMIT:
            payload["price_per_unit"] = decimal_text(self.price, "price")
        return payload
