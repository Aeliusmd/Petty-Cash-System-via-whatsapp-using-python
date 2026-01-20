"""
Migration: Add role column to employees table
Run this to add super admin support
"""
import asyncio
import asyncpg

async def run():
    try:
        conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/petty_cash_db')
        
        # Add role column
        await conn.execute('''
            ALTER TABLE employees 
            ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'employee'
        ''')
        print('✅ Added role column')
        
        # Migrate existing data - admins stay admin, others are employee
        await conn.execute('''
            UPDATE employees 
            SET role = CASE 
                WHEN is_admin = TRUE THEN 'admin'
                ELSE 'employee'
            END
            WHERE role = 'employee' OR role IS NULL
        ''')
        print('✅ Migrated existing is_admin values')
        
        # Set employee ID 1 as super_admin (you can change this)
        await conn.execute('''
            UPDATE employees 
            SET role = 'super_admin' 
            WHERE id = 1
        ''')
        print('✅ Set employee ID 1 as super_admin')
        
        # Show current roles
        rows = await conn.fetch('SELECT id, name, role FROM employees ORDER BY id LIMIT 10')
        print('\n📋 Current employee roles:')
        for row in rows:
            print(f'   ID {row["id"]}: {row["name"]} - {row["role"]}')
        
        await conn.close()
        print('\n✅ Migration complete!')
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == "__main__":
    asyncio.run(run())
