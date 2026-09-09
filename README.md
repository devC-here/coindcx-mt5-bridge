# CoinDCX MT5 Compatibility Bridge

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Safety](https://img.shields.io/badge/Safety-Dry--Run%20Default-green)](#-safety-first-architecture)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen)](#-running-tests)

A clean, drop-in Python compatibility library that connects algorithmic trading strategies, indicators, and bots written for **MetaTrader 5 (MT5)** directly to **CoinDCX Spot and Futures** with **zero code overhaul**.

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

# 4. REAL-TIME TICK & SPREAD
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

- **Drop-in MT5 Compatibility**: Full 1:1 emulation of the official `MetaTrader5` Python API (`initialize`, `copy_rates_from_pos`, `symbol_info_tick`, `order_send`, `positions_get`, `account_info`).
- **Exact MT5 NumPy Structured Array Schema**: `copy_rates_from_pos` returns `numpy.ndarray` with dtype `[('time', '<i8'), ('open', '<f8'), ('high', '<f8'), ('low', '<f8'), ('close', '<f8'), ('tick_volume', '<i8'), ('spread', '<i4'), ('real_volume', '<i8')]`, ensuring 100% plug-and-play compatibility with `pandas.DataFrame(rates)`.
- **Intelligent Symbol Normalization**: Automatically maps standard MT5 Forex/Crypto names (`BTCUSD`, `BTCUSDT`, `BTC/USDT`) to CoinDCX Futures (`B-BTC_USDT`) or CoinDCX Spot (`BTCUSDT`). Custom symbol mappings supported via `mt5.set_symbol_map(...)`.
- **Safe-by-Default Simulation Engine**: Operates in high-fidelity simulation mode by default. Orders validate syntax, fill against live bid/ask quotes, and maintain an in-memory position ledger with live unrealized mark-to-market PnL.
- **Two-Step Live Execution Gating**: Real orders with actual funds are only transmitted when explicitly enabled via `mt5.set_live_trading(True)` or `COINDCX_LIVE_TRADING=true`.

---

## 📁 Clean Repository Structure

```
coindcx-mt5-bridge/
├── coindcx_mt5/              # Clean Python MT5 bridge library
│   ├── __init__.py           # Package exports & mt5 alias
│   └── compat.py             # Complete MT5 API emulator & CoinDCX connector
├── examples/
│   └── mt5_dropin_demo.py    # Complete MA crossover strategy demo
├── tests/
│   └── test_compat.py        # Comprehensive MT5 API test suite
├── pyproject.toml            # Package configuration (numpy>=1.20.0)
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

---

## 🧪 Running Tests

Run the unit test suite verifying the MT5 API compatibility:

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
