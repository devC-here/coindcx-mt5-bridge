from __future__ import annotations
from decimal import Decimal
from typing import Any, Mapping
from .models import OrderRequest, OrderType, Side

class MT5OrderAdapter:
    """Convert common MT5 Python request dictionaries to CoinDCX orders.

    Map symbols explicitly because broker symbols and CoinDCX markets differ.
    """
    def __init__(self, symbol_map: Mapping[str, str]) -> None:
        self.symbol_map = {key.upper(): value for key, value in symbol_map.items()}
    def to_coindcx(self, request: Mapping[str, Any]) -> OrderRequest:
        symbol = str(request.get("symbol", "")).upper()
        market = self.symbol_map.get(symbol)
        if market is None: raise ValueError(f"No CoinDCX market mapping configured for {symbol!r}")
        action = request.get("type")
        side = Side.BUY if action in (0, "BUY", "buy") else Side.SELL if action in (1, "SELL", "sell") else None
        if side is None: raise ValueError("type must be MT5 BUY (0) or SELL (1)")
        if request.get("volume") is None: raise ValueError("MT5 request must include volume")
        quantity = Decimal(str(request["volume"]))
        price = request.get("price")
        order_type = OrderType.LIMIT if price not in (None, 0, "0", "0.0") else OrderType.MARKET
        return OrderRequest(market, side, order_type, quantity, price)
