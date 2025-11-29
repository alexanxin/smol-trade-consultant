import sqlite3
import os
from database import LifecycleDatabase

# Use a test database file
TEST_DB = "test_trader_agent.db"
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

def test_signal_logging():
    print(f"Testing signal logging with DB: {TEST_DB}")
    
    # Initialize DB
    db = LifecycleDatabase(db_path=TEST_DB)
    
    # Mock signal data
    mock_signal = {
        "action": "HOLD",
        "entry_price": 100.0,
        "stop_loss": 90.0,
        "take_profit": 120.0,
        "conviction_score": 85,
        "reasoning": "Market is choppy, waiting for breakout.",
        "some_extra_data": "test"
    }
    
    mock_risk = {
        "approved": False,
        "critique": "Too risky"
    }
    
    # Save signal
    print("Saving mock signal...")
    db.save_signal("SOL", mock_signal, mock_risk, status="REJECTED")
    
    # Verify
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM signals")
    rows = cursor.fetchall()
    conn.close()
    
    if len(rows) == 1:
        print("✅ Signal saved successfully!")
        print(f"Row: {rows[0]}")
    else:
        print(f"❌ Failed to save signal. Rows found: {len(rows)}")

    # Clean up
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

if __name__ == "__main__":
    test_signal_logging()
