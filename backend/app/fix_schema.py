import asyncio
import os
import sys

# Add parent directory to path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import db

async def fix_schema():
    print("🚀 Connecting to database...")
    try:
        await db.connect()
        print("📦 Connected.")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    try:
        print("🔧 Fixing foreign key constraint on audit_logs...")
        
        # 1. Drop the incorrect constraint
        # We try dropping both potential names just in case
        try:
            await db.execute("""
                ALTER TABLE audit_logs 
                DROP CONSTRAINT IF EXISTS audit_logs_organization_id_fkey
            """)
            print("Dropped audit_logs_organization_id_fkey")
        except Exception as e:
            print(f"Warning dropping constraint: {e}")

        # 2. Add the correct constraint
        await db.execute("""
            ALTER TABLE audit_logs 
            ADD CONSTRAINT audit_logs_organization_id_fkey 
            FOREIGN KEY (organization_id) REFERENCES organizations(id)
        """)
        
        print("✅ Foreign key constraint fixed! (References organizations table)")
        
    except Exception as e:
        print(f"❌ Error executing schema fix: {e}")
    finally:
        await db.close()
        print("👋 Connection closed.")

if __name__ == "__main__":
    asyncio.run(fix_schema())
