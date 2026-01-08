import asyncio
import sys
import os

# Add /app/backend to path so we can import 'app'
sys.path.insert(0, '/app/backend')

from app.db import db

async def migrate():
    print("🔄 Starting migration...")
    try:
        await db.connect()
        print("✅ DB Connected")
    except Exception as e:
        print(f"⚠️ DB Connect warning (might be already connected or lazy): {e}")

    # Add message_id column
    try:
        await db.execute("ALTER TABLE claim_receipts ADD COLUMN IF NOT EXISTS message_id TEXT;")
        print("✅ Column 'message_id' added (or already exists)")
    except Exception as e:
        print(f"❌ Error adding column: {e}")

    # Add index
    try:
        await db.execute("CREATE INDEX IF NOT EXISTS idx_claim_receipts_message_id ON claim_receipts(message_id);")
        print("✅ Index created (or already exists)")
    except Exception as e:
        print(f"❌ Error creating index: {e}")
        
    await db.close()

if __name__ == "__main__":
    asyncio.run(migrate())
