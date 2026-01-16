"""
Quick script to run units table migration
"""
import asyncio
import asyncpg
import os

async def run_migration():
    # Database connection settings
    DB_HOST = os.getenv('DB_HOST', 'host.docker.internal')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', 'petty_cash')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASS = os.getenv('DB_PASSWORD', 'postgres')
    
    print(f"Connecting to {DB_HOST}:{DB_PORT}/{DB_NAME}...")
    
    conn = await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    
    # Create units table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS units (
            id SERIAL PRIMARY KEY,
            code VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ Created units table")
    
    # Insert default units
    await conn.execute('''
        INSERT INTO units (code, name) VALUES
            ('HQ', 'Headquarters'),
            ('SALES', 'Sales Department'),
            ('OPS', 'Operations')
        ON CONFLICT (code) DO NOTHING
    ''')
    print("✅ Inserted default units")
    
    await conn.close()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(run_migration())
