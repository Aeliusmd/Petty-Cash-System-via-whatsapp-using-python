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

    orgs = await conn.fetch('SELECT id, name FROM organizations WHERE id != 1')
    
    default_units = [
        ('FIN', 'Finance'),
        ('HR', 'Human Resources'),
        ('IT', 'Information Technology'),
        ('OPS', 'Operations'),
        ('SALES', 'Sales'),
        ('ADMIN', 'Administration'),
        ('MKT', 'Marketing')
    ]
    
    for org in orgs:
        print(f"Populating departments for Org: {org['name']} (ID: {org['id']})")
        for code, name in default_units:
            await conn.execute('''
                INSERT INTO units (code, name, organization_id, is_active)
                VALUES ($1, $2, $3, TRUE)
                ON CONFLICT (code, organization_id) WHERE organization_id IS NOT NULL AND is_active = TRUE
                DO NOTHING
            ''', code, name, org['id'])
    
    await conn.close()
    
asyncio.run(run())
