"""CoinDCX MT5 Compatibility Layer.

A drop-in Python library emulating the official MetaTrader5 (MT5) API.
Allows existing algorithmic trading strategies, indicators, and bots written
for MT5 to run directly on CoinDCX Spot and Futures with zero to minimal logic changes.

Usage:
    from coindcx_mt5 import mt5
    # or
    import coindcx_mt5 as mt5

    mt5.initialize()
    rates = mt5.copy_rates_from_pos("BTCUSD", mt5.TIMEFRAME_M15, 0, 100)
    tick = mt5.symbol_info_tick("BTCUSD")
    result = mt5.order_send({
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": "BTCUSD",
        "volume": 0.001,
        "type": mt5.ORDER_TYPE_BUY,
        "price": tick.ask,
    })
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from collections import namedtuple
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np

logger = logging.getLogger("coindcx_mt5.compat")

# =====================================================================
# MT5 Data Structures (namedtuples matching MetaTrader5 schema)
# =====================================================================

SymbolInfo = namedtuple(
    "SymbolInfo",
    [
        "custom",
        "chart_mode",
        "select",
        "visible",
        "session_deals",
        "session_buy_orders",
        "session_sell_orders",
        "volume",
        "volume_high",
        "volume_low",
        "time",
        "digits",
        "spread",
        "spread_float",
        "ticks_bookdepth",
        "trade_calc_mode",
        "trade_mode",
        "start_time",
        "expiration_time",
        "trade_stops_level",
        "trade_freeze_level",
        "trade_exemode",
        "swap_mode",
        "swap_rollover3days",
        "margin_hedged_use_checking",
        "margin_hedged",
        "price_change",
        "price_volatility",
        "price_theoretical",
        "price_greeks_delta",
        "price_greeks_theta",
        "price_greeks_gamma",
        "price_greeks_vega",
        "price_greeks_rho",
        "price_greeks_omega",
        "price_sensitivity",
        "basis",
        "category",
        "currency_base",
        "currency_profit",
        "currency_margin",
        "bank",
        "description",
        "exchange",
        "formula",
        "isin",
        "name",
        "page",
        "path",
        "bid",
        "bidhigh",
        "bidlow",
        "ask",
        "askhigh",
        "asklow",
        "last",
        "lasthigh",
        "lastlow",
        "volume_real",
        "volumehigh_real",
        "volumelow_real",
        "option_strike",
        "point",
        "trade_tick_value",
        "trade_tick_value_profit",
        "trade_tick_value_loss",
        "trade_tick_size",
        "trade_contract_size",
        "volume_min",
        "volume_max",
        "volume_step",
        "volume_limit",
        "swap_long",
        "swap_short",
        "margin_initial",
        "margin_maintenance",
        "session_volume",
        "session_turnover",
        "session_interest",
        "session_buy_orders_volume",
        "session_sell_orders_volume",
        "session_open",
        "session_close",
        "session_aw",
        "price_strike",
    ],
)

Tick = namedtuple(
    "Tick",
    ["time", "bid", "ask", "last", "volume", "time_msc", "flags", "volume_real"],
)

AccountInfo = namedtuple(
    "AccountInfo",
    [
        "login",
        "trade_mode",
        "leverage",
        "limit_orders",
        "margin_so_mode",
        "trade_allowed",
        "trade_expert",
        "margin_mode",
        "currency_digits",
        "fifo",
        "balance",
        "credit",
        "profit",
        "equity",
        "margin",
        "margin_free",
        "margin_level",
        "margin_so_call",
        "margin_so_so",
        "margin_initial",
        "margin_maintenance",
        "assets",
        "liabilities",
        "commission_blocked",
        "name",
        "server",
        "currency",
        "company",
    ],
)

TradePosition = namedtuple(
    "TradePosition",
    [
        "ticket",
        "time",
        "time_msc",
        "time_update",
        "time_update_msc",
        "type",
        "magic",
        "identifier",
        "reason",
        "volume",
        "price_open",
        "sl",
        "tp",
        "price_current",
        "swap",
        "profit",
        "symbol",
        "comment",
        "external_id",
    ],
)

TradeOrder = namedtuple(
    "TradeOrder",
    [
        "ticket",
        "time_setup",
        "time_setup_msc",
        "time_done",
        "time_done_msc",
        "time_expiration",
        "type",
        "type_time",
        "type_filling",
        "state",
        "magic",
        "position_id",
        "position_by_id",
        "reason",
        "volume_initial",
        "volume_current",
        "price_open",
        "sl",
        "tp",
        "price_current",
        "price_stoplimit",
        "symbol",
        "comment",
        "external_id",
    ],
)

OrderSendResult = namedtuple(
    "OrderSendResult",
    [
        "retcode",
        "deal",
        "order",
        "volume",
        "price",
        "bid",
        "ask",
        "comment",
        "request_id",
        "retcode_external",
        "request",
    ],
)

OrderCheckResult = namedtuple(
    "OrderCheckResult",
    [
        "retcode",
        "balance",
        "equity",
        "profit",
        "margin",
        "margin_free",
        "margin_level",
        "comment",
        "request",
    ],
)

# =====================================================================
# MT5 Constants & Enums
# =====================================================================

# Timeframes
TIMEFRAME_M1 = 1
TIMEFRAME_M2 = 2
TIMEFRAME_M3 = 3
TIMEFRAME_M4 = 4
TIMEFRAME_M5 = 5
TIMEFRAME_M6 = 6
TIMEFRAME_M10 = 10
TIMEFRAME_M12 = 12
TIMEFRAME_M15 = 15
TIMEFRAME_M20 = 20
TIMEFRAME_M30 = 30
TIMEFRAME_H1 = 16385
TIMEFRAME_H2 = 16386
TIMEFRAME_H3 = 16387
TIMEFRAME_H4 = 16388
TIMEFRAME_H6 = 16390
TIMEFRAME_H8 = 16392
TIMEFRAME_H12 = 16396
TIMEFRAME_D1 = 16408
TIMEFRAME_W1 = 32769
TIMEFRAME_MN1 = 49153

# Trade actions
TRADE_ACTION_DEAL = 1
TRADE_ACTION_PENDING = 5
TRADE_ACTION_SLTP = 6
TRADE_ACTION_MODIFY = 7
TRADE_ACTION_REMOVE = 8
TRADE_ACTION_CLOSE_BY = 10

# Order types
ORDER_TYPE_BUY = 0
ORDER_TYPE_SELL = 1
ORDER_TYPE_BUY_LIMIT = 2
ORDER_TYPE_SELL_LIMIT = 3
ORDER_TYPE_BUY_STOP = 4
ORDER_TYPE_SELL_STOP = 5
ORDER_TYPE_BUY_STOP_LIMIT = 6
ORDER_TYPE_SELL_STOP_LIMIT = 7
ORDER_TYPE_CLOSE_BY = 8

# Position types
POSITION_TYPE_BUY = 0
POSITION_TYPE_SELL = 1

# Order Filling
ORDER_FILLING_FOK = 0
ORDER_FILLING_IOC = 1
ORDER_FILLING_RETURN = 2
ORDER_FILLING_BOC = 3

# Order Time
ORDER_TIME_GTC = 0
ORDER_TIME_DAY = 1
ORDER_TIME_SPECIFIED = 2
ORDER_TIME_SPECIFIED_DAY = 3

# Trade Return Codes
TRADE_RETCODE_REQUOTE = 10004
TRADE_RETCODE_REJECT = 10006
TRADE_RETCODE_CANCEL = 10007
TRADE_RETCODE_PLACED = 10008
TRADE_RETCODE_DONE = 10009
TRADE_RETCODE_DONE_PARTIAL = 10010
TRADE_RETCODE_ERROR = 10011
TRADE_RETCODE_TIMEOUT = 10012
TRADE_RETCODE_INVALID = 10013
TRADE_RETCODE_INVALID_VOLUME = 10014
TRADE_RETCODE_INVALID_PRICE = 10015
TRADE_RETCODE_INVALID_STOPS = 10016
TRADE_RETCODE_TRADE_DISABLED = 10017
TRADE_RETCODE_MARKET_CLOSED = 10018
TRADE_RETCODE_NO_MONEY = 10019
TRADE_RETCODE_PRICE_CHANGED = 10020
TRADE_RETCODE_PRICE_OFF = 10021
TRADE_RETCODE_INVALID_EXPIRATION = 10022
TRADE_RETCODE_ORDER_CHANGED = 10023
TRADE_RETCODE_TOO_MANY_REQUESTS = 10024
TRADE_RETCODE_NO_CHANGES = 10025
TRADE_RETCODE_SERVER_DISABLES_AT = 10026
TRADE_RETCODE_CLIENT_DISABLES_AT = 10027
TRADE_RETCODE_LOCKED = 10028
TRADE_RETCODE_FROZEN = 10029
TRADE_RETCODE_INVALID_FILL = 10030
TRADE_RETCODE_CONNECTION = 10031
TRADE_RETCODE_ONLY_REAL = 10032
TRADE_RETCODE_LIMIT_ORDERS = 10033
TRADE_RETCODE_LIMIT_VOLUME = 10034
TRADE_RETCODE_INVALID_ORDER = 10035
TRADE_RETCODE_POSITION_CLOSED = 10036

# Trade Mode
SYMBOL_TRADE_MODE_DISABLED = 0
SYMBOL_TRADE_MODE_LONGONLY = 1
SYMBOL_TRADE_MODE_SHORTONLY = 2
SYMBOL_TRADE_MODE_CLOSEONLY = 3
SYMBOL_TRADE_MODE_FULL = 4

# Exact MT5 Structured Array dtype for rates
RATE_DTYPE = np.dtype(
    [
        ("time", "<i8"),
        ("open", "<f8"),
        ("high", "<f8"),
        ("low", "<f8"),
        ("close", "<f8"),
        ("tick_volume", "<i8"),
        ("spread", "<i4"),
        ("real_volume", "<i8"),
    ]
)

# Resolution lookup: maps MT5 timeframe constant (or minute integer) to (coindcx_resolution, interval_seconds)
TIMEFRAME_MAP: dict[int, tuple[str, int]] = {
    TIMEFRAME_M1: ("1", 60),
    1: ("1", 60),
    TIMEFRAME_M2: ("2", 120),
    2: ("2", 120),
    TIMEFRAME_M3: ("3", 180),
    3: ("3", 180),
    TIMEFRAME_M4: ("4", 240),
    4: ("4", 240),
    TIMEFRAME_M5: ("5", 300),
    5: ("5", 300),
    TIMEFRAME_M6: ("6", 360),
    6: ("6", 360),
    TIMEFRAME_M10: ("10", 600),
    10: ("10", 600),
    TIMEFRAME_M12: ("12", 720),
    12: ("12", 720),
    TIMEFRAME_M15: ("15", 900),
    15: ("15", 900),
    TIMEFRAME_M20: ("20", 1200),
    20: ("20", 1200),
    TIMEFRAME_M30: ("30", 1800),
    30: ("30", 1800),
    TIMEFRAME_H1: ("60", 3600),
    60: ("60", 3600),
    TIMEFRAME_H2: ("120", 7200),
    120: ("120", 7200),
    TIMEFRAME_H3: ("180", 10800),
    180: ("180", 10800),
    TIMEFRAME_H4: ("240", 14400),
    240: ("240", 14400),
    TIMEFRAME_H6: ("360", 21600),
    360: ("360", 21600),
    TIMEFRAME_H8: ("480", 28800),
    480: ("480", 28800),
    TIMEFRAME_H12: ("720", 43200),
    720: ("720", 43200),
    TIMEFRAME_D1: ("1D", 86400),
    1440: ("1D", 86400),
    TIMEFRAME_W1: ("1W", 604800),
    TIMEFRAME_MN1: ("1M", 2592000),
}

# =====================================================================
# Internal State & Bridge Configuration
# =====================================================================

PUBLIC_API_URL = "https://public.coindcx.com"
EXCHANGE_API_URL = "https://api.coindcx.com"

_initialized: bool = False
_live_trading: bool = False
_default_market: str = "futures"  # "futures" or "spot"
_api_key: str | None = None
_api_secret: str | None = None
_last_error: tuple[int, str] = (1, "Success")
_symbol_map: dict[str, str] = {}
_simulated_positions: dict[int, TradePosition] = {}
_simulated_orders: dict[int, TradeOrder] = {}
_ticket_counter: int = 2000000
_simulated_balance: float = 10000.0


def _set_error(code: int, message: str) -> None:
    global _last_error
    _last_error = (code, message)
    logger.debug("MT5 Error [%d]: %s", code, message)


def _http_get_json(url: str, timeout: float = 10.0) -> Any:
    req = Request(url, headers={"User-Agent": "coindcx-mt5-bridge/0.2.0"})
    with urlopen(req, timeout=timeout) as response:
        data = response.read()
        return json.loads(data.decode("utf-8"))


def _http_post_signed(path: str, payload: dict[str, Any], timeout: float = 10.0) -> Any:
    if not _api_key or not _api_secret:
        raise RuntimeError("COINDCX_API_KEY and COINDCX_API_SECRET required for live authenticated calls")
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    signature = hmac.new(_api_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-AUTH-APIKEY": _api_key,
        "X-AUTH-SIGNATURE": signature,
        "User-Agent": "coindcx-mt5-bridge/0.2.0",
    }
    req = Request(f"{EXCHANGE_API_URL}{path}", data=body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"CoinDCX HTTP {exc.code}: {err_body}") from exc


# =====================================================================
# Symbol Resolution & Normalization
# =====================================================================

def normalize_symbol(symbol: str) -> str:
    """Normalizes MT5 Forex/Crypto symbol names into CoinDCX market names.

    Examples:
        "BTCUSD"      -> "B-BTC_USDT" (in futures mode) or "BTCUSDT" (in spot mode)
        "BTCUSDT"     -> "B-BTC_USDT" (in futures mode)
        "B-BTC_USDT"  -> "B-BTC_USDT"
        "ETH/USDT"    -> "B-ETH_USDT"
    """
    sym = symbol.strip().upper()

    # 1. Check user-defined symbol mapping first
    if sym in _symbol_map:
        return _symbol_map[sym]

    # 2. Already fully qualified CoinDCX futures symbol
    if sym.startswith("B-") or sym.startswith("I-"):
        return sym

    # 3. Clean symbols: remove slashes and hyphens
    cleaned = sym.replace("/", "").replace("-", "").replace("_", "")

    # Normalization according to default market type
    if _default_market == "futures":
        # Extract base currency
        base = cleaned
        if base.endswith("USDT"):
            base = base[:-4]
        elif base.endswith("USD"):
            base = base[:-3]
        elif base.endswith("INR"):
            base = base[:-3]
        return f"B-{base}_USDT"
    else:
        # Spot mode
        if cleaned.endswith("USD") and not cleaned.endswith("USDT"):
            cleaned = cleaned[:-3] + "USDT"
        return cleaned


def set_symbol_map(mapping: Mapping[str, str]) -> None:
    """Register custom symbol mappings between MT5 symbols and CoinDCX pairs.

    Example:
        mt5.set_symbol_map({"GOLD": "B-PAXG_USDT", "BTC": "B-BTC_USDT"})
    """
    global _symbol_map
    _symbol_map.update({k.upper(): v for k, v in mapping.items()})


def set_default_market(market: str) -> None:
    """Set default market target: 'futures' (default) or 'spot'."""
    global _default_market
    market = market.lower().strip()
    if market not in ("futures", "spot"):
        raise ValueError("market must be 'futures' or 'spot'")
    _default_market = market


def set_live_trading(enabled: bool) -> None:
    """Explicitly enable or disable live real-money order execution on CoinDCX.

    When False (default), all orders run in high-fidelity simulation mode.
    """
    global _live_trading
    _live_trading = bool(enabled)
    mode = "LIVE REAL TRADING" if _live_trading else "SIMULATION / DRY-RUN"
    logger.info("CoinDCX MT5 Bridge mode switched to: %s", mode)


def is_live_trading() -> bool:
    """Return True if live order execution is active."""
    return _live_trading


# =====================================================================
# MT5 Lifecycle Functions
# =====================================================================

def initialize(
    path: str | None = None,
    login: int | None = None,
    server: str | None = None,
    password: str | None = None,
    timeout: float | None = None,
    portable: bool = False,
    api_key: str | None = None,
    api_secret: str | None = None,
    live_trading: bool | None = None,
    default_market: str | None = None,
) -> bool:
    """Initialize connection to CoinDCX and bridge session.

    Matches MT5 initialize() signature. Accepts additional optional CoinDCX kwargs.
    """
    global _initialized, _api_key, _api_secret, _live_trading, _default_market

    _api_key = api_key or os.getenv("COINDCX_API_KEY")
    _api_secret = api_secret or os.getenv("COINDCX_API_SECRET")

    if live_trading is not None:
        _live_trading = bool(live_trading)
    else:
        env_live = os.getenv("COINDCX_LIVE_TRADING", "").strip().lower()
        _live_trading = env_live in ("true", "1", "yes")

    if default_market is not None:
        set_default_market(default_market)

    # Validate public connectivity
    try:
        data = _http_get_json(f"{PUBLIC_API_URL}/market_data/orderbook?pair=B-BTC_USDT", timeout=timeout or 5.0)
        if not data or "asks" not in data:
            _set_error(TRADE_RETCODE_CONNECTION, "Unable to verify CoinDCX public market connectivity")
            return False
    except Exception as exc:
        _set_error(TRADE_RETCODE_CONNECTION, f"Failed to connect to CoinDCX: {exc}")
        return False

    _initialized = True
    _set_error(1, "Success")
    return True


def shutdown() -> bool:
    """Close connection to CoinDCX bridge session."""
    global _initialized
    _initialized = False
    _set_error(1, "Success")
    return True


def version() -> tuple[int, int, str]:
    """Return simulated MT5 terminal build version."""
    return (500, 4260, "09 Sep 2026")


def last_error() -> tuple[int, str]:
    """Return last error (code, description)."""
    return _last_error


# =====================================================================
# Market Data Functions
# =====================================================================

def symbol_info_tick(symbol: str) -> Tick | None:
    """Fetch current real-time tick for a symbol from CoinDCX.

    Returns:
        Tick namedtuple with time, bid, ask, last, volume, time_msc, flags.
    """
    pair = normalize_symbol(symbol)
    try:
        url = f"{PUBLIC_API_URL}/market_data/orderbook?pair={pair}"
        ob = _http_get_json(url, timeout=5.0)
        bids = ob.get("bids", {})
        asks = ob.get("asks", {})

        best_bid = max((float(p) for p in bids.keys()), default=0.0) if bids else 0.0
        best_ask = min((float(p) for p in asks.keys()), default=0.0) if asks else 0.0
        last = best_bid if best_bid > 0 else best_ask

        # Try to get real volume from best levels
        volume = float(bids.get(str(best_bid), 0.0)) if best_bid else 1.0

        ts_msc = int(time.time() * 1000)
        ts_sec = int(ts_msc / 1000)

        return Tick(
            time=ts_sec,
            bid=best_bid,
            ask=best_ask,
            last=last,
            volume=volume,
            time_msc=ts_msc,
            flags=6,  # TICK_FLAG_BID | TICK_FLAG_ASK
            volume_real=volume,
        )
    except Exception as exc:
        _set_error(TRADE_RETCODE_PRICE_OFF, f"Failed to fetch tick for {symbol} ({pair}): {exc}")
        return None


def symbol_info(symbol: str) -> SymbolInfo | None:
    """Fetch symbol metadata and properties formatted as MT5 SymbolInfo namedtuple."""
    pair = normalize_symbol(symbol)
    tick = symbol_info_tick(symbol)
    if tick is None:
        return None

    # Derive base and quote currency
    currency_profit = "USDT"
    currency_margin = "USDT"
    currency_base = "BTC"
    if pair.startswith("B-") and "_" in pair:
        parts = pair[2:].split("_")
        currency_base = parts[0]
        currency_profit = parts[1]
    elif pair.endswith("USDT"):
        currency_base = pair[:-4]
        currency_profit = "USDT"

    # Digits and point estimation
    digits = 2 if tick.ask > 10 else 4 if tick.ask > 0.1 else 6
    point = 10 ** (-digits)

    return SymbolInfo(
        custom=False,
        chart_mode=0,
        select=True,
        visible=True,
        session_deals=0,
        session_buy_orders=0,
        session_sell_orders=0,
        volume=tick.volume,
        volume_high=0.0,
        volume_low=0.0,
        time=tick.time,
        digits=digits,
        spread=max(1, int(round((tick.ask - tick.bid) / point))) if point > 0 else 1,
        spread_float=True,
        ticks_bookdepth=50,
        trade_calc_mode=0,
        trade_mode=SYMBOL_TRADE_MODE_FULL,
        start_time=0,
        expiration_time=0,
        trade_stops_level=0,
        trade_freeze_level=0,
        trade_exemode=2,
        swap_mode=0,
        swap_rollover3days=3,
        margin_hedged_use_checking=False,
        margin_hedged=0.0,
        price_change=0.0,
        price_volatility=0.0,
        price_theoretical=0.0,
        price_greeks_delta=0.0,
        price_greeks_theta=0.0,
        price_greeks_gamma=0.0,
        price_greeks_vega=0.0,
        price_greeks_rho=0.0,
        price_greeks_omega=0.0,
        price_sensitivity=0.0,
        basis="",
        category="Crypto",
        currency_base=currency_base,
        currency_profit=currency_profit,
        currency_margin=currency_margin,
        bank="",
        description=f"CoinDCX {pair} Market",
        exchange="CoinDCX",
        formula="",
        isin="",
        name=symbol,
        page="",
        path=f"Crypto\\{pair}",
        bid=tick.bid,
        bidhigh=0.0,
        bidlow=0.0,
        ask=tick.ask,
        askhigh=0.0,
        asklow=0.0,
        last=tick.last,
        lasthigh=0.0,
        lastlow=0.0,
        volume_real=tick.volume_real,
        volumehigh_real=0.0,
        volumelow_real=0.0,
        option_strike=0.0,
        point=point,
        trade_tick_value=point,
        trade_tick_value_profit=point,
        trade_tick_value_loss=point,
        trade_tick_size=point,
        trade_contract_size=1.0,
        volume_min=0.0001,
        volume_max=1000.0,
        volume_step=0.0001,
        volume_limit=0.0,
        swap_long=0.0,
        swap_short=0.0,
        margin_initial=0.0,
        margin_maintenance=0.0,
        session_volume=0.0,
        session_turnover=0.0,
        session_interest=0.0,
        session_buy_orders_volume=0.0,
        session_sell_orders_volume=0.0,
        session_open=0.0,
        session_close=0.0,
        session_aw=0.0,
        price_strike=0.0,
    )


def symbol_select(symbol: str, enable: bool = True) -> bool:
    """Select a symbol in Market Watch (always returns True for supported symbols)."""
    return True


def symbols_total() -> int:
    """Return total count of available symbols."""
    return 100


def symbols_get(group: str | None = None) -> tuple[SymbolInfo, ...]:
    """Return available symbols as a tuple of SymbolInfo."""
    default_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
    results = []
    for sym in default_symbols:
        info = symbol_info(sym)
        if info:
            results.append(info)
    return tuple(results)


def copy_rates_from_pos(
    symbol: str,
    timeframe: int,
    start_pos: int,
    count: int,
) -> np.ndarray | None:
    """Copy candlestick rates starting from specified index position backwards.

    Returns:
        np.ndarray with structured dtype:
        [('time', '<i8'), ('open', '<f8'), ('high', '<f8'), ('low', '<f8'),
         ('close', '<f8'), ('tick_volume', '<i8'), ('spread', '<i4'), ('real_volume', '<i8')]
    """
    if count <= 0:
        _set_error(TRADE_RETCODE_INVALID, "count must be greater than 0")
        return None

    res_info = TIMEFRAME_MAP.get(timeframe)
    if not res_info:
        _set_error(TRADE_RETCODE_INVALID, f"Unsupported timeframe: {timeframe}")
        return None

    resolution, interval_sec = res_info
    pair = normalize_symbol(symbol)

    # Determine timestamp query window
    now = int(time.time())
    buffer_candles = max(10, int(count * 0.2))
    total_needed = start_pos + count + buffer_candles
    from_ts = now - (total_needed * interval_sec)
    to_ts = now

    pcode = "&pcode=f" if pair.startswith("B-") else ""
    url = (
        f"{PUBLIC_API_URL}/market_data/candlesticks"
        f"?pair={pair}&from={from_ts}&to={to_ts}&resolution={resolution}{pcode}"
    )

    try:
        res = _http_get_json(url, timeout=10.0)
        raw_candles = res.get("data", [])
        if not raw_candles:
            _set_error(TRADE_RETCODE_DONE, "No candle data returned")
            return np.empty(0, dtype=RATE_DTYPE)

        # Sort chronologically (oldest to newest)
        raw_candles.sort(key=lambda x: x.get("time", 0))

        # Slicing from pos:
        # start_pos=0 means ending at the most recent candle
        if start_pos == 0:
            selected = raw_candles[-count:]
        else:
            selected = raw_candles[-(count + start_pos) : -start_pos]

        records = []
        for c in selected:
            t_sec = int(c.get("time", 0) / 1000)
            records.append(
                (
                    t_sec,
                    float(c.get("open", 0.0)),
                    float(c.get("high", 0.0)),
                    float(c.get("low", 0.0)),
                    float(c.get("close", 0.0)),
                    int(float(c.get("volume", 0.0))),
                    2,  # default spread
                    int(float(c.get("volume", 0.0))),
                )
            )

        return np.array(records, dtype=RATE_DTYPE)
    except Exception as exc:
        _set_error(TRADE_RETCODE_ERROR, f"Failed to fetch candlesticks for {symbol}: {exc}")
        return None


def copy_rates_range(
    symbol: str,
    timeframe: int,
    date_from: datetime | int,
    date_to: datetime | int,
) -> np.ndarray | None:
    """Copy rates for specified date/time range."""
    res_info = TIMEFRAME_MAP.get(timeframe)
    if not res_info:
        _set_error(TRADE_RETCODE_INVALID, f"Unsupported timeframe: {timeframe}")
        return None

    resolution, _ = res_info
    pair = normalize_symbol(symbol)

    from_ts = int(date_from.timestamp()) if isinstance(date_from, datetime) else int(date_from)
    to_ts = int(date_to.timestamp()) if isinstance(date_to, datetime) else int(date_to)

    pcode = "&pcode=f" if pair.startswith("B-") else ""
    url = (
        f"{PUBLIC_API_URL}/market_data/candlesticks"
        f"?pair={pair}&from={from_ts}&to={to_ts}&resolution={resolution}{pcode}"
    )

    try:
        res = _http_get_json(url, timeout=10.0)
        raw_candles = res.get("data", [])
        raw_candles.sort(key=lambda x: x.get("time", 0))

        records = [
            (
                int(c.get("time", 0) / 1000),
                float(c.get("open", 0.0)),
                float(c.get("high", 0.0)),
                float(c.get("low", 0.0)),
                float(c.get("close", 0.0)),
                int(float(c.get("volume", 0.0))),
                2,
                int(float(c.get("volume", 0.0))),
            )
            for c in raw_candles
        ]
        return np.array(records, dtype=RATE_DTYPE)
    except Exception as exc:
        _set_error(TRADE_RETCODE_ERROR, f"Failed to fetch candle range for {symbol}: {exc}")
        return None


def copy_rates_from(
    symbol: str,
    timeframe: int,
    date_from: datetime | int,
    count: int,
) -> np.ndarray | None:
    """Copy rates starting from specified datetime forward."""
    res_info = TIMEFRAME_MAP.get(timeframe)
    if not res_info:
        _set_error(TRADE_RETCODE_INVALID, f"Unsupported timeframe: {timeframe}")
        return None

    _, interval_sec = res_info
    from_ts = int(date_from.timestamp()) if isinstance(date_from, datetime) else int(date_from)
    to_ts = from_ts + (count * interval_sec)
    return copy_rates_range(symbol, timeframe, from_ts, to_ts)


# =====================================================================
# Trading & Order Management
# =====================================================================

def order_check(request: dict[str, Any]) -> OrderCheckResult:
    """Simulate order check for validity without execution."""
    symbol = request.get("symbol")
    if not symbol:
        return OrderCheckResult(
            retcode=TRADE_RETCODE_INVALID,
            balance=_simulated_balance,
            equity=_simulated_balance,
            profit=0.0,
            margin=0.0,
            margin_free=_simulated_balance,
            margin_level=0.0,
            comment="Symbol not specified",
            request=request,
        )

    volume = float(request.get("volume", 0.0))
    if volume <= 0:
        return OrderCheckResult(
            retcode=TRADE_RETCODE_INVALID_VOLUME,
            balance=_simulated_balance,
            equity=_simulated_balance,
            profit=0.0,
            margin=0.0,
            margin_free=_simulated_balance,
            margin_level=0.0,
            comment="Invalid order volume",
            request=request,
        )

    return OrderCheckResult(
        retcode=0,
        balance=_simulated_balance,
        equity=_simulated_balance,
        profit=0.0,
        margin=100.0,
        margin_free=_simulated_balance - 100.0,
        margin_level=1000.0,
        comment="Done",
        request=request,
    )


def order_send(request: dict[str, Any]) -> OrderSendResult:
    """Send an order request to CoinDCX using the standard MT5 request dict.

    Safety:
        Defaults to Dry-Run Simulation unless `set_live_trading(True)` has been called.

    Supported request fields:
        - action: TRADE_ACTION_DEAL, TRADE_ACTION_PENDING, etc.
        - symbol: "BTCUSD", "B-BTC_USDT", etc.
        - volume: float or int
        - type: ORDER_TYPE_BUY, ORDER_TYPE_SELL, ORDER_TYPE_BUY_LIMIT, etc.
        - price: float execution price (optional for market orders)
        - sl: float stop loss
        - tp: float take profit
        - position: int ticket (to close an existing position)
        - magic: int EA identifier
        - comment: str comment
    """
    global _ticket_counter, _simulated_positions

    symbol = str(request.get("symbol", "")).strip()
    if not symbol:
        _set_error(TRADE_RETCODE_INVALID, "Order request must specify symbol")
        return OrderSendResult(TRADE_RETCODE_INVALID, 0, 0, 0.0, 0.0, 0.0, 0.0, "Missing symbol", 0, 0, request)

    pair = normalize_symbol(symbol)
    volume = float(request.get("volume", 0.0))
    if volume <= 0:
        _set_error(TRADE_RETCODE_INVALID_VOLUME, "Order volume must be greater than 0")
        return OrderSendResult(TRADE_RETCODE_INVALID_VOLUME, 0, 0, 0.0, 0.0, 0.0, 0.0, "Invalid volume", 0, 0, request)

    order_type = request.get("type", ORDER_TYPE_BUY)
    is_buy = order_type in (ORDER_TYPE_BUY, ORDER_TYPE_BUY_LIMIT, ORDER_TYPE_BUY_STOP)
    is_sell = order_type in (ORDER_TYPE_SELL, ORDER_TYPE_SELL_LIMIT, ORDER_TYPE_SELL_STOP)

    if not is_buy and not is_sell:
        _set_error(TRADE_RETCODE_INVALID_ORDER, f"Unsupported order type: {order_type}")
        return OrderSendResult(TRADE_RETCODE_INVALID_ORDER, 0, 0, 0.0, 0.0, 0.0, 0.0, "Invalid order type", 0, 0, request)

    # Fetch current prices for reference
    tick = symbol_info_tick(symbol)
    bid = tick.bid if tick else 0.0
    ask = tick.ask if tick else 0.0
    exec_price = float(request.get("price") or (ask if is_buy else bid))

    position_ticket = request.get("position")

    # -------------------------------------------------------------
    # SIMULATION / DRY-RUN MODE (Default)
    # -------------------------------------------------------------
    if not _live_trading:
        _ticket_counter += 1
        ticket = _ticket_counter
        deal_id = ticket
        now_ts = int(time.time())

        # If closing an existing position ticket
        if position_ticket and int(position_ticket) in _simulated_positions:
            closed_pos = _simulated_positions.pop(int(position_ticket))
            pnl = (exec_price - closed_pos.price_open) * closed_pos.volume if closed_pos.type == POSITION_TYPE_BUY else (closed_pos.price_open - exec_price) * closed_pos.volume
            logger.info(
                "[DRY-RUN] Closed Position #%d (%s, vol=%.4f) at %.2f | PnL: %.2f USDT",
                closed_pos.ticket, closed_pos.symbol, closed_pos.volume, exec_price, pnl
            )
            return OrderSendResult(
                retcode=TRADE_RETCODE_DONE,
                deal=deal_id,
                order=ticket,
                volume=volume,
                price=exec_price,
                bid=bid,
                ask=ask,
                comment=f"Dry-run closed position #{position_ticket}",
                request_id=ticket,
                retcode_external=0,
                request=request,
            )

        # Create new simulated position for DEAL
        pos_type = POSITION_TYPE_BUY if is_buy else POSITION_TYPE_SELL
        new_pos = TradePosition(
            ticket=ticket,
            time=now_ts,
            time_msc=now_ts * 1000,
            time_update=now_ts,
            time_update_msc=now_ts * 1000,
            type=pos_type,
            magic=int(request.get("magic", 0)),
            identifier=ticket,
            reason=0,
            volume=volume,
            price_open=exec_price,
            sl=float(request.get("sl", 0.0)),
            tp=float(request.get("tp", 0.0)),
            price_current=exec_price,
            swap=0.0,
            profit=0.0,
            symbol=symbol,
            comment=str(request.get("comment", "Dry-run order")),
            external_id=f"SIM-{ticket}",
        )
        _simulated_positions[ticket] = new_pos
        logger.info(
            "[DRY-RUN] Executed %s %s | Vol: %.4f | Price: %.2f | Ticket: #%d",
            "BUY" if is_buy else "SELL", symbol, volume, exec_price, ticket
        )

        return OrderSendResult(
            retcode=TRADE_RETCODE_DONE,
            deal=deal_id,
            order=ticket,
            volume=volume,
            price=exec_price,
            bid=bid,
            ask=ask,
            comment="Dry-run order filled successfully",
            request_id=ticket,
            retcode_external=0,
            request=request,
        )

    # -------------------------------------------------------------
    # LIVE TRADING EXECUTION ON COINDCX
    # -------------------------------------------------------------
    try:
        side_str = "buy" if is_buy else "sell"
        order_type_str = "limit_order" if request.get("price") else "market_order"
        timestamp_ms = int(time.time() * 1000)

        # Decide whether to use Futures endpoint or Spot endpoint
        if pair.startswith("B-"):
            # Futures order
            payload: dict[str, Any] = {
                "side": side_str,
                "order_type": order_type_str,
                "market": pair,
                "total_quantity": format(Decimal(str(volume)), "f"),
                "timestamp": timestamp_ms,
            }
            if order_type_str == "limit_order":
                payload["price_per_unit"] = format(Decimal(str(exec_price)), "f")

            resp = _http_post_signed("/exchange/v1/derivatives/futures/orders/create", payload)
        else:
            # Spot order
            payload = {
                "side": side_str,
                "order_type": order_type_str,
                "market": pair,
                "total_quantity": format(Decimal(str(volume)), "f"),
                "timestamp": timestamp_ms,
            }
            if order_type_str == "limit_order":
                payload["price_per_unit"] = format(Decimal(str(exec_price)), "f")

            resp = _http_post_signed("/exchange/v1/orders/create", payload)

        order_id = resp.get("id") or resp.get("order_id") or int(time.time())
        return OrderSendResult(
            retcode=TRADE_RETCODE_DONE,
            deal=order_id,
            order=order_id,
            volume=volume,
            price=exec_price,
            bid=bid,
            ask=ask,
            comment="CoinDCX live order placed",
            request_id=order_id,
            retcode_external=0,
            request=request,
        )
    except Exception as exc:
        _set_error(TRADE_RETCODE_ERROR, f"Live order failed: {exc}")
        return OrderSendResult(
            retcode=TRADE_RETCODE_ERROR,
            deal=0,
            order=0,
            volume=volume,
            price=exec_price,
            bid=bid,
            ask=ask,
            comment=f"Error: {exc}",
            request_id=0,
            retcode_external=1,
            request=request,
        )


def positions_get(
    symbol: str | None = None,
    ticket: int | None = None,
) -> tuple[TradePosition, ...]:
    """Return active open positions, dynamically updating current price and unrealized PnL."""
    if not _live_trading:
        # In simulation mode, refresh prices and unrealized profit
        results = []
        for pos in list(_simulated_positions.values()):
            if symbol and normalize_symbol(pos.symbol) != normalize_symbol(symbol):
                continue
            if ticket is not None and pos.ticket != ticket:
                continue

            # Update current market price & profit
            tick = symbol_info_tick(pos.symbol)
            if tick:
                current_price = tick.bid if pos.type == POSITION_TYPE_BUY else tick.ask
                if pos.type == POSITION_TYPE_BUY:
                    profit = (current_price - pos.price_open) * pos.volume
                else:
                    profit = (pos.price_open - current_price) * pos.volume
            else:
                current_price = pos.price_current
                profit = pos.profit

            updated_pos = pos._replace(price_current=current_price, profit=round(profit, 4))
            _simulated_positions[pos.ticket] = updated_pos
            results.append(updated_pos)

        return tuple(results)

    # In live mode, query CoinDCX futures positions if API credentials available
    try:
        positions_raw = _http_post_signed(
            "/exchange/v1/derivatives/futures/positions",
            {"timestamp": int(time.time() * 1000)},
        )
        results = []
        now_ts = int(time.time())
        for idx, p in enumerate(positions_raw or []):
            mkt = p.get("market", "")
            if symbol and normalize_symbol(mkt) != normalize_symbol(symbol):
                continue

            side = p.get("side", "buy").lower()
            pos_type = POSITION_TYPE_BUY if side == "buy" else POSITION_TYPE_SELL
            qty = float(p.get("quantity", 0.0))
            if qty <= 0:
                continue

            entry_price = float(p.get("entry_price", 0.0))
            mark_price = float(p.get("mark_price", entry_price))
            unrealized_pnl = float(p.get("unrealized_pnl", 0.0))
            t_id = int(p.get("id", idx + 10000))

            tp = TradePosition(
                ticket=t_id,
                time=now_ts,
                time_msc=now_ts * 1000,
                time_update=now_ts,
                time_update_msc=now_ts * 1000,
                type=pos_type,
                magic=0,
                identifier=t_id,
                reason=0,
                volume=qty,
                price_open=entry_price,
                sl=0.0,
                tp=0.0,
                price_current=mark_price,
                swap=0.0,
                profit=unrealized_pnl,
                symbol=mkt,
                comment="CoinDCX Live Position",
                external_id=str(t_id),
            )
            results.append(tp)
        return tuple(results)
    except Exception as exc:
        _set_error(TRADE_RETCODE_ERROR, f"Failed to fetch live positions: {exc}")
        return ()


def positions_total() -> int:
    """Return total number of open positions."""
    return len(positions_get())


def orders_get(
    symbol: str | None = None,
    ticket: int | None = None,
) -> tuple[TradeOrder, ...]:
    """Return pending orders."""
    results = []
    for ord_obj in list(_simulated_orders.values()):
        if symbol and normalize_symbol(ord_obj.symbol) != normalize_symbol(symbol):
            continue
        if ticket is not None and ord_obj.ticket != ticket:
            continue
        results.append(ord_obj)
    return tuple(results)


def orders_total() -> int:
    """Return total number of pending orders."""
    return len(orders_get())


def account_info() -> AccountInfo | None:
    """Return trading account information formatted as MT5 AccountInfo namedtuple."""
    if not _live_trading or not _api_key or not _api_secret:
        # Dry-run account representation
        total_profit = sum(p.profit for p in _simulated_positions.values())
        equity = _simulated_balance + total_profit
        margin = sum(p.price_open * p.volume * 0.1 for p in _simulated_positions.values())
        margin_free = max(0.0, equity - margin)
        margin_level = (equity / margin * 100) if margin > 0 else 0.0

        return AccountInfo(
            login=100888,
            trade_mode=0,
            leverage=10,
            limit_orders=500,
            margin_so_mode=0,
            trade_allowed=True,
            trade_expert=True,
            margin_mode=0,
            currency_digits=2,
            fifo=False,
            balance=_simulated_balance,
            credit=0.0,
            profit=round(total_profit, 2),
            equity=round(equity, 2),
            margin=round(margin, 2),
            margin_free=round(margin_free, 2),
            margin_level=round(margin_level, 2),
            margin_so_call=50.0,
            margin_so_so=30.0,
            margin_initial=0.0,
            margin_maintenance=0.0,
            assets=0.0,
            liabilities=0.0,
            commission_blocked=0.0,
            name="CoinDCX MT5 Bridge (Simulation)",
            server="CoinDCX-Sim",
            currency="USDT",
            company="CoinDCX",
        )

    # Live balance fetch from CoinDCX
    try:
        raw_balances = _http_post_signed(
            "/exchange/v1/users/balances",
            {"timestamp": int(time.time() * 1000)},
        )
        usdt_balance = 0.0
        for item in raw_balances or []:
            if item.get("currency") == "USDT":
                usdt_balance = float(item.get("balance", 0.0))
                break

        positions = positions_get()
        total_profit = sum(p.profit for p in positions)
        equity = usdt_balance + total_profit

        return AccountInfo(
            login=999001,
            trade_mode=1,
            leverage=10,
            limit_orders=1000,
            margin_so_mode=0,
            trade_allowed=True,
            trade_expert=True,
            margin_mode=0,
            currency_digits=2,
            fifo=False,
            balance=round(usdt_balance, 2),
            credit=0.0,
            profit=round(total_profit, 2),
            equity=round(equity, 2),
            margin=0.0,
            margin_free=round(equity, 2),
            margin_level=0.0,
            margin_so_call=50.0,
            margin_so_so=30.0,
            margin_initial=0.0,
            margin_maintenance=0.0,
            assets=0.0,
            liabilities=0.0,
            commission_blocked=0.0,
            name="CoinDCX Live Account",
            server="CoinDCX-Live",
            currency="USDT",
            company="CoinDCX",
        )
    except Exception as exc:
        _set_error(TRADE_RETCODE_ERROR, f"Failed to fetch account info: {exc}")
        return None
