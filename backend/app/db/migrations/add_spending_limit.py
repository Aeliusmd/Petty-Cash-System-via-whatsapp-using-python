"""
Migration: Add spending limit columns to employees table
Adds spending_limit, spending_limit_period, and spending_limit_custom_days
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend directory to path (3 levels up from this file)
# .../backend/app/db/migrations/add_spending_limit.py -> .../backend
current_file = Path(__file__).resolve()
backend_dir = current_file.parents[3]
sys.path.insert(0, str(backend_dir))

# Load environment variables
from dotenv import load_dotenv
root_dir = backend_dir.parent
env_local = root_dir / '.env.local'
env_default = root_dir / '.env'

if env_local.exists():
    print(f"📄 Loading environment from: {env_local.name}")
    load_dotenv(env_local)
else:
    print(f"📄 Loading environment from: {env_default.name}")
    load_dotenv(env_default)

from app.db.database import db


async def migrate():
    """Add spending limit columns to employees table"""
    print("🔄 Adding spending limit columns to employees table...")

    # Add spending_limit column
    await db.execute("""
        ALTER TABLE employees
        ADD COLUMN IF NOT EXISTS spending_limit DECIMAL(10,2) DEFAULT NULL
    """)
    print("  ✅ Added spending_limit column")

    # Add spending_limit_period column
    await db.execute("""
        ALTER TABLE employees
        ADD COLUMN IF NOT EXISTS spending_limit_period VARCHAR(20) DEFAULT 'monthly'
    """)
    print("  ✅ Added spending_limit_period column")

    # Add spending_limit_custom_days column
    await db.execute("""
        ALTER TABLE employees
        ADD COLUMN IF NOT EXISTS spending_limit_custom_days INT DEFAULT NULL
    """)
    print("  ✅ Added spending_limit_custom_days column")

    # Add check constraint for period values (ignore if already exists)
    try:
        await db.execute("""
            ALTER TABLE employees
            ADD CONSTRAINT chk_spending_limit_period
            CHECK (spending_limit_period IN ('daily', 'weekly', 'monthly', 'custom'))
        """)
        print("  ✅ Added check constraint for spending_limit_period")
    except Exception as e:
        if 'already exists' in str(e).lower():
            print("  ⚠️ Check constraint already exists, skipping")
        else:
            print(f"  ⚠️ Could not add check constraint (may already exist): {e}")

    print("✅ Migration complete!")


async def main():
    await db.connect()
    try:
        await migrate()
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
