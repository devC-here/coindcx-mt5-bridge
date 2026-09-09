import hashlib
import hmac
import json
import unittest
from coindcx_mt5 import CoinDCXClient, MT5OrderAdapter, OrderRequest, OrderType, Side
from coindcx_mt5.client import CoinDCXError

class CoinDCXClientTests(unittest.TestCase):
    def test_dry_run_never_calls_network(self):
        result = CoinDCXClient().place_order(OrderRequest("B-BTC_USDT", Side.BUY, OrderType.LIMIT, "0.01", "6000000"))
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["payload"]["price_per_unit"], "6000000")
    def test_signature_matches_exact_sent_body(self):
        captured = {}
        def transport(url, body, headers, timeout):
            captured.update(body=body, headers=headers)
            return 200, b'[]'
        CoinDCXClient("key", "secret", live_trading=True, transport=transport).balances()
        expected = hmac.new(b"secret", captured["body"], hashlib.sha256).hexdigest()
        self.assertEqual(captured["headers"]["X-AUTH-SIGNATURE"], expected)
        self.assertIsInstance(json.loads(captured["body"]), dict)
    def test_live_order_requires_explicit_confirmation(self):
        order = OrderRequest("B-BTC_USDT", Side.BUY, OrderType.MARKET, "0.01")
        with self.assertRaises(CoinDCXError): CoinDCXClient("key", "secret", live_trading=True).place_order(order)
    def test_mt5_adapter(self):
        order = MT5OrderAdapter({"BTCUSD": "B-BTC_USDT"}).to_coindcx({"symbol": "BTCUSD", "type": 0, "volume": "0.01", "price": "6000000"})
        self.assertEqual((order.market, order.side), ("B-BTC_USDT", Side.BUY))
if __name__ == "__main__": unittest.main()
