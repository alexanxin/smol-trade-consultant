signal_none = {'entry_price': None}
signal_val = {'entry_price': 123.456789}
signal_missing = {}

print(f"None: ${(signal_none.get('entry_price') or 0):.4f}")
print(f"Value: ${(signal_val.get('entry_price') or 0):.4f}")
print(f"Missing: ${(signal_missing.get('entry_price') or 0):.4f}")
