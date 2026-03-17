"""
Migration: Scope units code to organization
- Drop global unique constraint on units.code
- Add unique constraint on (organization_id, code)
"""
import asyncio
import asyncpg
import os

async def run():
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', 'petty_cash_db')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASS = os.getenv('DB_PASSWORD', 'postgres')
    
    conn = await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    
    try:
        print('[1/2] Dropping global unique constraint on units.code')
        # Find the constraint name
        constraint_query = """
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'units' AND constraint_type = 'UNIQUE'
            AND constraint_name LIKE '%code%'
        """
        constraints = await conn.fetch(constraint_query)
        
        for c in constraints:
            c_name = c['constraint_name']
            print(f'   Dropping constraint {c_name}...')
            await conn.execute(f'ALTER TABLE units DROP CONSTRAINT IF EXISTS "{c_name}"')
            
        # Also drop unique indexes if any
        index_query = """
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'units' AND indexdef LIKE '%UNIQUE%' AND indexdef LIKE '%code%'
        """
        indexes = await conn.fetch(index_query)
        for idx in indexes:
            idx_name = idx['indexname']
            # Only drop if it's not the primary key, which doesn't contain code
            print(f'   Dropping index {idx_name}...')
            await conn.execute(f'DROP INDEX IF EXISTS "{idx_name}"')

        print('[2/2] Adding organization-scoped unique constraint for active units')
        await conn.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_units_code_org_active 
            ON units(code, organization_id) WHERE organization_id IS NOT NULL AND is_active = TRUE
        ''')
        await conn.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_units_code_global_active 
            ON units(code) WHERE organization_id IS NULL AND is_active = TRUE
        ''')
        print('   OK - Scoped unique constraints added successfully')
        
    except Exception as e:
        print(f'ERROR: {e}')
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run())
