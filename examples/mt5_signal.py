"""MT5-style signal to CoinDCX. It remains dry-run by default."""
from coindcx_mt5 import CoinDCXClient, MT5OrderAdapter

adapter = MT5OrderAdapter({"BTCUSD": "B-BTC_USDT"})
signal = {"symbol": "BTCUSD", "type": "BUY", "volume": "0.0001", "price": "6000000"}
print(CoinDCXClient().place_order(adapter.to_coindcx(signal)))
