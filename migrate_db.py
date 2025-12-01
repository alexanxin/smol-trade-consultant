#!/usr/bin/env python3
"""
Database migration script for Phase 5: Position Management
Adds new columns to the trades table for position tracking.
"""

import sqlite3
import os

DB_PATH = "trader_agent.db"

def migrate_database():
    """Add Phase 5 columns to existing database."""
    
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} does not exist. No migration needed.")
        return
    
    print(f"Migrating database: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(trades)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    # Define new columns to add
    new_columns = {
        'token_address': 'TEXT',
        'entry_amount': 'REAL',
        'current_price': 'REAL',
        'unrealized_pnl': 'REAL',
        'last_check_timestamp': 'TEXT',
        'trailing_stop_price': 'REAL',
        'execution_mode': 'TEXT'
    }
    
    # Add missing columns
    added_count = 0
    for column_name, column_type in new_columns.items():
        if column_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE trades ADD COLUMN {column_name} {column_type}")
                print(f"✅ Added column: {column_name} ({column_type})")
                added_count += 1
            except sqlite3.OperationalError as e:
                print(f"⚠️  Could not add {column_name}: {e}")
        else:
            print(f"ℹ️  Column already exists: {column_name}")
    
    conn.commit()
    conn.close()
    
    if added_count > 0:
        print(f"\n✅ Migration complete! Added {added_count} column(s).")
    else:
        print(f"\n✅ Database already up to date.")

if __name__ == "__main__":
    migrate_database()
