"""
Database migration: Add message_id column to claim_receipts table
This enables receipt forwarding during appeals
"""
import asyncio
import sys
import os

# Add parent directory to path to import db module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db

async def run_migration():
    """Run the migration to add message_id column"""
    try:
        print("🔄 Starting migration: add message_id to claim_receipts...")
        
        # Add message_id column
        await db.execute("""
            ALTER TABLE claim_receipts 
            ADD COLUMN IF NOT EXISTS message_id TEXT
        """)
        print("✅ Added message_id column")
        
        # Create index
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_claim_receipts_message_id 
            ON claim_receipts(message_id)
        """)
        print("✅ Created index on message_id")
        
        print("🎉 Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_migration())
