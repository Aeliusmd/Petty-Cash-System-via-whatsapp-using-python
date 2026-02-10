
import asyncio
import asyncpg
import os

async def update_schema():
    print("🚀 Connecting to database...")
    
    try:
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            database=os.getenv('DB_NAME', 'petty_cash_db'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        print("📦 Connected to PostgreSQL database")
        
        print("🔄 Updating claim_type constraint...")
        # Drop the existing constraint
        await conn.execute("ALTER TABLE claims DROP CONSTRAINT IF EXISTS claims_claim_type_check")
        
        # Add the new constraint with 'advance'
        await conn.execute("ALTER TABLE claims ADD CONSTRAINT claims_claim_type_check CHECK (claim_type IN ('bill', 'outright', 'advance', 'quotation'))")
        
        print("✅ Constraint updated successfully!")
        
        await conn.close()
    except Exception as e:
        print(f"❌ Error updating schema: {e}")

if __name__ == "__main__":
    asyncio.run(update_schema())
