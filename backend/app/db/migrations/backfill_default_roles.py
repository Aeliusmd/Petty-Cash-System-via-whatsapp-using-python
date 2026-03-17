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
    
    # We will copy 'admin', 'manager', 'finance', 'staff' from org 1 or defaults
    default_roles = [
        ('admin', 'Admin', 'Organization administrator'),
        ('manager', 'Manager', 'Team manager with approval rights'),
        ('finance', 'Finance', 'Finance officer'),
        ('staff', 'Staff', 'Standard employee role')
    ]
    
    for org in orgs:
        print(f"Populating roles for Org: {org['name']} (ID: {org['id']})")
        for code, name, desc in default_roles:
            # Check if role exists
            exists = await conn.fetchval('''
                SELECT id FROM roles 
                WHERE code = $1 AND organization_id = $2
            ''', code, org['id'])
            
            if not exists:
                # Insert role
                role_id = await conn.fetchval('''
                    INSERT INTO roles (code, name, description, organization_id, is_system_role, is_active)
                    VALUES ($1, $2, $3, $4, FALSE, TRUE)
                    RETURNING id
                ''', code, name, desc, org['id'])
                
                # Copy permissions from org 1's equivalent role
                source_role_id = await conn.fetchval('''
                    SELECT id FROM roles WHERE code = $1 AND organization_id = 1
                ''', code)
                
                if source_role_id and role_id:
                    await conn.execute('''
                        INSERT INTO role_permissions (role_id, permission_id)
                        SELECT $1, permission_id FROM role_permissions WHERE role_id = $2
                    ''', role_id, source_role_id)
                    
    await conn.close()
    
asyncio.run(run())
