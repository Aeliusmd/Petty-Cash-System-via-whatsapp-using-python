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
    """Create new employee with auto-generated code if not provided"""
    # Auto-generate employee code if not provided
    employee_code = data.get('employee_code')
    if not employee_code:
        # Get the next employee code number
        result = await db.query("""
            SELECT COALESCE(MAX(CAST(SUBSTRING(employee_code FROM 5) AS INTEGER)), 0) + 1 as next_num
            FROM employees WHERE employee_code LIKE 'EMP-%'
        """)
        next_num = result[0]['next_num'] if result else 1
        employee_code = f"EMP-{next_num:04d}"
    
    result = await db.query("""
        INSERT INTO employees (employee_code, name, phone_number, email,
                               grade_id, unit_id, location_id, manager_id, role)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING *
    """, employee_code, data.get('name'), data.get('phone_number'),
        data.get('email'), data.get('grade_id'), data.get('unit_id'),
        data.get('location_id'), data.get('manager_id'), data.get('role', 'staff'))
    
    return result[0]


async def update(employee_id: int, data: dict) -> dict:
    """Update employee"""
    result = await db.query("""
        UPDATE employees SET
            employee_code = COALESCE($1, employee_code),
            name = COALESCE($2, name),
            phone_number = COALESCE($3, phone_number),
            email = COALESCE($4, email),
            grade_id = COALESCE($5, grade_id),
            unit_id = COALESCE($6, unit_id),
            location_id = COALESCE($7, location_id),
            manager_id = $8,
            role = COALESCE($9, role),
            is_active = COALESCE($10, is_active),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $11 RETURNING *
    """, data.get('employee_code'), data.get('name'), data.get('phone_number'),
        data.get('email'), data.get('grade_id'), data.get('unit_id'),
        data.get('location_id'), data.get('manager_id'), data.get('role'),
        data.get('is_active'), employee_id)
    
    return result[0] if result else None


async def delete(employee_id: int) -> bool:
    """Delete employee (soft delete - sets is_active to False)"""
    result = await db.query("""
        UPDATE employees SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
        WHERE id = $1 RETURNING id
    """, employee_id)
    
    return len(result) > 0


async def hard_delete(employee_id: int) -> bool:
    """Permanently delete employee (use with caution)"""
    result = await db.query("""
        DELETE FROM employees WHERE id = $1 RETURNING id
    """, employee_id)
    
    return len(result) > 0


async def find_all_with_details(role: str = None, location_id: int = None, 
                                 include_inactive: bool = False) -> list[dict]:
    """Get all employees with full details and optional filters"""
    query = """
        SELECT e.*, g.code as grade_code, g.name as grade_name,
               u.code as unit_code, u.name as unit_name,
               l.code as location_code, l.name as location_name,
               m.name as manager_name
        FROM employees e
        LEFT JOIN grades g ON e.grade_id = g.id
        LEFT JOIN units u ON e.unit_id = u.id
        LEFT JOIN locations l ON e.location_id = l.id
        LEFT JOIN employees m ON e.manager_id = m.id
        WHERE 1=1
    """
    params = []
    param_idx = 1
    
    if not include_inactive:
        query += f" AND e.is_active = TRUE"
    
    if role:
        query += f" AND e.role = ${param_idx}"
        params.append(role)
        param_idx += 1
    
    if location_id:
        query += f" AND e.location_id = ${param_idx}"
        params.append(location_id)
        param_idx += 1
    
    query += " ORDER BY e.name"
    
    return await db.query(query, *params)
