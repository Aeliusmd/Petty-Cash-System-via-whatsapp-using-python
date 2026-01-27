import asyncio
import asyncpg
import os

# DB Config
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'petty_cash_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

async def add_prompt_messages():
    print("Connecting to database...")
    conn = await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    
    try:
        print("\n=== Adding prompt_message column ===")
        
        # Check if column exists
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'claim_categories' 
                AND column_name = 'prompt_message'
            )
        """)
        
        if not column_exists:
            await conn.execute("""
                ALTER TABLE claim_categories 
                ADD COLUMN prompt_message TEXT
            """)
            print("✅ Added prompt_message column")
        else:
            print("ℹ️  prompt_message column already exists")
        
        print("\n=== Setting default prompt messages ===")
        
        # Update existing categories with default prompts
        await conn.execute("""
            UPDATE claim_categories 
            SET prompt_message = 
                CASE 
                    WHEN LOWER(name) LIKE '%batta%' OR LOWER(code) = 'batta' THEN 
                        '📦 Daily Allowance Claim

Please provide:
• Date of travel
• Location/Route
• Purpose

Example: "2024-01-15, Colombo to Galle, Client meeting"'
                    
                    WHEN LOWER(name) LIKE '%fuel%' OR LOWER(code) = 'fuel' THEN 
                        '⛽ Fuel Expense Claim

Please provide:
• Date
• Amount (Rs.)
• Vehicle number
• Purpose/Destination

Example: "2024-01-15, Rs.5000, CAR-1234, Site visit to Kandy"'
                    
                    WHEN LOWER(name) LIKE '%accom%' OR LOWER(code) = 'accom' THEN 
                        '🏨 Accommodation Claim

Please provide:
• Hotel name
• Check-in and Check-out dates
• Amount (Rs.)
• Purpose

Example: "Hotel Cinnamon, 15-16 Jan, Rs.8000, Conference attendance"'
                    
                    WHEN LOWER(name) LIKE '%sundry%' OR LOWER(code) = 'sundry' THEN 
                        '📝 Sundry Expense Claim

Please describe:
• What was purchased
• Amount (Rs.)
• Purpose

Example: "Stationery supplies, Rs.1500, Office use"'
                    
                    ELSE 
                        '📝 Expense Claim

Please provide:
• Description of expense
• Amount (Rs.)
• Purpose

Example: "Office supplies, Rs.2000, Team meeting"'
                END
            WHERE prompt_message IS NULL
        """)
        
        print("✅ Updated default prompt messages")
        
        print("\n=== Current Categories with Prompts ===")
        categories = await conn.fetch("""
            SELECT id, code, name, LEFT(prompt_message, 50) as prompt_preview
            FROM claim_categories
            WHERE is_active = TRUE
            ORDER BY display_order, name
        """)
        
        for cat in categories:
            preview = cat['prompt_preview'] + '...' if cat['prompt_preview'] else 'No prompt'
            print(f"[{cat['id']}] {cat['name']} ({cat['code']})")
            print(f"    Prompt: {preview}")
        
        print("\n✅ Migration complete!")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(add_prompt_messages())
