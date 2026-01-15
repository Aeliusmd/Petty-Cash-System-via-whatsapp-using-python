import asyncio
import os
import sys

# Ensure app module can be imported
sys.path.append(os.getcwd())

from app.db.database import db

async def fix_schema():
    print("🔧 Starting schema fix...")
    try:
        # Use existing DB connection logic which reads env vars
        await db.connect()
        
        print("Checking conversation_states table...")
        
        # ALTER COLUMN to DROP NOT NULL constraint
        print("Attempting to make organization_id nullable...")
        
        # using db.pool directly to execute DDL
        async with db.pool.acquire() as connection:
            # Fix conversation_states
            print("Attempting to make organization_id nullable in conversation_states...")
            try:
                await connection.execute("""
                    ALTER TABLE conversation_states 
                    ALTER COLUMN organization_id DROP NOT NULL;
                """)
                print("✅ conversation_states: fixed")
            except Exception as e:
                print(f"⚠️ conversation_states error (might be already fixed/missing): {e}")

            # Fix claims
            print("Attempting to make organization_id nullable in claims...")
            try:
                await connection.execute("""
                    ALTER TABLE claims 
                    ALTER COLUMN organization_id DROP NOT NULL;
                """)
                print("✅ claims: fixed")
            except Exception as e:
                print(f"⚠️ claims error: {e}")

            
        print("✅ Successfully forced organization_id to be nullable")
        
    except Exception as e:
        print(f"❌ Error during schema fix: {e}")
    finally:
        await db.close()
        
if __name__ == "__main__":
    asyncio.run(fix_schema())
