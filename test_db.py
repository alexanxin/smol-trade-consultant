import unittest
import os
import sqlite3
import json
from database import LifecycleDatabase

class TestLifecycleDatabase(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_trader_agent.db"
        self.db = LifecycleDatabase(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_add_and_get_trade(self):
        trade_id = self.db.add_trade(
            symbol="SOL",
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            strategy_output={"action": "BUY"},
            risk_assessment={"approved": True}
        )
        
        active_trade = self.db.get_active_trade()
        self.assertIsNotNone(active_trade)
        self.assertEqual(active_trade['symbol'], "SOL")
        self.assertEqual(active_trade['entry_price'], 100.0)
        self.assertEqual(active_trade['status'], "OPEN")

    def test_close_trade(self):
        trade_id = self.db.add_trade(
            symbol="ETH",
            entry_price=2000.0,
            stop_loss=1900.0,
            take_profit=2200.0,
            strategy_output={"action": "BUY"},
            risk_assessment={"approved": True}
        )
        
        self.db.close_trade(trade_id, 2200.0, "Take Profit Hit")
        
        active_trade = self.db.get_active_trade()
        self.assertIsNone(active_trade)
        
        # Verify it's closed in DB
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT status, exit_price FROM trades WHERE id = ?", (trade_id,))
        row = cursor.fetchone()
        conn.close()
        
        self.assertEqual(row[0], "CLOSED")
        self.assertEqual(row[1], 2200.0)

if __name__ == '__main__':
    unittest.main()
