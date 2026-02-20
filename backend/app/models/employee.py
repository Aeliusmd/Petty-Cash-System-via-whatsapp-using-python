"""
Employee Model
OOP class for employee database operations
"""

import re
from typing import Optional, List, Dict, Any
from app.models.base import BaseModel
from app.db.database import db


class Employee(BaseModel):
    """
    Employee model with database operations.
    Handles employee CRUD and phone number matching.
    """
    
    table_name = "employees"
    
    # Instance attributes
    id: int = None
    employee_code: str = None
    name: str = None
    phone_number: str = None
    email: str = None
    role: str = "staff" # Legacy string role (kept for backward compatibility)
    role_id: int = None # New RBAC role ID
    grade_id: int = None
    unit_id: int = None
    location_id: int = None
    manager_id: int = None
    whatsapp_chat_id: str = None
    is_active: bool = True
    is_admin: bool = False
    spending_limit: float = None
    spending_limit_period: str = 'monthly'
    spending_limit_custom_days: int = None
    is_manager: bool = False
    
    # Joined fields (from queries)
    grade_code: str = None
    grade_name: str = None
    unit_code: str = None
    unit_name: str = None
    location_code: str = None
    location_name: str = None
    manager_name: str = None
    manager_phone: str = None
    organization_id: int = None
    organization_name: str = None
    
    # Permissions (populated dynamically)
    permissions: List[str] = []
    
    async def get_permissions(self) -> List[str]:
        """
        Get all permissions including inherited ones via Recursive CTE
        """
        # If no role_id, fallback to mapping from role string or empty
        role_id_to_use = self.role_id
        if not role_id_to_use and self.role:
            # Try to resolve role_id from role string
            res = await db.query("SELECT id FROM roles WHERE code = $1", self.role)
            if res:
                role_id_to_use = res[0]['id']
                
        if not role_id_to_use:
            return []

        query = """
            WITH RECURSIVE role_hierarchy AS (
                -- Base case: current role
                SELECT id, parent_role_id FROM roles WHERE id = $1
                UNION ALL
                -- Recursive case: parent role
                SELECT p.id, p.parent_role_id 
                FROM roles p 
                JOIN role_hierarchy rh ON rh.parent_role_id = p.id
            )
            SELECT DISTINCT p.code
            FROM role_hierarchy rh
            JOIN role_permissions rp ON rh.id = rp.role_id
            JOIN permissions p ON rp.permission_id = p.id
            WHERE p.is_active = TRUE
        """
        rows = await db.query(query, role_id_to_use)
        return [row['code'] for row in rows]
    
    def __init__(self, data: Dict[str, Any] = None):
        """Initialize employee from data dict"""
        super().__init__(data)
        if data and 'permissions' in data:
            self.permissions = data['permissions']
    
    @staticmethod
    def normalize_phone(phone: str) -> str:
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
            digits = digits[2:]
        
        # Remove leading 0 if present
        if digits.startswith('0') and len(digits) >= 10:
            digits = digits[1:]
        
        return digits
    
    @classmethod
    async def find_by_phone(cls, phone_number: str) -> Optional['Employee']:
        """
        Find employee by phone number.
        Handles various phone number formats.
        
        Args:
            phone_number: Phone in any format
            
        Returns:
            Employee instance or None
        """
        normalized = cls.normalize_phone(phone_number)
        if not normalized:
            return None
        
        print(f"🔍 Phone lookup: original='{phone_number}' -> normalized='{normalized}'")
        
        result = await db.query("""
            SELECT e.*, g.code as grade_code, g.name as grade_name,
                   u.code as unit_code, u.name as unit_name,
                   l.code as location_code, l.name as location_name,
                   m.name as manager_name, m.phone_number as manager_phone,
                   COALESCE(e.organization_id, o.id) as organization_id, o.name as organization_name
            FROM employees e
            LEFT JOIN grades g ON e.grade_id = g.id
            LEFT JOIN units u ON e.unit_id = u.id
            LEFT JOIN organizations o ON u.organization_id = o.id
            LEFT JOIN locations l ON e.location_id = l.id
            LEFT JOIN employees m ON e.manager_id = m.id
            WHERE (
                REGEXP_REPLACE(e.phone_number, '[^0-9]', '', 'g') LIKE '%' || $1
                OR REGEXP_REPLACE(e.phone_number, '[^0-9]', '', 'g') LIKE '%94' || $1
                OR REGEXP_REPLACE(e.phone_number, '[^0-9]', '', 'g') LIKE '%0' || $1
            )
            AND e.is_active = TRUE
        """, normalized)
        
        if result:
            print(f"✅ Found employee: {result[0].get('name')}")
            return cls(result[0])
        
        print(f"⚠️ No employee found for phone: {normalized}")
        return None
    
    @classmethod
    async def find_by_chat_id(cls, chat_id: str) -> Optional['Employee']:
        """Find employee by WhatsApp chat ID"""
        result = await db.query("""
            SELECT e.*, g.code as grade_code, g.name as grade_name,
                   u.code as unit_code, u.name as unit_name,
                   l.code as location_code, l.name as location_name,
                   m.name as manager_name, m.phone_number as manager_phone,
                   COALESCE(e.organization_id, o.id) as organization_id, o.name as organization_name
            FROM employees e
            LEFT JOIN grades g ON e.grade_id = g.id
            LEFT JOIN units u ON e.unit_id = u.id
            LEFT JOIN organizations o ON u.organization_id = o.id
            LEFT JOIN locations l ON e.location_id = l.id
            LEFT JOIN employees m ON e.manager_id = m.id
            WHERE e.whatsapp_chat_id = $1 AND e.is_active = TRUE
        """, chat_id)
        
        return cls(result[0]) if result else None
    
    @classmethod
    async def find_by_id(cls, employee_id: int) -> Optional['Employee']:
        """Find employee by ID with joined data"""
        result = await db.query("""
            SELECT e.*, g.code as grade_code, g.name as grade_name,
                   u.code as unit_code, u.name as unit_name,
                   l.code as location_code, l.name as location_name,
                   COALESCE(e.organization_id, o.id) as organization_id,
                   o.name as organization_name
            FROM employees e
            LEFT JOIN grades g ON e.grade_id = g.id
            LEFT JOIN units u ON e.unit_id = u.id
            LEFT JOIN organizations o ON u.organization_id = o.id
            LEFT JOIN locations l ON e.location_id = l.id
            WHERE e.id = $1
        """, employee_id)
        
        return cls(result[0]) if result else None
    
    @classmethod
    async def link_chat_id(cls, employee_id: int, chat_id: str) -> Optional['Employee']:
        """Link WhatsApp chat ID to employee"""
        result = await db.query("""
            UPDATE employees 
            SET whatsapp_chat_id = $1, updated_at = CURRENT_TIMESTAMP
            WHERE id = $2 RETURNING *
        """, chat_id, employee_id)
        
        return cls(result[0]) if result else None
    
    @classmethod
    async def find_all(cls, include_inactive: bool = False) -> List['Employee']:
        """Get all employees"""
        query = """
            SELECT e.*, g.code as grade_code, l.code as location_code
            FROM employees e
            LEFT JOIN grades g ON e.grade_id = g.id
            LEFT JOIN locations l ON e.location_id = l.id
        """
        if not include_inactive:
            query += " WHERE e.is_active = TRUE"
        query += " ORDER BY e.name"
        
        result = await db.query(query)
        return [cls(row) for row in result]
    
    @classmethod
    async def find_all_with_details(
        cls,
        role: str = None,
        location_id: int = None,
        unit_id: int = None,
        organization_id: int = None,
        include_inactive: bool = False
    ) -> List['Employee']:
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
            query += " AND e.is_active = TRUE"
        
        if role:
            query += f" AND e.role = ${param_idx}"
            params.append(role)
            param_idx += 1
        
        if location_id:
            query += f" AND e.location_id = ${param_idx}"
            params.append(location_id)
            param_idx += 1
        
        if unit_id:
            query += f" AND e.unit_id = ${param_idx}"
            params.append(unit_id)
            param_idx += 1
        
        if organization_id:
            query += f" AND e.organization_id = ${param_idx}"
            params.append(organization_id)
            param_idx += 1
        
        query += " ORDER BY e.name"
        
        result = await db.query(query, *params)
        return [cls(row) for row in result]
    
    @classmethod
    async def create(cls, data: Dict[str, Any]) -> 'Employee':
        """Create new employee with auto-generated code if not provided"""
        employee_code = data.get('employee_code')
        if not employee_code:
            result = await db.query("""
                SELECT COALESCE(MAX(CAST(SUBSTRING(employee_code FROM 5) AS INTEGER)), 0) + 1 as next_num
                FROM employees WHERE employee_code LIKE 'EMP-%'
            """)
            next_num = result[0]['next_num'] if result else 1
            employee_code = f"EMP-{next_num:04d}"
        
        result = await db.query("""
            INSERT INTO employees (employee_code, name, phone_number, email,
                                   grade_id, unit_id, location_id, manager_id, role, role_id,
                                   organization_id, is_admin, is_manager,
                                   spending_limit, spending_limit_period, spending_limit_custom_days)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::VARCHAR, 
                    (SELECT id FROM roles WHERE code = $9::VARCHAR LIMIT 1), -- Auto-map role string to ID
                    $10, $11, $12, $13, $14, $15) RETURNING *
        """, employee_code, data.get('name'), data.get('phone_number'),
            data.get('email'), data.get('grade_id'), data.get('unit_id'),
            data.get('location_id'), data.get('manager_id'), data.get('role', 'staff'),
            data.get('organization_id'), data.get('is_admin', False), data.get('is_manager', False),
            data.get('spending_limit'), data.get('spending_limit_period', 'monthly'),
            data.get('spending_limit_custom_days'))
        
        return cls(result[0])
    
    @classmethod
    async def update(cls, employee_id: int, data: Dict[str, Any]) -> Optional['Employee']:
        """Update employee with dynamic query generation"""
        if not data:
            return await cls.find_by_id(employee_id)
        
        valid_fields = {
            'employee_code', 'name', 'phone_number', 'email',
            'grade_id', 'unit_id', 'location_id', 'manager_id',
            'role', 'role_id', 'is_active', 'is_admin', 'is_manager',
            'spending_limit', 'spending_limit_period', 'spending_limit_custom_days'
        }
        
        set_clauses = ["updated_at = CURRENT_TIMESTAMP"]
        values = []
        param_idx = 1
        
        for key, value in data.items():
            if key in valid_fields:
                set_clauses.append(f"{key} = ${param_idx}")
                values.append(value)
                param_idx += 1
        
        if len(set_clauses) == 1:  # Only updated_at
            return await cls.find_by_id(employee_id)
        
        values.append(employee_id)
        
        query = f"""
            UPDATE employees 
            SET {', '.join(set_clauses)}
            WHERE id = ${param_idx} 
            RETURNING *
        """
        result = await db.query(query, *values)
        return cls(result[0]) if result else None
    
    @classmethod
    async def delete(cls, employee_id: int, soft: bool = True) -> bool:
        """Delete employee (soft delete by default)"""
        if soft:
            result = await db.query("""
                UPDATE employees SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1 RETURNING id
            """, employee_id)
        else:
            # Hard delete with cascades
            await db.execute("""
                DELETE FROM claim_status_history 
                WHERE claim_id IN (SELECT id FROM claims WHERE employee_id = $1)
            """, employee_id)
            await db.execute("""
                DELETE FROM claim_receipts 
                WHERE claim_id IN (SELECT id FROM claims WHERE employee_id = $1)
            """, employee_id)
            await db.execute("""
                DELETE FROM claim_comments 
                WHERE claim_id IN (SELECT id FROM claims WHERE employee_id = $1)
            """, employee_id)
            await db.execute("DELETE FROM conversation_states WHERE employee_id = $1", employee_id)
            await db.execute("DELETE FROM claims WHERE employee_id = $1", employee_id)
            result = await db.query("DELETE FROM employees WHERE id = $1 RETURNING id", employee_id)
        
        return len(result) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert employee to dictionary"""
        return {
            'id': self.id,
            'employee_code': self.employee_code,
            'name': self.name,
            'phone_number': self.phone_number,
            'email': self.email,
            'role': self.role,
            'role_id': self.role_id,
            'permissions': self.permissions,
            'grade_id': self.grade_id,
            'grade_code': self.grade_code,
            'grade_name': self.grade_name,
            'unit_id': self.unit_id,
            'unit_code': self.unit_code,
            'unit_name': self.unit_name,
            'location_id': self.location_id,
            'location_code': self.location_code,
            'location_name': self.location_name,
            'manager_id': self.manager_id,
            'manager_name': self.manager_name,
            'manager_phone': self.manager_phone,
            'organization_id': self.organization_id,  # Was missing!
            'organization_name': self.organization_name, # Was missing!
            'whatsapp_chat_id': self.whatsapp_chat_id,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'is_manager': self.is_manager,
            'spending_limit': self.spending_limit,
            'spending_limit_period': self.spending_limit_period,
            'spending_limit_custom_days': self.spending_limit_custom_days
        }


# Backward compatibility - expose class methods as module functions
async def find_by_phone(phone_number: str):
    emp = await Employee.find_by_phone(phone_number)
    return emp.to_dict() if emp else None

async def find_by_chat_id(chat_id: str):
    emp = await Employee.find_by_chat_id(chat_id)
    return emp.to_dict() if emp else None

async def find_by_id(employee_id: int):
    emp = await Employee.find_by_id(employee_id)
    return emp.to_dict() if emp else None

async def link_chat_id(employee_id: int, chat_id: str):
    emp = await Employee.link_chat_id(employee_id, chat_id)
    return emp.to_dict() if emp else None

async def find_all():
    employees = await Employee.find_all()
    return [e.to_dict() for e in employees]

async def find_all_with_details(role: str = None, location_id: int = None, include_inactive: bool = False):
    employees = await Employee.find_all_with_details(role=role, location_id=location_id, include_inactive=include_inactive)
    return [e.to_dict() for e in employees]

async def create(data: dict):
    emp = await Employee.create(data)
    return emp.to_dict()

async def update(employee_id: int, data: dict):
    emp = await Employee.update(employee_id, data)
    return emp.to_dict() if emp else None

async def delete(employee_id: int):
    return await Employee.delete(employee_id)

async def hard_delete(employee_id: int):
    return await Employee.delete(employee_id, soft=False)

def normalize_phone_for_matching(phone: str):
    return Employee.normalize_phone(phone)
