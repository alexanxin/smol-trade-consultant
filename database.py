import sqlite3
import json
from datetime import datetime
import os

class LifecycleDatabase:
    def __init__(self, db_path="trader_agent.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database and create tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                status TEXT NOT NULL, -- 'OPEN', 'CLOSED'
                timestamp TEXT NOT NULL,
                strategy_output TEXT, -- JSON string
                risk_assessment TEXT, -- JSON string
                exit_price REAL,
                exit_reason TEXT,
                exit_timestamp TEXT,
                -- Phase 5: Position tracking fields
                token_address TEXT,
                entry_amount REAL,
                current_price REAL,
                unrealized_pnl REAL,
                last_check_timestamp TEXT,
                trailing_stop_price REAL,
                execution_mode TEXT -- 'spot' or 'leverage'
            )
        ''')
        
        # Create signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                confidence REAL,
                reasoning TEXT,
                strategy_output TEXT, -- JSON string
                risk_assessment TEXT, -- JSON string
                status TEXT -- 'PENDING', 'EXECUTED', 'REJECTED', 'SKIPPED'
            )
        ''')

        # Create portfolio_snapshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_equity REAL,
                cash_balance REAL,
                unrealized_pnl REAL,
                open_positions_count INTEGER,
                risk_exposure REAL
            )
        ''')
        
        conn.commit()
        conn.close()

    def get_active_trade(self):
        """Retrieve the currently active trade, if any."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM trades WHERE status = 'OPEN' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return dict(row)
        return None

    def add_trade(self, symbol, entry_price, stop_loss, take_profit, strategy_output, risk_assessment):
        """Add a new trade to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO trades (symbol, entry_price, stop_loss, take_profit, status, timestamp, strategy_output, risk_assessment)
            VALUES (?, ?, ?, ?, 'OPEN', ?, ?, ?)
        ''', (
            symbol, 
            entry_price, 
            stop_loss, 
            take_profit, 
            timestamp, 
            json.dumps(strategy_output) if isinstance(strategy_output, dict) else strategy_output,
            json.dumps(risk_assessment) if isinstance(risk_assessment, dict) else risk_assessment
        ))
        
        conn.commit()
        trade_id = cursor.lastrowid
        conn.close()
        return trade_id

    def save_signal(self, symbol, signal_data, risk_assessment=None, status="SKIPPED"):
        """Save a generated signal to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        # Extract fields safely
        action = signal_data.get('action', 'UNKNOWN')
        entry_price = signal_data.get('entry_price')
        stop_loss = signal_data.get('stop_loss')
        take_profit = signal_data.get('take_profit')
        confidence = signal_data.get('conviction_score') or signal_data.get('confidence')
        reasoning = signal_data.get('reasoning')
        
        cursor.execute('''
            INSERT INTO signals (
                timestamp, symbol, action, entry_price, stop_loss, take_profit, 
                confidence, reasoning, strategy_output, risk_assessment, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp,
            symbol,
            action,
            entry_price,
            stop_loss,
            take_profit,
            confidence,
            reasoning,
            json.dumps(signal_data) if isinstance(signal_data, dict) else str(signal_data),
            json.dumps(risk_assessment) if isinstance(risk_assessment, dict) else str(risk_assessment),
            status
        ))
        
        conn.commit()
        conn.close()

    def close_trade(self, trade_id, exit_price, exit_reason):
        """Close an active trade."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        exit_timestamp = datetime.now().isoformat()
        
        cursor.execute('''
            UPDATE trades 
            SET status = 'CLOSED', exit_price = ?, exit_reason = ?, exit_timestamp = ?
            WHERE id = ?
        ''', (exit_price, exit_reason, exit_timestamp, trade_id))
        
        conn.commit()
        conn.close()

    def update_trade(self, trade_id, **kwargs):
        """Update specific fields of a trade."""
        if not kwargs:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [trade_id]
        
        cursor.execute(f'''
            UPDATE trades 
            SET {set_clause}
            WHERE id = ?
        ''', values)
        
        conn.commit()
        conn.close()

    def get_open_positions(self):
        """Retrieve all open positions."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM trades WHERE status = 'OPEN' ORDER BY id ASC")
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]

    def update_position_price(self, trade_id, current_price, unrealized_pnl):
        """Update position with current price and P&L."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        last_check = datetime.now().isoformat()
        
        cursor.execute('''
            UPDATE trades 
            SET current_price = ?, unrealized_pnl = ?, last_check_timestamp = ?
            WHERE id = ?
        ''', (current_price, unrealized_pnl, last_check, trade_id))
        
        conn.commit()
        conn.close()

    def update_trailing_stop(self, trade_id, new_stop_price):
        """Update trailing stop price for a position."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE trades 
            SET trailing_stop_price = ?, stop_loss = ?
            WHERE id = ?
        ''', (new_stop_price, new_stop_price, trade_id))
        
        conn.commit()
        conn.close()

    def save_portfolio_snapshot(self, total_equity, cash_balance, unrealized_pnl, open_positions_count, risk_exposure):
        """Save a snapshot of the portfolio state."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO portfolio_snapshots (timestamp, total_equity, cash_balance, unrealized_pnl, open_positions_count, risk_exposure)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), total_equity, cash_balance, unrealized_pnl, open_positions_count, risk_exposure))
        conn.commit()
        conn.close()

    def get_positions_by_status(self, status):
        """Get positions by status."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM trades WHERE status = ? ORDER BY id ASC", (status,))
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]
