from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import LifecycleDatabase


@dataclass
class Position:
    """Represents an active trading position."""
    trade_id: int
    symbol: str
    token_address: str
    entry_price: float
    entry_amount: float
    stop_loss: float
    take_profit: float
    execution_mode: str  # 'spot' or 'leverage'
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    trailing_stop_enabled: bool = False
    trailing_stop_distance: float = 0.02  # 2% default
    trailing_stop_price: Optional[float] = None
    timestamp: Optional[str] = None
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Position':
        """Create Position from database row."""
        return cls(
            trade_id=row['id'],
            symbol=row['symbol'],
            token_address=row.get('token_address', ''),
            entry_price=row['entry_price'],
            entry_amount=row.get('entry_amount', 0.0),
            stop_loss=row['stop_loss'],
            take_profit=row['take_profit'],
            execution_mode=row.get('execution_mode', 'spot'),
            current_price=row.get('current_price'),
            unrealized_pnl=row.get('unrealized_pnl'),
            trailing_stop_price=row.get('trailing_stop_price'),
            timestamp=row.get('timestamp')
        )
    
    def calculate_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L."""
        if self.execution_mode == 'spot':
            # Spot: P&L = (current_price - entry_price) * entry_amount
            return (current_price - self.entry_price) * self.entry_amount
        else:
            # Leverage: Similar calculation (simplified)
            return (current_price - self.entry_price) * self.entry_amount
    
    def calculate_pnl_percentage(self, current_price: float) -> float:
        """Calculate P&L as percentage."""
        if self.entry_price == 0:
            return 0.0
        return ((current_price - self.entry_price) / self.entry_price) * 100
    
    def should_exit_stop_loss(self, current_price: float) -> bool:
        """Check if stop-loss should be triggered."""
        return current_price <= self.stop_loss
    
    def should_exit_take_profit(self, current_price: float) -> bool:
        """Check if take-profit should be triggered."""
        return current_price >= self.take_profit
    
    def update_trailing_stop(self, current_price: float) -> Optional[float]:
        """
        Update trailing stop if price moved favorably.
        Returns new stop price if updated, None otherwise.
        """
        if not self.trailing_stop_enabled:
            return None
        
        # Calculate trailing stop price
        new_trailing_stop = current_price * (1 - self.trailing_stop_distance)
        
        # Only update if new stop is higher than current stop (for long positions)
        if new_trailing_stop > self.stop_loss:
            self.trailing_stop_price = new_trailing_stop
            self.stop_loss = new_trailing_stop
            return new_trailing_stop
        
        return None


class PositionManager:
    """Manages all active trading positions."""
    
    def __init__(self, db_path: str = "trader_agent.db"):
        self.db = LifecycleDatabase(db_path)
        self.positions: Dict[int, Position] = {}
        self.load_positions()
    
    def load_positions(self):
        """Load all open positions from database."""
        open_trades = self.db.get_open_positions()
        self.positions = {}
        
        for trade in open_trades:
            position = Position.from_db_row(trade)
            self.positions[position.trade_id] = position
        
        print(f"[PositionManager] Loaded {len(self.positions)} open positions")

    def refresh_positions(self):
        """Force refresh of positions from database."""
        self.load_positions()
    
    def add_position(self, trade_data: Dict[str, Any], execution_result: Dict[str, Any], 
                    token: str, token_address: str) -> Position:
        """
        Register a new position after successful trade execution.
        
        Args:
            trade_data: Decision data from MasterTrader
            execution_result: Result from ExecutionEngine
            token: Token symbol
            token_address: Token contract address
        """
        plan = trade_data.get('plan', {})
        
        # Add trade to database
        trade_id = self.db.add_trade(
            symbol=token,
            entry_price=plan.get('entry'),
            stop_loss=plan.get('stop_loss'),
            take_profit=plan.get('take_profit'),
            strategy_output=trade_data,
            risk_assessment={}
        )
        
        # Update with position-specific fields
        self.db.update_trade(
            trade_id,
            token_address=token_address,
            entry_amount=execution_result.get('amount', 0.0),
            execution_mode=execution_result.get('mode', 'spot'),
            current_price=plan.get('entry')
        )
        
        # Create Position object
        position = Position(
            trade_id=trade_id,
            symbol=token,
            token_address=token_address,
            entry_price=plan.get('entry'),
            entry_amount=execution_result.get('amount', 0.0),
            stop_loss=plan.get('stop_loss'),
            take_profit=plan.get('take_profit'),
            execution_mode=execution_result.get('mode', 'spot'),
            current_price=plan.get('entry'),
            timestamp=datetime.now().isoformat()
        )
        
        self.positions[trade_id] = position
        
        print(f"[PositionManager] Added position {trade_id} for {token}")
        print(f"   Entry: ${position.entry_price:.4f}, SL: ${position.stop_loss:.4f}, TP: ${position.take_profit:.4f}")
        
        return position
    
    def remove_position(self, trade_id: int):
        """Remove a closed position."""
        if trade_id in self.positions:
            del self.positions[trade_id]
            print(f"[PositionManager] Removed position {trade_id}")
    
    def get_position(self, trade_id: int) -> Optional[Position]:
        """Retrieve a position by trade ID."""
        return self.positions.get(trade_id)
    
    def get_all_positions(self) -> List[Position]:
        """Get all active positions."""
        return list(self.positions.values())
    
    def update_position_price(self, trade_id: int, current_price: float):
        """Update position with current price and calculate P&L."""
        position = self.positions.get(trade_id)
        if not position:
            return
        
        position.current_price = current_price
        position.unrealized_pnl = position.calculate_pnl(current_price)
        
        # Update database
        self.db.update_position_price(trade_id, current_price, position.unrealized_pnl)
        
        # Check and update trailing stop
        if position.trailing_stop_enabled:
            new_stop = position.update_trailing_stop(current_price)
            if new_stop:
                self.db.update_trailing_stop(trade_id, new_stop)
                print(f"[PositionManager] Updated trailing stop for {trade_id}: ${new_stop:.4f}")
    
    def check_exit_conditions(self, position: Position) -> Optional[str]:
        """
        Check if position should be exited.
        Returns exit reason if exit needed, None otherwise.
        """
        if not position.current_price:
            return None
        
        # Check stop-loss
        if position.should_exit_stop_loss(position.current_price):
            pnl_pct = position.calculate_pnl_percentage(position.current_price)
            return f"STOP_LOSS (P&L: {pnl_pct:.2f}%)"
        
        # Check take-profit
        if position.should_exit_take_profit(position.current_price):
            pnl_pct = position.calculate_pnl_percentage(position.current_price)
            return f"TAKE_PROFIT (P&L: {pnl_pct:.2f}%)"
        
        return None
    
    def close_position(self, trade_id: int, exit_price: float, exit_reason: str):
        """Close a position and update database."""
        self.db.close_trade(trade_id, exit_price, exit_reason)
        self.remove_position(trade_id)
        
        print(f"[PositionManager] Closed position {trade_id}: {exit_reason}")
