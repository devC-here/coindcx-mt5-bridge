"""MT5 Drop-In Strategy Demonstration on CoinDCX.

This script demonstrates a standard MetaTrader 5 algorithmic trading strategy
running directly on CoinDCX Spot & Futures.

Notice that the entire trading strategy logic, data structures, and function calls
remain 100% identical to official MetaTrader 5 Python scripts.
The only difference is the import:
    from coindcx_mt5 import mt5
"""

import sys
from pathlib import Path

# Add project root to sys.path for direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
# Drop-in replacement for `import MetaTrader5 as mt5`
from coindcx_mt5 import mt5


def run_strategy():
    print("=" * 70)
    print(" CoinDCX MT5 Compatibility Bridge - Live Drop-In Demo")
    print("=" * 70)

    # 1. Initialize the terminal session
    if not mt5.initialize():
        print("[-] Failed to initialize MT5 bridge:", mt5.last_error())
        sys.exit(1)

    print("[+] Bridge initialized successfully!")
    print(f"[+] Terminal Version: {mt5.version()}")
    print(f"[+] Mode: {'LIVE REAL ORDERS' if mt5.is_live_trading() else 'SIMULATION / DRY-RUN (Safe)'}")

    # 2. Query Account Information
    account = mt5.account_info()
    if account:
        print(f"\n--- Account Status ---")
        print(f"Login / ID : {account.login}")
        print(f"Server     : {account.server}")
        print(f"Balance    : {account.balance:.2f} {account.currency}")
        print(f"Equity     : {account.equity:.2f} {account.currency}")
        print(f"Free Margin: {account.margin_free:.2f} {account.currency}")

    symbol = "BTCUSD"

    # 3. Fetch Real-time Tick
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        print(f"[-] Could not retrieve tick for {symbol}")
        mt5.shutdown()
        return

    print(f"\n--- Real-Time Tick for {symbol} ---")
    print(f"Bid Price : ${tick.bid:,.2f}")
    print(f"Ask Price : ${tick.ask:,.2f}")
    print(f"Spread    : ${(tick.ask - tick.bid):,.2f}")

    # 4. Fetch Candlesticks (15-Minute Bars)
    print(f"\n--- Fetching Historical Rates ---")
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 30)
    if rates is None or len(rates) == 0:
        print(f"[-] Failed to fetch rates: {mt5.last_error()}")
        mt5.shutdown()
        return

    df = pd.DataFrame(rates)
    df["datetime"] = pd.to_datetime(df["time"], unit="s")
    df["sma_fast"] = df["close"].rolling(5).mean()
    df["sma_slow"] = df["close"].rolling(15).mean()

    latest_close = df["close"].iloc[-1]
    fast_ma = df["sma_fast"].iloc[-1]
    slow_ma = df["sma_slow"].iloc[-1]

    print(f"Latest Bar Close : ${latest_close:,.2f}")
    print(f"Fast SMA (5)     : ${fast_ma:,.2f}")
    print(f"Slow SMA (15)    : ${slow_ma:,.2f}")

    signal = "BUY" if fast_ma > slow_ma else "SELL"
    print(f"Strategy Signal  : {signal} (Trend Following MA Crossover)")

    # 5. Place an Order (Simulated / Dry-Run by default)
    order_type = mt5.ORDER_TYPE_BUY if signal == "BUY" else mt5.ORDER_TYPE_SELL
    exec_price = tick.ask if signal == "BUY" else tick.bid
    sl_price = exec_price * 0.98 if signal == "BUY" else exec_price * 1.02
    tp_price = exec_price * 1.04 if signal == "BUY" else exec_price * 0.96

    order_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": 0.001,
        "type": order_type,
        "price": exec_price,
        "sl": sl_price,
        "tp": tp_price,
        "magic": 987654,
        "comment": "SMA Crossover Bot",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    print(f"\n--- Sending Order Request ---")
    print(f"Order: {signal} 0.001 {symbol} @ ${exec_price:,.2f} | SL: ${sl_price:,.2f} | TP: ${tp_price:,.2f}")

    result = mt5.order_send(order_request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"[+] Order Placed Successfully!")
        print(f"    Deal ID  : #{result.deal}")
        print(f"    Order ID : #{result.order}")
        print(f"    Volume   : {result.volume}")
        print(f"    Price    : ${result.price:,.2f}")
        print(f"    Status   : {result.comment}")
    else:
        print(f"[-] Order Failed with code {result.retcode}: {result.comment}")

    # 6. Check Active Positions
    positions = mt5.positions_get(symbol=symbol)
    print(f"\n--- Open Positions ({len(positions)}) ---")
    for pos in positions:
        pos_dir = "BUY (Long)" if pos.type == mt5.POSITION_TYPE_BUY else "SELL (Short)"
        print(
            f"  Ticket #{pos.ticket} | {pos.symbol} {pos_dir} | "
            f"Vol: {pos.volume} | Open: ${pos.price_open:,.2f} | "
            f"Now: ${pos.price_current:,.2f} | Profit: ${pos.profit:,.2f}"
        )

    # 7. Shutdown
    mt5.shutdown()
    print("\n[+] Bridge session closed cleanly.")
    print("=" * 70)


if __name__ == "__main__":
    run_strategy()
