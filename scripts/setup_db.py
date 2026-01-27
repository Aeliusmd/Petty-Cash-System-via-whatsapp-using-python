#!/usr/bin/env python3
"""
Database Setup Script - Run from project root
Usage: python setup_db.py
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from dotenv import load_dotenv
load_dotenv('.env')

import psycopg2
from psycopg2 import sql


DB_NAME = os.getenv('DB_NAME', 'petty_cash_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')


def setup():
    print('🔧 Petty Cash Database Setup')
    print('============================')
    
    try:
        # Connect to postgres database first
        print(f"\n1️⃣ Checking if database '{DB_NAME}' exists...")
        admin_conn = psycopg2.connect(
            host=DB_HOST, port=int(DB_PORT), database='postgres',
            user=DB_USER, password=DB_PASSWORD
        )
        admin_conn.autocommit = True
        admin_cur = admin_conn.cursor()
        
        admin_cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        if not admin_cur.fetchone():
            print(f"   Creating database '{DB_NAME}'...")
            admin_cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
            print('   ✅ Database created!')
        else:
            print('   ✅ Database already exists.')
        
        admin_cur.close()
        admin_conn.close()
        
        # Connect to our database
        print(f"\n2️⃣ Connecting to '{DB_NAME}'...")
        conn = psycopg2.connect(
            host=DB_HOST, port=int(DB_PORT), database=DB_NAME,
            user=DB_USER, password=DB_PASSWORD
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        db_dir = Path(__file__).parent.parent / 'backend' / 'app' / 'db'
        
        # Run schema
        print('\n3️⃣ Running schema.sql...')
        schema_path = db_dir / 'schema.sql'
        with open(schema_path, 'r', encoding='utf-8') as f:
            cur.execute(f.read())
        print('   ✅ Schema created!')
        
        # Run seed data
        print('\n4️⃣ Running seed.sql...')
        seed_path = db_dir / 'seed.sql'
        with open(seed_path, 'r', encoding='utf-8') as f:
            cur.execute(f.read())
        print('   ✅ Seed data inserted!')
        
        # Verify
        print('\n5️⃣ Verifying setup...')
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' ORDER BY table_name
        """)
        tables = cur.fetchall()
        print(f'   Found {len(tables)} tables:')
        for (table_name,) in tables:
            print(f'   - {table_name}')
        
        cur.execute('SELECT COUNT(*) FROM grades')
        grades = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM locations')
        locations = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM claim_categories')
        categories = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM batta_rates')
        rates = cur.fetchone()[0]
        
        print(f'\n📊 Record counts: Grades={grades}, Locations={locations}, Categories={categories}, Rates={rates}')
        
        cur.close()
        conn.close()
        
        print('\n✅ Database setup complete!')
        print('Next: python run.py')
        
    except Exception as e:
        print(f'\n❌ Setup failed: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    setup()
