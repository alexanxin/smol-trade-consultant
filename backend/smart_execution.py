"""
Smart Execution - Camouflaged order placement to avoid front-running.

Implements Samir Varma's principle: Liquidity is scarce, and predatory algorithms
hunt for obvious orders. Use "stupid" order sizes and non-round stop prices to
blend in with retail traders.

Strategy:
1. Use odd-lot sizes (96, 221, 347 shares) instead of round lots (100, 500)
2. Place stops at non-obvious prices ($99.73 instead of $100.00)
3. Avoid technical levels for stop placement
4. Make orders look retail, not institutional
"""

import logging
import random
from typing import Dict, Optional

logger = logging.getLogger("SmartExecution")


class SmartExecution:
    """
    Camouflaged order execution to avoid detection by predatory algorithms.
    
    Varma's insight: Retail stops are liquidity for institutions. By using
    non-standard order sizes and prices, we reduce the likelihood of being
    "front-run" or having our stops swept.
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize Smart Execution.
        
        Args:
            seed: Optional random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)
        
        logger.info("SmartExecution initialized")
    
    def generate_odd_lot_size(
        self,
        target_usd_amount: float,
        price: float,
        min_size: float = 0.01
    ) -> float:
        """
        Generate an odd-lot order size that looks retail.
        
        Args:
            target_usd_amount: Target position size in USD
            price: Current asset price
            min_size: Minimum order size (e.g., 0.01 SOL)
        
        Returns:
            Odd-lot size in asset units
        """
        # Calculate base size
        base_size = target_usd_amount / price
        
        # Generate a "stupid" multiplier (not 1.0, not 0.5, something weird)
        # Use prime-ish numbers or odd decimals
        stupid_multipliers = [0.96, 0.97, 0.98, 0.99, 1.01, 1.02, 1.03, 1.04]
        multiplier = random.choice(stupid_multipliers)
        
        # Apply multiplier
        odd_size = base_size * multiplier
        
        # Round to weird decimal places (not 2, use 3 or 4)
        decimal_places = random.choice([3, 4])
        odd_size = round(odd_size, decimal_places)
        
        # Ensure minimum size
        odd_size = max(odd_size, min_size)
        
        logger.debug(f"Odd-lot sizing: target=${target_usd_amount:.2f}, "
                    f"price=${price:.4f}, base={base_size:.4f}, "
                    f"multiplier={multiplier}, final={odd_size:.4f}")
        
        return odd_size
    
    def calculate_camouflaged_stop(
        self,
        entry_price: float,
        stop_loss_pct: float,
        direction: str = "long"
    ) -> float:
        """
        Calculate a camouflaged stop-loss price (non-round number).
        
        Args:
            entry_price: Entry price
            stop_loss_pct: Stop loss percentage (as decimal, e.g., 0.03 for 3%)
            direction: "long" or "short"
        
        Returns:
            Camouflaged stop price
        """
        # Calculate base stop price
        if direction.lower() == "long":
            base_stop = entry_price * (1 - stop_loss_pct)
        else:  # short
            base_stop = entry_price * (1 + stop_loss_pct)
        
        # Add random noise to avoid round numbers
        # Use prime numbers or weird decimals
        noise_pct = random.uniform(-0.003, 0.003)  # ±0.3% noise
        camouflaged_stop = base_stop * (1 + noise_pct)
        
        # Round to weird decimal places
        # Avoid .00, .25, .50, .75 endings
        decimal_places = random.choice([3, 4])
        camouflaged_stop = round(camouflaged_stop, decimal_places)
        
        logger.debug(f"Camouflaged stop: entry=${entry_price:.4f}, "
                    f"base_stop=${base_stop:.4f}, final=${camouflaged_stop:.4f}")
        
        return camouflaged_stop
    
    def generate_prime_like_number(self, target: float, tolerance: float = 0.05) -> float:
        """
        Generate a "prime-like" number near the target (looks weird/retail).
        
        Args:
            target: Target number
            tolerance: Acceptable deviation from target (as decimal)
        
        Returns:
            Prime-like number
        """
        # List of small primes and prime-like numbers
        prime_multipliers = [0.97, 0.991, 1.009, 1.03, 1.07, 1.11, 1.13]
        
        multiplier = random.choice(prime_multipliers)
        result = target * multiplier
        
        # Ensure within tolerance
        if abs(result - target) / target > tolerance:
            result = target * (1 + random.uniform(-tolerance, tolerance))
        
        return round(result, 4)
    
    def place_hidden_order(
        self,
        order_type: str,
        entry_price: float,
        position_size_usd: float,
        stop_loss_pct: float,
        take_profit_pct: Optional[float] = None
    ) -> Dict[str, any]:
        """
        Generate a camouflaged order with odd-lot sizing and hidden stops.
        
        Args:
            order_type: "BUY" or "SELL"
            entry_price: Entry price
            position_size_usd: Target position size in USD
            stop_loss_pct: Stop loss percentage (as decimal)
            take_profit_pct: Optional take profit percentage
        
        Returns:
            Dict with order parameters
        """
        # Generate odd-lot size
        asset_quantity = self.generate_odd_lot_size(position_size_usd, entry_price)
        
        # Calculate camouflaged stop
        direction = "long" if order_type.upper() == "BUY" else "short"
        stop_price = self.calculate_camouflaged_stop(entry_price, stop_loss_pct, direction)
        
        # Calculate take profit if specified
        take_profit_price = None
        if take_profit_pct is not None:
            if direction == "long":
                base_tp = entry_price * (1 + take_profit_pct)
            else:
                base_tp = entry_price * (1 - take_profit_pct)
            
            # Add noise to take profit too
            noise_pct = random.uniform(-0.002, 0.002)
            take_profit_price = round(base_tp * (1 + noise_pct), 4)
        
        order = {
            "order_type": order_type,
            "entry_price": entry_price,
            "asset_quantity": asset_quantity,
            "position_size_usd": asset_quantity * entry_price,  # Actual size after odd-lot
            "stop_loss": stop_price,
            "take_profit": take_profit_price,
            "execution_style": "camouflaged",
            "notes": "Odd-lot sizing and non-round stops to avoid detection"
        }
        
        tp_str = f"{take_profit_price:.4f}" if take_profit_price is not None else "None"
        logger.info(f"Hidden order: {order_type} {asset_quantity:.4f} @ ${entry_price:.4f}, "
                   f"SL=${stop_price:.4f}, TP=${tp_str}")
        
        return order
    
    def should_use_limit_order(self, volatility: float, threshold: float = 0.02) -> bool:
        """
        Determine if we should use limit order vs market order based on volatility.
        
        High volatility = use limit orders to avoid slippage.
        
        Args:
            volatility: Current volatility (as decimal, e.g., 0.05 for 5%)
            threshold: Volatility threshold for limit orders
        
        Returns:
            True if should use limit order
        """
        use_limit = volatility > threshold
        
        logger.debug(f"Order type decision: volatility={volatility*100:.2f}%, "
                    f"threshold={threshold*100:.2f}%, use_limit={use_limit}")
        
        return use_limit
