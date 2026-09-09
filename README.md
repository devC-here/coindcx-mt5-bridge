# CoinDCX MT5 Bridge & Execution Core

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Rust](https://img.shields.io/badge/Rust-2021-DEA584?logo=rust&logoColor=white)](https://www.rust-lang.org/)
[![Safety](https://img.shields.io/badge/Safety-Dry--Run%20Default-green)](#safety-features)

A modular, safety-first Python library designed to map MetaTrader 5 (MT5) algorithmic trading signals directly to CoinDCX Spot and Futures REST endpoints. Also features experimental low-latency kernel-bypass C (DPDK) and Rust UDP order creation harnesses for high-frequency trading research.

---

## 🚀 Key Features

- **Safe by Default**: All order requests execute in dry-run mode unless both `live_trading=True` is set on client initialization **and** `confirm_live=True` is provided on the specific execution call.
- **MT5 to CoinDCX Symbol Mapping**: Built-in order adapter converting MT5 tick volumes, lot sizes, and market codes to CoinDCX exchange standards.
- **Zero Heavy Dependencies**: Built with native Python standard libraries (`urllib`, `hmac`, `hashlib`) for maximum portability and zero dependency bloat.
- **Unit Tested**: Full test coverage of client signature generation, payload formatting, and dry-run safety gates.
- **Low-Latency Experiments**: Includes a Rust UDP binary packet order sender and a C DPDK fast-path kernel-bypass settlement loop.

---

## 📁 Repository Structure

```
coindcx-mt5-bridge/
├── coindcx_mt5/              # Core Python package
│   ├── __init__.py           # Package exports
│   ├── client.py             # HMAC-SHA256 authenticated REST client
│   ├── models.py             # Order models & payload builders
│   └── mt5_adapter.py        # MT5 signal to CoinDCX order translator
├── examples/
│   └── mt5_signal.py         # End-to-end signal processing example
├── tests/
│   └── test_client.py        # Unit tests
├── hft-experiments/          # Low-latency research components
│   ├── rust-order-sender/    # Zero-copy binary UDP packet sender (Rust)
│   └── dpdk-settlement.c     # DPDK Ethernet fast-path order processor (C)
├── .env.example              # Environment variables template
├── pyproject.toml            # Package configuration
└── README.md
```

---

## 🛠️ Installation

Clone the repository and install in editable mode:

```bash
git clone https://github.com/your-username/coindcx-mt5-bridge.git
cd coindcx-mt5-bridge
pip install -e .
```

---

## ⚙️ Configuration

Copy the example environment file and set your CoinDCX API credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```env
COINDCX_API_KEY=your_coindcx_api_key
COINDCX_API_SECRET=your_coindcx_api_secret
```

> **Security Note:** Never commit your `.env` file or hardcode keys into source code.

---

## 💡 Usage Example

### 1. Simulated / Dry-Run Signal (Default)

```python
from coindcx_mt5 import CoinDCXClient, MT5OrderAdapter

# 1. Initialize client (dry_run mode is active by default)
client = CoinDCXClient()

# 2. Translate MT5 signal to CoinDCX order
adapter = MT5OrderAdapter()
order = adapter.convert_signal(
    symbol="BTCUSDT",
    side="buy",
    volume=0.005,
    order_type="market"
)

# 3. Process the order safely
result = client.place_order(order)
print("Dry run result:", result)
```

### 2. Live Execution (Explicit Confirmation Required)

```python
# Live trading requires explicit two-level confirmation
client = CoinDCXClient(live_trading=True)

# Level 1: client.live_trading == True
# Level 2: confirm_live == True on order placement
result = client.place_order(order, confirm_live=True)
print("Live order response:", result)
```

---

## 🧪 Running Tests

```bash
python -m unittest discover -s tests -v
```

---

## ⚡ HFT & Low-Latency Experiments (`hft-experiments/`)

- **Rust UDP Order Packet Generator**: Located in `hft-experiments/rust-order-sender`. Builds a fixed-point, 32-byte C-ABI compatible UDP binary payload with timestamped nonces for sub-microsecond serialization.
  ```bash
  cd hft-experiments/rust-order-sender
  cargo run --release
  ```
- **DPDK Kernel-Bypass Fast Path**: Located in `hft-experiments/dpdk-settlement.c`. Demonstrates DPDK `rte_eth_rx_burst` zero-copy packet ingestion and fixed-width order matching.

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
