"""
Migration: Add Multi-Tenant Organization Support
- Add organization_id to employees table
- Create super_admin_audit_log table
- Update existing employees to belong to main org
"""
import asyncio
import asyncpg

async def run():
    try:
        conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/petty_cash_db')
        
        print('[1/4] Adding organization_id to employees...')
        
        # Add organization_id column if not exists
        await conn.execute('''
            ALTER TABLE employees 
            ADD COLUMN IF NOT EXISTS organization_id INTEGER REFERENCES units(id)
        ''')
        print('   OK - Added organization_id column')
        
        # Update existing employees to belong to main org (id=1)
        result = await conn.execute('''
            UPDATE employees 
            SET organization_id = 1 
            WHERE organization_id IS NULL
        ''')
        print(f'   OK - Updated employees: {result}')
        
        print('[2/4] Creating audit log table...')
        
        # Create super admin audit log table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS super_admin_audit_log (
                id SERIAL PRIMARY KEY,
                super_admin_id INTEGER REFERENCES employees(id),
                action VARCHAR(50) NOT NULL,
                organization_id INTEGER REFERENCES units(id),
                organization_name VARCHAR(100),
                ip_address VARCHAR(50),
                user_agent TEXT,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print('   OK - Created super_admin_audit_log table')
        
        print('[3/4] Creating indexes...')
        
        # Create index for faster queries
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_super_admin 
            ON super_admin_audit_log(super_admin_id, created_at DESC)
        ''')
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_employees_org
            ON employees(organization_id)
        ''')
        print('   OK - Created indexes')
        
        print('[4/4] Verifying...')
        
        # Show employee org distribution
        rows = await conn.fetch('''
            SELECT u.name as org_name, COUNT(e.id) as employee_count
            FROM employees e
            LEFT JOIN units u ON e.organization_id = u.id
            GROUP BY u.name
        ''')
        print('   Employees by organization:')
        for row in rows:
            print(f'      {row["org_name"] or "No Org"}: {row["employee_count"]} employees')
        
        await conn.close()
        print('\nDONE - Migration complete!')
        
    except Exception as e:
        print(f'ERROR: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
