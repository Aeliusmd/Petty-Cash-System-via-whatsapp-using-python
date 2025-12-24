"""
Employee Model - Database operations for employees table
"""

import re
from typing import Optional
from app.db.database import db


async def find_by_phone(phone_number: str) -> Optional[dict]:
    """Find employee by phone number"""
    normalized = re.sub(r'[\s+\-]', '', phone_number)
    
    result = await db.query("""
        SELECT e.*, g.code as grade_code, g.name as grade_name,
               u.code as unit_code, u.name as unit_name,
               l.code as location_code, l.name as location_name,
               m.name as manager_name, m.phone_number as manager_phone
        FROM employees e
        LEFT JOIN grades g ON e.grade_id = g.id
        LEFT JOIN units u ON e.unit_id = u.id
        LEFT JOIN locations l ON e.location_id = l.id
        LEFT JOIN employees m ON e.manager_id = m.id
        WHERE (e.phone_number LIKE $1 OR e.phone_number LIKE $2)
        AND e.is_active = TRUE
    """, f"%{normalized}", f"%{normalized[-10:]}")
    
    return result[0] if result else None


async def find_by_chat_id(chat_id: str) -> Optional[dict]:
    """Find employee by WhatsApp chat ID"""
    result = await db.query("""
        SELECT e.*, g.code as grade_code, g.name as grade_name,
               u.code as unit_code, u.name as unit_name,
               l.code as location_code, l.name as location_name,
               m.name as manager_name, m.phone_number as manager_phone
        FROM employees e
        LEFT JOIN grades g ON e.grade_id = g.id
        LEFT JOIN units u ON e.unit_id = u.id
        LEFT JOIN locations l ON e.location_id = l.id
        LEFT JOIN employees m ON e.manager_id = m.id
        WHERE e.whatsapp_chat_id = $1 AND e.is_active = TRUE
    """, chat_id)
    
    return result[0] if result else None


async def link_chat_id(employee_id: int, chat_id: str) -> Optional[dict]:
    """Link WhatsApp chat ID to employee"""
    result = await db.query("""
        UPDATE employees 
        SET whatsapp_chat_id = $1, updated_at = CURRENT_TIMESTAMP
        WHERE id = $2 RETURNING *
    """, chat_id, employee_id)
    
    return result[0] if result else None


async def find_by_id(employee_id: int) -> Optional[dict]:
    """Find employee by ID"""
    result = await db.query("""
        SELECT e.*, g.code as grade_code, g.name as grade_name,
               u.code as unit_code, u.name as unit_name,
               l.code as location_code, l.name as location_name
        FROM employees e
        LEFT JOIN grades g ON e.grade_id = g.id
        LEFT JOIN units u ON e.unit_id = u.id
        LEFT JOIN locations l ON e.location_id = l.id
        WHERE e.id = $1
    """, employee_id)
    
    return result[0] if result else None


async def find_all() -> list[dict]:
    """Get all active employees"""
    return await db.query("""
        SELECT e.*, g.code as grade_code, l.code as location_code
        FROM employees e
        LEFT JOIN grades g ON e.grade_id = g.id
        LEFT JOIN locations l ON e.location_id = l.id
        WHERE e.is_active = TRUE ORDER BY e.name
    """)


async def create(data: dict) -> dict:
    """Create new employee"""
    result = await db.query("""
        INSERT INTO employees (employee_code, name, phone_number, email,
                               grade_id, unit_id, location_id, manager_id, role)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING *
    """, data.get('employee_code'), data.get('name'), data.get('phone_number'),
        data.get('email'), data.get('grade_id'), data.get('unit_id'),
        data.get('location_id'), data.get('manager_id'), data.get('role', 'staff'))
    
    return result[0]
