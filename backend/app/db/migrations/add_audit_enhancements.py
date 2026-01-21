"""
Database Migration: Add Audit Log Enhancements
Adds session_id, organization_id, and metadata columns to audit_logs table
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import db module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db import db


async def migrate():
    """Run the migration"""
    try:
        await db.connect()
        print("🔄 Running audit_logs enhancement migration...")
        
        # Add new columns to audit_logs table
        print("  [1/4] Adding session_id column...")
        await db.execute("""
            ALTER TABLE audit_logs 
            ADD COLUMN IF NOT EXISTS session_id VARCHAR(100)
        """)
        print("  ✅ Added session_id column")
        
        print("  [2/4] Adding organization_id column...")
        await db.execute("""
            ALTER TABLE audit_logs 
            ADD COLUMN IF NOT EXISTS organization_id INT REFERENCES units(id)
        """)
        print("  ✅ Added organization_id column")
        
        print("  [3/4] Adding metadata column...")
        await db.execute("""
            ALTER TABLE audit_logs 
            ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'
        """)
        print("  ✅ Added metadata column")
        
        print("  [4/4] Creating indexes...")
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_performed_by 
            ON audit_logs(performed_by)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_action 
            ON audit_logs(action)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_organization 
            ON audit_logs(organization_id)
        """)
        print("  ✅ Created indexes")
        
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(migrate())
