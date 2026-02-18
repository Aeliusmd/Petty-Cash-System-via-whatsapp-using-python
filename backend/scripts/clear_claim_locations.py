"""
Script to clear auto-assigned location_id from all existing claims.
The claim creation process never had a location picker, so all location_id
values were auto-assigned from employee.location_id by old code.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env.local'))

from app.db.database import db

async def clear_claim_locations():
    await db.connect()
    try:
        # Count how many claims have a location set
        result = await db.query("SELECT COUNT(*) as count FROM claims WHERE location_id IS NOT NULL")
        count = result[0]['count']
        print(f"Found {count} claims with location_id set.")

        if count == 0:
            print("Nothing to do.")
            return

        # Clear location_id from all claims
        await db.query("UPDATE claims SET location_id = NULL, updated_at = CURRENT_TIMESTAMP WHERE location_id IS NOT NULL")
        print(f"✅ Cleared location_id from {count} claims.")
    finally:
        await db.disconnect()

if __name__ == '__main__':
    asyncio.run(clear_claim_locations())
