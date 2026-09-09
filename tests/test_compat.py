import unittest
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from coindcx_mt5 import (
    mt5,
    initialize,
    copy_rates_from_pos,
    copy_rates_range,
    symbol_info_tick,
    symbol_info,
    order_send,
    order_check,
    positions_get,
    positions_total,
    account_info,
    set_live_trading,
    is_live_trading,
    set_symbol_map,
    set_default_market,
    normalize_symbol,
    TIMEFRAME_M15,
    TIMEFRAME_H1,
    ORDER_TYPE_BUY,
    ORDER_TYPE_SELL,
    TRADE_ACTION_DEAL,
    TRADE_RETCODE_DONE,
    TRADE_RETCODE_INVALID,
    POSITION_TYPE_BUY,
)


class TestMT5CompatibilityBridge(unittest.TestCase):
    def setUp(self):
        # Always ensure dry-run mode for tests
        set_live_trading(False)
        set_default_market("futures")
        initialize()

    def test_initialization_and_version(self):
        self.assertTrue(initialize())
        v = mt5.version()
        self.assertIsInstance(v, tuple)
        self.assertEqual(len(v), 3)
        self.assertEqual(v[0], 500)

        err_code, err_msg = mt5.last_error()
        self.assertIsInstance(err_code, int)
        self.assertIsInstance(err_msg, str)

    def test_symbol_normalization(self):
        # Futures mode (default)
        self.assertEqual(normalize_symbol("BTCUSD"), "B-BTC_USDT")
        self.assertEqual(normalize_symbol("BTCUSDT"), "B-BTC_USDT")
        self.assertEqual(normalize_symbol("B-BTC_USDT"), "B-BTC_USDT")
        self.assertEqual(normalize_symbol("ETH/USDT"), "B-ETH_USDT")
        self.assertEqual(normalize_symbol("SOL-USD"), "B-SOL_USDT")

        # Custom mappings
        set_symbol_map({"CRYPTO_INDEX": "B-BTC_USDT", "CUSTOM_COIN": "B-ETH_USDT"})
        self.assertEqual(normalize_symbol("CRYPTO_INDEX"), "B-BTC_USDT")
        self.assertEqual(normalize_symbol("CUSTOM_COIN"), "B-ETH_USDT")

        # Spot mode
        set_default_market("spot")
        self.assertEqual(normalize_symbol("BTCUSD"), "BTCUSDT")
        self.assertEqual(normalize_symbol("BTCUSDT"), "BTCUSDT")

        # Reset back to futures
        set_default_market("futures")

    def test_symbol_info_tick(self):
        tick = symbol_info_tick("BTCUSD")
        self.assertIsNotNone(tick, "Tick for BTCUSD should not be None")
        self.assertGreater(tick.bid, 0.0)
        self.assertGreater(tick.ask, 0.0)
        self.assertGreaterEqual(tick.ask, tick.bid)
        self.assertGreater(tick.time, 0)
        self.assertGreater(tick.time_msc, 0)

    def test_symbol_info(self):
        info = symbol_info("BTCUSD")
        self.assertIsNotNone(info)
        self.assertEqual(info.name, "BTCUSD")
        self.assertGreater(info.bid, 0.0)
        self.assertGreater(info.ask, 0.0)
        self.assertIn(info.currency_profit, ("USDT", "INR", "USD"))
        self.assertEqual(info.trade_contract_size, 1.0)

    def test_copy_rates_from_pos_and_pandas(self):
        count = 15
        rates = copy_rates_from_pos("BTCUSD", TIMEFRAME_M15, 0, count)
        self.assertIsNotNone(rates, "Rates should not be None")
        self.assertIsInstance(rates, np.ndarray)
        self.assertEqual(len(rates), count)

        # Check structured array field names
        expected_fields = ("time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume")
        self.assertEqual(rates.dtype.names, expected_fields)

        # Ensure close prices are positive numbers
        self.assertTrue(np.all(rates["close"] > 0))
        self.assertTrue(np.all(rates["high"] >= rates["low"]))

        # Check Pandas DataFrame integration (crucial for algorithmic traders)
        df = pd.DataFrame(rates)
        self.assertEqual(len(df), count)
        for col in expected_fields:
            self.assertIn(col, df.columns)

        # Can calculate technical indicator like SMA
        sma = df["close"].rolling(window=3).mean()
        self.assertEqual(len(sma), count)

    def test_order_check(self):
        valid_request = {
            "action": TRADE_ACTION_DEAL,
            "symbol": "BTCUSD",
            "volume": 0.01,
            "type": ORDER_TYPE_BUY,
            "price": 60000.0,
        }
        res = order_check(valid_request)
        self.assertEqual(res.retcode, 0)
        self.assertEqual(res.comment, "Done")

        # Invalid volume
        invalid_vol_req = valid_request.copy()
        invalid_vol_req["volume"] = 0
        res_invalid = order_check(invalid_vol_req)
        self.assertNotEqual(res_invalid.retcode, 0)

    def test_order_send_and_positions_dry_run(self):
        self.assertFalse(is_live_trading())

        # 1. Place a BUY order
        buy_req = {
            "action": TRADE_ACTION_DEAL,
            "symbol": "BTCUSD",
            "volume": 0.002,
            "type": ORDER_TYPE_BUY,
            "magic": 123456,
            "comment": "Test Buy Order",
        }
        res = order_send(buy_req)
        self.assertEqual(res.retcode, TRADE_RETCODE_DONE)
        self.assertGreater(res.deal, 0)
        self.assertGreater(res.order, 0)
        ticket = res.order

        # 2. Verify position in positions_get()
        positions = positions_get(symbol="BTCUSD")
        self.assertGreaterEqual(len(positions), 1)

        pos = next((p for p in positions if p.ticket == ticket), None)
        self.assertIsNotNone(pos, f"Position #{ticket} must exist")
        self.assertEqual(pos.volume, 0.002)
        self.assertEqual(pos.type, POSITION_TYPE_BUY)
        self.assertEqual(pos.magic, 123456)
        self.assertGreater(pos.price_current, 0.0)

        # 3. Close the position
        close_req = {
            "action": TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": "BTCUSD",
            "volume": 0.002,
            "type": ORDER_TYPE_SELL,
            "comment": "Close Position",
        }
        close_res = order_send(close_req)
        self.assertEqual(close_res.retcode, TRADE_RETCODE_DONE)

        # 4. Verify position is removed
        positions_after = positions_get(symbol="BTCUSD")
        pos_after = next((p for p in positions_after if p.ticket == ticket), None)
        self.assertIsNone(pos_after, "Position should be closed and removed")

    def test_account_info(self):
        acc = account_info()
        self.assertIsNotNone(acc)
        self.assertGreater(acc.balance, 0.0)
        self.assertGreater(acc.equity, 0.0)
        self.assertEqual(acc.currency, "USDT")
        self.assertTrue(acc.trade_allowed)
        self.assertTrue(acc.trade_expert)


if __name__ == "__main__":
    unittest.main()
