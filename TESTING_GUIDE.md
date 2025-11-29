# Testing Solana Payment Integration

## Prerequisites

1. **Get a Solana Wallet Private Key**
   - Use Phantom, Solflare, or create a new wallet with Solana CLI
   - Export your private key (base58 format)
   - **IMPORTANT**: Use a test wallet with minimal funds (0.1 SOL max)

2. **Add Private Key to `.env`**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add:
   SOLANA_PRIVATE_KEY=your_base58_private_key_here
   RPC_URL=https://api.mainnet-beta.solana.com  # Optional, defaults to mainnet
   ```

## Testing Steps

### 1. Verify Wallet Connection
Run the verification script to check if your wallet loads correctly:
```bash
python3 verify_wallet.py
```

Expected output:
```
✅ Wallet loaded successfully: <your_public_key>
   Balance: X.XX SOL
✅ Quote fetched successfully!
```

### 2. Test with Dry Run (No Real Swap)
If you don't add `SOLANA_PRIVATE_KEY`, the agent will run in **simulation mode**:
```bash
python3 trader-agent.py --token SOL --chain solana --mode signal
```

Output will show:
```
⚠️  No wallet configured. Skipping live swap.
```

### 3. Test with Real Swap (CAUTION!)
Once you've added your private key:
```bash
python3 trader-agent.py --token BONK --chain solana --mode signal
```

If a BUY signal is generated and approved:
- The agent will swap **0.01 SOL** for the target token
- Transaction will be sent to Solana blockchain
- You'll see: `✅ Swap Executed! Signature: <tx_signature>`

### 4. Verify Transaction
Check your transaction on Solscan:
```
https://solscan.io/tx/<your_signature>
```

## Safety Features

1. **Fixed Amount**: Currently hardcoded to 0.01 SOL per swap
2. **Slippage Protection**: Default 0.5% slippage tolerance
3. **Risk Manager**: Trades must pass AI risk assessment
4. **Database Logging**: All signals and swaps are logged to `trader_agent.db`

## Troubleshooting

**"No wallet loaded"**
- Check your `.env` file has `SOLANA_PRIVATE_KEY`
- Ensure the key is in base58 format (starts with letters/numbers, no spaces)

**"Insufficient funds"**
- Add at least 0.02 SOL to your wallet (0.01 for swap + fees)

**"Swap failed"**
- Check RPC connection
- Verify token address is correct
- Ensure sufficient liquidity on Jupiter

## Next Steps

To customize the swap amount, edit `trader-agent.py` around line 2333:
```python
amount_sol = 0.01  # Change this value
```
