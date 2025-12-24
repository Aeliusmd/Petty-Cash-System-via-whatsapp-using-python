#!/usr/bin/env python3
"""
Petty Cash System - Main Runner
Run from project root: python run.py
"""

import os
import sys
from pathlib import Path

# Add backend to Python path
root_dir = Path(__file__).parent
backend_dir = root_dir / 'backend'
sys.path.insert(0, str(backend_dir))

# Load environment from root
from dotenv import load_dotenv
load_dotenv(root_dir / '.env')

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
