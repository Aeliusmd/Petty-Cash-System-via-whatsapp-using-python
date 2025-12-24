#!/usr/bin/env python3
"""
Add Employee Script - Run from project root
Usage: python add_employee.py <phone> <name> <grade> <location> [role]
       python add_employee.py list
"""

import os
import sys
import re
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from dotenv import load_dotenv
load_dotenv('.env')

import psycopg2


def get_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5432')),
        database=os.getenv('DB_NAME', 'petty_cash_db'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres')
    )


def add_employee(phone_number, name, grade_code, location_code, role='staff'):
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('SELECT id FROM grades WHERE code = %s', (grade_code.upper(),))
        grade_result = cur.fetchone()
        if not grade_result:
            print(f"❌ Grade '{grade_code}' not found. Valid: A, B, C, D, E")
            return
        grade_id = grade_result[0]

        cur.execute('SELECT id FROM locations WHERE code = %s', (location_code.upper(),))
        location_result = cur.fetchone()
        if not location_result:
            print(f"❌ Location '{location_code}' not found.")
            cur.execute('SELECT code, name FROM locations ORDER BY code')
            for code, loc_name in cur.fetchall():
                print(f'  {code} - {loc_name}')
            return
        location_id = location_result[0]

        cur.execute('SELECT COUNT(*) FROM employees')
        count = cur.fetchone()[0] + 1
        employee_code = f'EMP{count:04d}'

        normalized_phone = re.sub(r'[\s+\-]', '', phone_number)

        cur.execute('SELECT name FROM employees WHERE phone_number = %s', (normalized_phone,))
        existing = cur.fetchone()
        if existing:
            print(f"❌ Phone already registered to: {existing[0]}")
            return

        cur.execute("""
            INSERT INTO employees (employee_code, name, phone_number, grade_id, location_id, role)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING *
        """, (employee_code, name, normalized_phone, grade_id, location_id, role))
        
        conn.commit()
        print(f'✅ Added: {employee_code} | {name} | {normalized_phone} | Grade {grade_code.upper()} | {location_code.upper()} | {role}')
        
    except Exception as e:
        print(f'❌ Error: {e}')
    finally:
        cur.close()
        conn.close()


def list_employees():
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT e.employee_code, e.name, e.phone_number, g.code, l.code, e.role
        FROM employees e
        LEFT JOIN grades g ON e.grade_id = g.id
        LEFT JOIN locations l ON e.location_id = l.id
        WHERE e.is_active = TRUE ORDER BY e.employee_code
    """)
    
    employees = cur.fetchall()
    
    print('\n📋 Registered Employees:')
    print('─' * 90)
    print(f'{"Code":<10}{"Name":<25}{"Phone":<18}{"Grade":<8}{"Location":<10}{"Role":<10}')
    print('─' * 90)
    
    for emp in employees:
        code, name, phone, grade, location, role = emp
        print(f'{code:<10}{name[:23]:<25}{phone:<18}{grade or "N/A":<8}{location or "N/A":<10}{role:<10}')
    
    print('─' * 90)
    print(f'Total: {len(employees)}')
    
    cur.close()
    conn.close()


def main():
    args = sys.argv[1:]
    
    if not args or args[0] == 'list':
        list_employees()
    elif len(args) >= 4:
        phone, name, grade, location = args[:4]
        role = args[4] if len(args) > 4 else 'staff'
        add_employee(phone, name, grade, location, role)
    else:
        print('Usage:')
        print('  python add_employee.py list')
        print('  python add_employee.py <phone> "<name>" <grade> <location> [role]')
        print('  Grades: A, B, C, D, E')
        print('  Locations: CMB, KDY, GAL, JAF, ANU, KUR, RAT, BAD, TRI, BAT')
        print('  Roles: staff, manager, admin, finance')


if __name__ == '__main__':
    main()
