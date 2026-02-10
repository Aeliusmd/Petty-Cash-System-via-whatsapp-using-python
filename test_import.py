
import sys
import os
sys.path.append(os.getcwd())

try:
    print(f"Propagating path: {sys.path}")
    import app
    print(f"Imported app from {app.__file__}")
    from app import reply_engine
    print("Imported reply_engine")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
