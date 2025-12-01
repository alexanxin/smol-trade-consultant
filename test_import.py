import sys
print(sys.executable)
try:
    import google.generativeai
    print("Import successful")
except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"Other error: {e}")
