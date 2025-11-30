import os
import sys
from typing import Dict, Any

# Add parent directory to path to import wallet and client modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("[DEBUG] execution.py: About to import wallet/client modules", flush=True)
from wallet_manager import SolanaWallet
from jupiter_client import JupiterClient
# from drift_client_wrapper import DriftClientWrapper  # Commented out for spot trading focus
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
            # self.drift = DriftClientWrapper()  # Commented out for spot trading focus
            raise ValueError("Leverage mode not available - Drift commented out")
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'spot' or 'leverage'")
            
        print(f"[ExecutionEngine] Initialized in {mode.upper()} mode (dry_run={dry_run})", flush=True)

    def execute_decision(self, decision: Dict[str, Any], token: str, chain: str = "solana") -> Dict[str, Any]:
        """
        Execute the Master Trader's decision.
        """
        action = decision.get("action")
        plan = decision.get("plan", {})
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
                return self._execute_spot_buy(token, kelly_size)
            elif self.mode == "leverage":
                return self._execute_leverage_open(token, "LONG", kelly_size, plan)
        elif action == "SELL":
            if self.mode == "spot":
                return self._execute_spot_sell(token, kelly_size)
            elif self.mode == "leverage":
                return self._execute_leverage_open(token, "SHORT", kelly_size, plan)
        elif action == "HOLD":
            print(f"[ExecutionEngine] HOLD - No execution needed")
            return {"status": "hold"}
        else:
            return {"error": f"Unknown action: {action}"}

    def _execute_spot_buy(self, token: str, kelly_size: float) -> Dict[str, Any]:
        """
        Execute spot buy via Jupiter.
        """
        print(f"[ExecutionEngine] Executing SPOT BUY for {token}")
        
        # Get SOL balance
        sol_balance = self.wallet.get_balance()
        print(f"[ExecutionEngine] SOL Balance: {sol_balance}")
        
        if sol_balance <= 0.01:  # Keep 0.01 SOL for fees
            return {"error": "Insufficient SOL balance for trade + fees"}
        
        # Calculate amount to spend (Kelly size of available balance)
        amount_to_spend = (sol_balance - 0.01) * kelly_size
        amount_lamports = int(amount_to_spend * 1e9)  # Convert to lamports
        
        print(f"[ExecutionEngine] Spending {amount_to_spend:.4f} SOL ({kelly_size*100:.1f}% of balance)")
        
        # Get token address (simplified - assumes we have it)
        # In production, we'd use the same lookup as TechnicalAnalyst
        from trader_agent_core import TraderAgent
        import asyncio

        async def get_address():
            agent = TraderAgent()
            return await agent._get_token_address(token, "solana")

        # Use existing event loop instead of asyncio.run()
        try:
            loop = asyncio.get_running_loop()
            token_address = loop.run_until_complete(get_address())
        except RuntimeError:
            # No running loop, can use asyncio.run()
            token_address = asyncio.run(get_address())
        
        if not token_address:
            return {"error": f"Could not find address for {token}"}
        
        # Execute swap: SOL -> Token
        result = self.jupiter.execute_swap(
            input_mint=self.jupiter.SOL_MINT,
            output_mint=token_address,
            amount=amount_lamports,
            slippage_bps=100  # 1% slippage
        )
        
        return result

    def _execute_spot_sell(self, token: str, kelly_size: float) -> Dict[str, Any]:
        """
        Execute spot sell via Jupiter.
        """
        print(f"[ExecutionEngine] Executing SPOT SELL for {token}")
        
        # Get token address
        from trader_agent_core import TraderAgent
        import asyncio

        async def get_address():
            agent = TraderAgent()
            return await agent._get_token_address(token, "solana")

        # Use existing event loop instead of asyncio.run()
        try:
            loop = asyncio.get_running_loop()
            token_address = loop.run_until_complete(get_address())
        except RuntimeError:
            # No running loop, can use asyncio.run()
            token_address = asyncio.run(get_address())
        
        if not token_address:
            return {"error": f"Could not find address for {token}"}
        
        # Get token balance
        token_balance = self.wallet.get_token_balance(token_address)
        
        if token_balance <= 0:
            return {"error": f"No {token} balance to sell"}
        
        # Calculate amount to sell (Kelly size of holdings)
        amount_to_sell = int(token_balance * kelly_size)
        
        print(f"[ExecutionEngine] Selling {amount_to_sell} units ({kelly_size*100:.1f}% of holdings)")
        
        # Execute swap: Token -> SOL
        result = self.jupiter.execute_swap(
            input_mint=token_address,
            output_mint=self.jupiter.SOL_MINT,
            amount=amount_to_sell,
            slippage_bps=100  # 1% slippage
        )
        
        return result

    def _execute_leverage_open(self, token: str, direction: str, kelly_size: float, plan: Dict) -> Dict[str, Any]:
        """
        Execute leverage position via Drift.
        """
        # Commented out for spot trading focus
        return {"error": "Leverage functionality commented out for spot trading focus"}

    def close_position(self, token: str) -> Dict[str, Any]:
        """
        Close an existing position (leverage only).
        """
        # Commented out for spot trading focus
        return {"error": "Leverage functionality commented out for spot trading focus"}
