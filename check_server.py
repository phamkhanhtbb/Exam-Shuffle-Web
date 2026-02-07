
import sys
import os
import traceback

sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

print("Checking server.py syntax...")
try:
    from backend import server
    print("[PASS] server.py imported successfully.")
except Exception as e:
    print(f"[FAIL] server.py import failed: {e}")
    traceback.print_exc()
