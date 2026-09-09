# CoinDCX MT5 Bridge & Execution Core

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Rust](https://img.shields.io/badge/Rust-2021-DEA584?logo=rust&logoColor=white)](https://www.rust-lang.org/)
[![Safety](https://img.shields.io/badge/Safety-Dry--Run%20Default-green)](#-safety-first-architecture)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen)](#-running-tests)

A drop-in Python compatibility library and bridge that connects algorithmic trading strategies, indicators, and bots written for **MetaTrader 5 (MT5)** directly to **CoinDCX Spot and Futures** with **zero to minimal code overhaul**.

---

## 🎯 The Core Idea: Zero Code Overhaul

If you have existing trading robots, indicators, or machine learning pipelines built for MT5, you don't need to rewrite your data parsing, order logic, or position tracking. Simply swap your import:

```python
# -------------------------------------------------------------
# 1. SWAP YOUR IMPORT (Everything else stays identical!)
# -------------------------------------------------------------
# Instead of: import MetaTrader5 as mt5
from coindcx_mt5 import mt5

# 2. INITIALIZE SESSION
if not mt5.initialize():
    print("Failed to initialize MT5 bridge:", mt5.last_error())
    quit()

# 3. FETCH CANDLES (Returns exact MT5 numpy structured array!)
rates = mt5.copy_rates_from_pos("BTCUSD", mt5.TIMEFRAME_M15, 0, 50)
import pandas as pd
df = pd.DataFrame(rates)  # Has columns: time, open, high, low, close, tick_volume, spread, real_volume

# 4. REAL-TIME TICK
tick = mt5.symbol_info_tick("BTCUSD")
print(f"Bid: {tick.bid} | Ask: {tick.ask}")

# 5. SEND ORDERS USING STANDARD MT5 REQUEST DICTIONARY
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": "BTCUSD",
    "volume": 0.001,
    "type": mt5.ORDER_TYPE_BUY,
    "price": tick.ask,
    "sl": tick.ask * 0.98,
    "tp": tick.ask * 1.04,
    "magic": 123456,
    "comment": "My MT5 Strategy on CoinDCX",
}
result = mt5.order_send(request)
if result.retcode == mt5.TRADE_RETCODE_DONE:
    print(f"Order filled! Deal #{result.deal} | Ticket #{result.order}")

# 6. QUERY ACTIVE POSITIONS & ACCOUNT
positions = mt5.positions_get(symbol="BTCUSD")
account = mt5.account_info()
print(f"Account Balance: {account.balance} {account.currency} | Equity: {account.equity}")

# 7. SHUTDOWN
mt5.shutdown()
```

---

## 🚀 Key Features

- **Drop-in MT5 Compatibility**: Emulates the official `MetaTrader5` Python API (`initialize`, `copy_rates_from_pos`, `symbol_info_tick`, `order_send`, `positions_get`, `account_info`).
- **Exact MT5 NumPy Structured Array Schema**: `copy_rates_from_pos` returns `numpy.ndarray` with dtype `[('time', '<i8'), ('open', '<f8'), ('high', '<f8'), ('low', '<f8'), ('close', '<f8'), ('tick_volume', '<i8'), ('spread', '<i4'), ('real_volume', '<i8')]`, ensuring 100% plug-and-play compatibility with `pandas.DataFrame(rates)`.
- **Intelligent Symbol Normalization**: Automatically maps standard MT5 Forex/Crypto names (`BTCUSD`, `BTCUSDT`, `BTC/USDT`) to CoinDCX Futures (`B-BTC_USDT`) or CoinDCX Spot (`BTCUSDT`).
- **Safe-by-Default Simulation**: Runs in high-fidelity simulation mode by default. Test your strategies against live CoinDCX orderbooks without risking real capital until you explicitly opt into live trading.
- **Dynamic Real-Time PnL**: Simulated positions recalculate unrealized profit and loss in real-time against live market orderbooks.
- **Low-Latency Research**: Includes experimental C DPDK kernel-bypass order settlement and Rust zero-copy UDP binary packet serialization harnesses.

---

## 🛡️ Safety-First Architecture

By default, the bridge operates in **Simulation / Dry-Run Mode**:
- `mt5.order_send()` validates request syntax, fills against live bid/ask prices, logs execution, and returns standard MT5 `TRADE_RETCODE_DONE` (10009).
- Positions are tracked in an in-memory ledger with live mark-to-market valuations.

### Enabling Live Real-Money Execution:
To send real orders with actual capital to CoinDCX:
```python
# Enable in Python:
mt5.set_live_trading(True)

# Or set in environment:
# export COINDCX_LIVE_TRADING=true
# export COINDCX_API_KEY="your_api_key"
# export COINDCX_API_SECRET="your_api_secret"
```

---

## 📁 Repository Structure

```
coindcx-mt5-bridge/
├── coindcx_mt5/              # Core Python package
│   ├── __init__.py           # Package exports & mt5 alias
│   ├── compat.py             # MT5 drop-in emulator module
│   ├── client.py             # HMAC-SHA256 authenticated REST client
│   ├── models.py             # Order models & payload builders
│   └── mt5_adapter.py        # MT5 signal to CoinDCX order translator
├── examples/
│   ├── mt5_dropin_demo.py    # Complete MA crossover strategy demo
│   └── mt5_signal.py         # Signal conversion example
├── tests/
│   ├── test_compat.py        # Full MT5 API compatibility tests
│   └── test_client.py        # REST client & auth signature tests
├── hft-experiments/          # Low-latency research components
│   ├── rust-order-sender/    # Zero-copy binary UDP packet sender (Rust)
│   └── dpdk-settlement.c     # DPDK Ethernet fast-path order processor (C)
├── pyproject.toml            # Package configuration
└── README.md
```

---

## 🛠️ Installation

```bash
git clone https://github.com/devC-here/coindcx-mt5-bridge.git
cd coindcx-mt5-bridge
pip install -e .
```

---

## 💡 Quick Start: Run the Drop-In Strategy Demo

Run the end-to-end MT5 strategy demonstration:

```bash
python examples/mt5_dropin_demo.py
```

Sample output:
```
======================================================================
 CoinDCX MT5 Compatibility Bridge - Live Drop-In Demo
======================================================================
[+] Bridge initialized successfully!
[+] Terminal Version: (500, 4260, '09 Sep 2026')
[+] Mode: SIMULATION / DRY-RUN (Safe)

--- Account Status ---
Login / ID : 100888
Server     : CoinDCX-Sim
Balance    : 10000.00 USDT
Equity     : 10000.00 USDT
Free Margin: 10000.00 USDT

--- Real-Time Tick for BTCUSD ---
Bid Price : $79,196.00
Ask Price : $79,196.01
Spread    : $0.01

--- Fetching Historical Rates ---
Latest Bar Close : $79,158.00
Fast SMA (5)     : $79,152.68
Slow SMA (15)    : $79,244.45
Strategy Signal  : SELL (Trend Following MA Crossover)

--- Sending Order Request ---
Order: SELL 0.001 BTCUSD @ $79,196.00 | SL: $80,779.92 | TP: $76,028.16
[+] Order Placed Successfully!
    Deal ID  : #2000001
    Order ID : #2000001
    Volume   : 0.001
    Price    : $79,196.00
    Status   : Dry-run order filled successfully

--- Open Positions (1) ---
  Ticket #2000001 | BTCUSD SELL (Short) | Vol: 0.001 | Open: $79,196.00 | Now: $79,180.01 | Profit: $0.02

[+] Bridge session closed cleanly.
======================================================================
```

---

## 🧪 Running Tests

Execute the comprehensive test suite verifying the MT5 compatibility layer and REST client:

```bash
python -m unittest discover -s tests -v
```

---

## ⚙️ Configuration & Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `COINDCX_API_KEY` | CoinDCX API Key for authenticated endpoints | `None` |
| `COINDCX_API_SECRET` | CoinDCX API Secret for HMAC-SHA256 signatures | `None` |
| `COINDCX_LIVE_TRADING` | Set to `true` to enable real order placement | `false` |

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
