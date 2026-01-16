"""
Database migration: Add vendor column to claim_receipts table
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.database import db


async def migrate():
    """Add vendor column to claim_receipts"""
    try:
        await db.connect()
        
        print("🔄 Starting migration: add vendor to claim_receipts...")
        
        # Add vendor column
        await db.execute("""
            ALTER TABLE claim_receipts 
            ADD COLUMN IF NOT EXISTS vendor VARCHAR(255)
        """)
        
        print("✅ Added vendor column")
        
        # Add index
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_claim_receipts_vendor 
            ON claim_receipts(vendor)
        """)
        
        print("✅ Added vendor index")
        print("✅ Migration completed successfully!")
        
        await db.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(migrate())
