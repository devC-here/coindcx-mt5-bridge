"""CoinDCX MT5 Compatibility Bridge Library.

A clean, drop-in Python library emulating MetaTrader 5 (MT5).
Allows algorithmic trading strategies, indicators, and bots built for MT5
to plug directly into CoinDCX Spot & Futures with zero logic overhaul.

Usage:
    from coindcx_mt5 import mt5
    # or
    import coindcx_mt5 as mt5

    mt5.initialize()
    rates = mt5.copy_rates_from_pos("BTCUSD", mt5.TIMEFRAME_M15, 0, 50)
"""

from . import compat as mt5
from .compat import *

__all__ = [
    "mt5",
    # MT5 LifeCycle
    "initialize",
    "shutdown",
    "version",
    "last_error",
    # MT5 Market Data
    "copy_rates_from_pos",
    "copy_rates_range",
    "copy_rates_from",
    "symbol_info",
    "symbol_info_tick",
    "symbol_select",
    "symbols_total",
    "symbols_get",
    # MT5 Orders & Positions
    "order_send",
    "order_check",
    "positions_get",
    "positions_total",
    "orders_get",
    "orders_total",
    "account_info",
    # Configuration
    "set_live_trading",
    "is_live_trading",
    "set_symbol_map",
    "set_default_market",
    "normalize_symbol",
    # Constants
    "TIMEFRAME_M1",
    "TIMEFRAME_M2",
    "TIMEFRAME_M3",
    "TIMEFRAME_M4",
    "TIMEFRAME_M5",
    "TIMEFRAME_M6",
    "TIMEFRAME_M10",
    "TIMEFRAME_M12",
    "TIMEFRAME_M15",
    "TIMEFRAME_M20",
    "TIMEFRAME_M30",
    "TIMEFRAME_H1",
    "TIMEFRAME_H2",
    "TIMEFRAME_H3",
    "TIMEFRAME_H4",
    "TIMEFRAME_H6",
    "TIMEFRAME_H8",
    "TIMEFRAME_H12",
    "TIMEFRAME_D1",
    "TIMEFRAME_W1",
    "TIMEFRAME_MN1",
    "ORDER_TYPE_BUY",
    "ORDER_TYPE_SELL",
    "ORDER_TYPE_BUY_LIMIT",
    "ORDER_TYPE_SELL_LIMIT",
    "TRADE_ACTION_DEAL",
    "TRADE_ACTION_PENDING",
    "TRADE_RETCODE_DONE",
    "TRADE_RETCODE_ERROR",
    "POSITION_TYPE_BUY",
    "POSITION_TYPE_SELL",
    "SymbolInfo",
    "Tick",
    "AccountInfo",
    "TradePosition",
    "TradeOrder",
    "OrderSendResult",
    "OrderCheckResult",
]
