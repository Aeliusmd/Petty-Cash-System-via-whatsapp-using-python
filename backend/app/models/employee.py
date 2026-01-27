"""
Employee Model - Database operations for employees table
"""

import re
from typing import Optional
from app.db.database import db


def normalize_phone_for_matching(phone: str) -> str:
    """
    Normalize phone number for consistent matching.
    Handles Sri Lankan phone formats:
    - +94771234567 -> 771234567 (international with +)
    - 94771234567  -> 771234567 (international without +)
    - 0771234567   -> 771234567 (local with leading 0)
    - 771234567    -> 771234567 (already normalized)
    """
    if not phone:
        return ''
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Handle Sri Lankan country code (94)
    if digits.startswith('94') and len(digits) >= 11:
        # Remove country code (94)
        digits = digits[2:]
    
    # Remove leading 0 if present
    if digits.startswith('0') and len(digits) >= 10:
        digits = digits[1:]
    
    return digits


async def find_by_phone(phone_number: str) -> Optional[dict]:
    """
    Find employee by phone number.
    Handles various phone number formats:
    - 94771234567 (from WhatsApp)
    - 0771234567 (local Sri Lankan)
    - +94771234567
    - 771234567
    """
    # Normalize incoming phone number
    normalized = normalize_phone_for_matching(phone_number)
    
    if not normalized:
        return None
    
    print(f"🔍 Phone lookup: original='{phone_number}' -> normalized='{normalized}'")
    
    # Use multiple patterns for flexible matching:
    # 1. Match the full normalized number anywhere
    # 2. Match with 94 prefix
    # 3. Match with 0 prefix
    # 4. Match last 9 digits (the core number without any prefix)
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
        WHERE (
            -- Match normalized phone directly
            REGEXP_REPLACE(e.phone_number, '[^0-9]', '', 'g') LIKE '%' || $1
            -- Or match with country code prepended
            OR REGEXP_REPLACE(e.phone_number, '[^0-9]', '', 'g') LIKE '%94' || $1
            -- Or match without leading 0
            OR REGEXP_REPLACE(e.phone_number, '[^0-9]', '', 'g') LIKE '%0' || $1
        )
        AND e.is_active = TRUE
    """, normalized)
    
    if result:
        print(f"✅ Found employee: {result[0].get('name')}")
    else:
        print(f"⚠️ No employee found for phone: {normalized}")
    
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
                               grade_id, unit_id, location_id, manager_id, role,
                               is_admin, is_manager)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11) RETURNING *
    """, employee_code, data.get('name'), data.get('phone_number'),
        data.get('email'), data.get('grade_id'), data.get('unit_id'),
        data.get('location_id'), data.get('manager_id'), data.get('role', 'staff'),
        data.get('is_admin', False), data.get('is_manager', False))
    
    return result[0]


async def update(employee_id: int, data: dict) -> dict:
    """
    Update employee with dynamic query generation.
    Only updates fields present in the data dictionary.
    Allows setting fields to None (NULL).
    """
    if not data:
        return await find_by_id(employee_id)
        
    # Map of allowed fields to column names (if different, otherwise same)
    # This prevents SQL injection by whitelisting columns
    valid_fields = {
        'employee_code': 'employee_code',
        'name': 'name',
        'phone_number': 'phone_number',
        'email': 'email',
        'grade_id': 'grade_id',
        'unit_id': 'unit_id',
        'location_id': 'location_id',
        'manager_id': 'manager_id',
        'role': 'role',
        'is_active': 'is_active',
        'is_admin': 'is_admin',
        'is_manager': 'is_manager'
    }
    
    set_clauses = []
    values = []
    param_idx = 1
    
    # Always update updated_at
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    
    for key, value in data.items():
        if key in valid_fields:
            column = valid_fields[key]
            set_clauses.append(f"{column} = ${param_idx}")
            values.append(value)
            param_idx += 1
            
    if not set_clauses:
        return await find_by_id(employee_id)
        
    query = f"""
        UPDATE employees 
        SET {', '.join(set_clauses)}
        WHERE id = ${param_idx} 
        RETURNING *
    """
    values.append(employee_id)
    
    result = await db.query(query, *values)
    
    return result[0] if result else None


async def delete(employee_id: int) -> bool:
    """Delete employee (soft delete - sets is_active to False)"""
    result = await db.query("""
        UPDATE employees SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
        WHERE id = $1 RETURNING id
    """, employee_id)
    
    return len(result) > 0


async def hard_delete(employee_id: int) -> bool:
    """
    Permanently delete employee and their associated data (use with caution)
    This will also delete all claims associated with the employee.
    """
    # First, delete associated claim status history
    await db.execute("""
        DELETE FROM claim_status_history 
        WHERE claim_id IN (SELECT id FROM claims WHERE employee_id = $1)
    """, employee_id)
    
    # Delete associated claim receipts
    await db.execute("""
        DELETE FROM claim_receipts 
        WHERE claim_id IN (SELECT id FROM claims WHERE employee_id = $1)
    """, employee_id)
    
    # Delete associated claim comments
    await db.execute("""
        DELETE FROM claim_comments 
        WHERE claim_id IN (SELECT id FROM claims WHERE employee_id = $1)
    """, employee_id)
    
    # Delete associated conversation states
    await db.execute("""
        DELETE FROM conversation_states WHERE employee_id = $1
    """, employee_id)
    
    # Delete associated claims
    await db.execute("""
        DELETE FROM claims WHERE employee_id = $1
    """, employee_id)
    
    # Finally, delete the employee
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
