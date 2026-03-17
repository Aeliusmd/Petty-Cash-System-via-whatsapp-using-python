#!/usr/bin/env python3
"""
Petty Cash System - Main Runner
Run from project root: python run.py
"""

import os
import sys
from pathlib import Path

# Force UTF-8 on Windows console so emojis in print() don't crash with cp1252
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add backend to Python path
root_dir = Path(__file__).parent
backend_dir = root_dir / 'backend'
sys.path.insert(0, str(backend_dir))

# Load environment from root
# Priority: .env.local (for local dev) > .env (for Docker/default)
from dotenv import load_dotenv
env_local = root_dir / '.env.local'
env_default = root_dir / '.env'

if env_local.exists():
    load_dotenv(env_local)
    print("📄 Loaded environment from: .env.local (LOCAL DEVELOPMENT MODE)")
else:
    load_dotenv(env_default)
    print("📄 Loaded environment from: .env")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', '4101'))
    
    print("🚀 Starting Petty Cash System...")
    print(f"📍 Running from: {root_dir}")
    print(f"🔌 Port: {port}")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=[str(backend_dir)]
    )
