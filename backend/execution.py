import os
import sys
from typing import Dict, Any

# Add parent directory to path to import wallet and client modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("[DEBUG] execution.py: About to import wallet/client modules", flush=True)
from wallet_manager import SolanaWallet
from jupiter_client import JupiterClient
# from drift_client_wrapper import DriftClientWrapper
print("[DEBUG] execution.py: Imports successful", flush=True)

class ExecutionEngine:
    def __init__(self, mode: str = "spot", dry_run: bool = True):
        """
        Initialize ExecutionEngine.
        mode: "spot" or "leverage"
        dry_run: If True, simulate execution without actual trades
        """
        print(f"[DEBUG] ExecutionEngine.__init__ called with mode={mode}, dry_run={dry_run}", flush=True)
        self.mode = mode
        self.dry_run = dry_run
        
        print(f"[DEBUG] Initializing SolanaWallet...", flush=True)
        self.wallet = SolanaWallet()
        print(f"[DEBUG] SolanaWallet initialized", flush=True)
        
        if mode == "spot":
            print(f"[DEBUG] Initializing JupiterClient...", flush=True)
            self.jupiter = JupiterClient(self.wallet)
            print(f"[DEBUG] JupiterClient initialized", flush=True)
        elif mode == "leverage":
            # print(f"[DEBUG] Initializing DriftClientWrapper...", flush=True)
            # self.drift = DriftClientWrapper()
            # print(f"[DEBUG] DriftClientWrapper initialized", flush=True)
            raise ValueError("Leverage mode disabled due to missing dependencies")
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'spot' or 'leverage'")
            
        print(f"[ExecutionEngine] Initialized in {mode.upper()} mode (dry_run={dry_run})", flush=True)

    async def get_cash_balance(self) -> float:
        """Get current cash (USDC) balance."""
        if self.dry_run:
            return 1000.0 # Mock balance
            
        # USDC Mint Address
        USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        return self.wallet.get_token_balance(USDC_MINT)

    async def execute_decision(self, decision: Dict[str, Any], token: str, chain: str = "solana") -> Dict[str, Any]:
        """
        Execute the Master Trader's decision.
        """
        action = decision.get("action")
        plan = decision.get("plan") or {}  # Handle None plan
        kelly_size = plan.get("position_size_pct", 0.10)  # Default 10%
        
        print(f"\n[ExecutionEngine] Processing {action} decision for {token}")
        print(f"[ExecutionEngine] Kelly Size: {kelly_size*100:.2f}%")
        
        if self.dry_run:
            print(f"[ExecutionEngine] DRY RUN MODE - No actual execution")
            return {
                "status": "simulated",
                "action": action,
                "token": token,
                "size_pct": kelly_size
            }
        
        # Check wallet
        if not self.wallet.keypair:
            return {"error": "No wallet configured. Set SOLANA_PRIVATE_KEY in .env"}
        
        # Execute based on action
        if action == "BUY":
            if self.mode == "spot":
                return await self._execute_spot_buy(token, kelly_size)
            elif self.mode == "leverage":
                return await self._execute_leverage_open(token, "LONG", kelly_size, plan)
        elif action == "SELL":
            if self.mode == "spot":
                return await self._execute_spot_sell(token, kelly_size)
            elif self.mode == "leverage":
                return await self._execute_leverage_open(token, "SHORT", kelly_size, plan)
        elif action == "HOLD":
            print(f"[ExecutionEngine] HOLD - No execution needed")
            return {"status": "hold"}
        else:
            return {"error": f"Unknown action: {action}"}

    async def _execute_spot_buy(self, token: str, kelly_size: float) -> Dict[str, Any]:
        """
        Execute spot buy via Jupiter.
        For SOL: USDC -> SOL
        For other tokens: SOL -> Token
        """
        print(f"[ExecutionEngine] Executing SPOT BUY for {token}")

        # Get token address first
        from trader_agent_core import TraderAgent
        agent = TraderAgent()
        token_address = await agent._get_token_address(token, "solana")

        if not token_address:
            return {"error": f"Could not find address for {token}"}

        # Determine input currency and balance
        if token == "SOL":
            # Buy SOL using USDC
            input_mint = self.jupiter.USDC_MINT
            input_symbol = "USDC"
            input_decimals = 6  # USDC has 6 decimals

            # Get USDC balance
            usdc_balance = self.wallet.get_token_balance(input_mint)
            available_balance = usdc_balance / (10 ** input_decimals)  # Convert to USDC units

            if available_balance <= 1:  # Keep some USDC
                return {"error": f"Insufficient USDC balance: {available_balance} USDC"}

            # Calculate amount to spend (Kelly size of available balance)
            amount_to_spend = (available_balance - 1) * kelly_size
            amount_units = int(amount_to_spend * (10 ** input_decimals))  # Convert to atomic units

            print(f"[ExecutionEngine] USDC Balance: {available_balance}")
            print(f"[ExecutionEngine] Spending {amount_to_spend:.2f} USDC ({kelly_size*100:.1f}% of balance)")

            output_mint = self.jupiter.SOL_MINT
        else:
            # Buy other tokens using SOL
            input_mint = self.jupiter.SOL_MINT
            input_symbol = "SOL"
            input_decimals = 9  # SOL has 9 decimals

            # Get SOL balance
            sol_balance = self.wallet.get_balance()
            print(f"[ExecutionEngine] SOL Balance: {sol_balance}")

            if sol_balance <= 0.01:  # Keep 0.01 SOL for fees
                return {"error": "Insufficient SOL balance for trade + fees"}

            # Calculate amount to spend (Kelly size of available balance)
            amount_to_spend = (sol_balance - 0.01) * kelly_size
            amount_units = int(amount_to_spend * (10 ** input_decimals))  # Convert to lamports

            print(f"[ExecutionEngine] Spending {amount_to_spend:.4f} SOL ({kelly_size*100:.1f}% of balance)")

            output_mint = token_address

        # Execute swap
        result = self.jupiter.execute_swap(
            input_mint=input_mint,
            output_mint=output_mint,
            amount=amount_units,
            slippage_bps=100  # 1% slippage
        )

        return result

    async def _execute_spot_sell(self, token: str, kelly_size: float) -> Dict[str, Any]:
        """
        Execute spot sell via Jupiter.
        For SOL: SOL -> USDC
        For other tokens: Token -> SOL
        """
        print(f"[ExecutionEngine] Executing SPOT SELL for {token}")

        # Get token address
        from trader_agent_core import TraderAgent
        agent = TraderAgent()
        token_address = await agent._get_token_address(token, "solana")

        if not token_address:
            return {"error": f"Could not find address for {token}"}

        # Determine output currency
        if token == "SOL":
            # Sell SOL for USDC
            input_mint = self.jupiter.SOL_MINT
            output_mint = self.jupiter.USDC_MINT
            input_decimals = 9  # SOL has 9 decimals

            # Get SOL balance
            sol_balance = self.wallet.get_balance()
            available_balance = sol_balance

            if available_balance <= 0.01:  # Keep some SOL for fees
                return {"error": f"Insufficient SOL balance: {available_balance} SOL"}

            # SELL 100% of available balance (minus gas reserve)
            amount_to_sell = available_balance - 0.01  # Keep 0.01 SOL for gas
            amount_units = int(amount_to_sell * (10 ** input_decimals))  # Convert to lamports

            print(f"[ExecutionEngine] SOL Balance: {available_balance}")
            print(f"[ExecutionEngine] Selling {amount_to_sell:.4f} SOL (100% of available balance)")

        else:
            # Sell other tokens for SOL
            input_mint = token_address
            output_mint = self.jupiter.SOL_MINT

            # Get token balance
            token_balance = self.wallet.get_token_balance(token_address)

            if token_balance <= 0:
                return {"error": f"No {token} balance to sell"}

            # SELL 100% of token balance
            amount_units = int(token_balance)

            print(f"[ExecutionEngine] Selling {amount_units} units (100% of holdings)")

        # Execute swap
        result = self.jupiter.execute_swap(
            input_mint=input_mint,
            output_mint=output_mint,
            amount=amount_units,
            slippage_bps=100  # 1% slippage
        )

        return result

    async def _execute_leverage_open(self, token: str, direction: str, kelly_size: float, plan: Dict) -> Dict[str, Any]:
        """
        Execute leverage position via Drift.
        """
        # print(f"[ExecutionEngine] Executing LEVERAGE {direction} for {token}")
        
        # For leverage, kelly_size determines the size relative to our collateral or buying power.
        # Simplified: Use kelly_size * available_balance as the margin/notional?
        # Let's assume kelly_size is the % of portfolio to risk/use.
        
        # Get SOL balance (collateral)
        # sol_balance = self.wallet.get_balance()
        
        # Calculate size in SOL
        # Note: Drift open_position expects amount in SOL (notional)
        # If we want 1x leverage with 10% of portfolio, size = 0.1 * balance
        # If we want 5x leverage with 10% of portfolio, size = 0.1 * balance * 5
        
        # leverage_multiplier = plan.get("leverage", 1.0)
        # amount_sol = sol_balance * kelly_size * leverage_multiplier
        
        # print(f"[ExecutionEngine] Collateral: {sol_balance:.4f} SOL")
        # print(f"[ExecutionEngine] Position Size: {amount_sol:.4f} SOL (Lev: {leverage_multiplier}x)")
        
        # return await self.drift.open_position(token, direction, amount_sol, leverage_multiplier)
        return {"error": "Leverage mode disabled"}

    async def close_position(self, token: str) -> Dict[str, Any]:
        """
        Close an existing position (leverage only).
        """
        if self.mode != "leverage":
            return {"error": "Close position only available in leverage mode"}
            
        # return await self.drift.close_position(token)
        return {"error": "Leverage mode disabled"}
