
import asyncio
import os
import sys

# Ensure app module can be imported (assuming script runs from backend/ directory)
sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv('.env.local')  # Load local env vars

from app.db.database import db
from app.models.claim import Claim

async def fix_claims():
    print("Starting system_amount recalculation...")
    try:
        await db.connect()
        
        # Get all claim IDs
        claims = await db.query("SELECT id, claim_number FROM claims")
        print(f"Found {len(claims)} claims to process.")
        
        count = 0
        for claim in claims:
            claim_id = claim['id']
            try:
                # Calculate and update system_amount
                new_amount = await Claim.calculate_system_amount(claim_id)
                count += 1
                if new_amount > 0:
                    print(f"Claim #{claim['claim_number']}: Updated system_amount to {new_amount}")
            except Exception as e:
                print(f"Error processing Claim #{claim['claim_number']}: {e}")
        
        print(f"Completed! Processed {count} claims.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(fix_claims())
