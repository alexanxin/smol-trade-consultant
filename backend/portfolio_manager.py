import sys
import os
from typing import List, Dict, Any
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import LifecycleDatabase
from backend.position_manager import Position

class PortfolioManager:
    """
    Manages the overall portfolio state, including:
    - Total Equity (Cash + Unrealized P&L)
    - Risk Exposure
    - Performance Metrics
    """
    
    def __init__(self, db_path: str = "trader_agent.db", max_portfolio_risk: float = 0.50):
        """
        Args:
            db_path: Path to SQLite database
            max_portfolio_risk: Maximum allowed risk exposure (e.g., 0.50 = 50% of equity)
        """
        self.db = LifecycleDatabase(db_path)
        self.max_portfolio_risk = max_portfolio_risk
        
        self.total_equity = 0.0
        self.cash_balance = 0.0
        self.unrealized_pnl = 0.0
        self.risk_exposure = 0.0
        
    def update_state(self, cash_balance: float, open_positions: List[Position]):
        """
        Update portfolio state based on current cash and open positions.
        """
        self.cash_balance = cash_balance
        
        # Calculate Unrealized P&L and Risk
        self.unrealized_pnl = 0.0
        total_position_value = 0.0
        
        for pos in open_positions:
            if pos.unrealized_pnl is not None:
                self.unrealized_pnl += pos.unrealized_pnl
            
            # Calculate current value of position
            if pos.current_price and pos.entry_amount:
                total_position_value += pos.current_price * pos.entry_amount
            elif pos.entry_price and pos.entry_amount:
                # Fallback to entry value if current price unknown
                total_position_value += pos.entry_price * pos.entry_amount
                
        self.total_equity = self.cash_balance + total_position_value
        
        # Calculate Risk Exposure (Total Position Value / Total Equity)
        if self.total_equity > 0:
            self.risk_exposure = total_position_value / self.total_equity
        else:
            self.risk_exposure = 0.0
            
        # Save snapshot
        self.db.save_portfolio_snapshot(
            self.total_equity,
            self.cash_balance,
            self.unrealized_pnl,
            len(open_positions),
            self.risk_exposure
        )
        
        print(f"[PortfolioManager] Equity: ${self.total_equity:.2f} | P&L: ${self.unrealized_pnl:.2f} | Risk: {self.risk_exposure*100:.1f}%")

    def check_trade_risk(self, estimated_trade_value: float) -> bool:
        """
        Check if a new trade would breach portfolio risk limits.
        """
        if self.total_equity == 0:
            return True # Allow first trade to establish equity? Or block? 
            # If equity is 0, we probably haven't initialized properly or are broke.
            # Let's assume cash_balance is the limit.
            return estimated_trade_value <= self.cash_balance

        projected_exposure = (self.risk_exposure * self.total_equity + estimated_trade_value) / self.total_equity
        
        if projected_exposure > self.max_portfolio_risk:
            print(f"[PortfolioManager] Risk Check FAILED: Projected exposure {projected_exposure*100:.1f}% > Limit {self.max_portfolio_risk*100:.1f}%")
            return False
            
        return True

    def get_summary(self) -> Dict[str, Any]:
        """Return a summary of the portfolio state."""
        return {
            "total_equity": self.total_equity,
            "cash_balance": self.cash_balance,
            "unrealized_pnl": self.unrealized_pnl,
            "risk_exposure": self.risk_exposure,
            "max_risk": self.max_portfolio_risk
        }
