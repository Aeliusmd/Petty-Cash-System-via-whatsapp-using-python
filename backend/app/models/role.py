from datetime import datetime
from typing import Optional, List
from app.db import db
from pydantic import BaseModel

class Role(BaseModel):
    id: Optional[int] = None
    code: str
    name: str
    description: Optional[str] = None
    organization_id: Optional[int] = None
    parent_role_id: Optional[int] = None
    is_system_role: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    async def find_all(cls, organization_id: int = None, include_system: bool = True):
        """
        Get all roles.
        If organization_id is provided, fetches org-specific roles + global system roles.
        """
        query = "SELECT * FROM roles WHERE is_active = TRUE"
        params = []
        
        if organization_id:
            query += " AND (organization_id = $1"
            params.append(organization_id)
            if include_system:
                query += " OR organization_id IS NULL"
            query += ")"
        elif not include_system:
            query += " AND organization_id IS NOT NULL"
            
        rows = await db.query(query, *params)
        return [cls(**row) for row in rows]

    @classmethod
    async def find_by_id(cls, role_id: int):
        query = "SELECT * FROM roles WHERE id = $1"
        row = await db.query_one(query, role_id)
        return cls(**row) if row else None

    @classmethod
    async def find_by_code(cls, code: str, organization_id: int = None):
        query = "SELECT * FROM roles WHERE code = $1"
        params = [code]
        
        if organization_id:
            query += " AND (organization_id = $2 OR organization_id IS NULL)"
            params.append(organization_id)
            
        row = await db.query_one(query, *params)
        return cls(**row) if row else None

    @classmethod
    async def create(cls, data: dict):
        query = """
            INSERT INTO roles (code, name, description, organization_id, parent_role_id, is_system_role, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """
        role_id = await db.fetchval(
            query, 
            data.get('code'),
            data.get('name'),
            data.get('description'),
            data.get('organization_id'),
            data.get('parent_role_id'),
            data.get('is_system_role', False),
            data.get('is_active', True)  # Default to active
        )
        return await cls.find_by_id(role_id)

    @classmethod
    async def update(cls, role_id: int, data: dict):
        if not data:
            return await cls.find_by_id(role_id)
        
        # Build dynamic query with positional parameters
        set_clauses = []
        values = []
        param_idx = 1
        
        for key, value in data.items():
            set_clauses.append(f"{key} = ${param_idx}")
            values.append(value)
            param_idx += 1
            
        # Add role_id as last parameter
        values.append(role_id)
        
        query = f"""
            UPDATE roles 
            SET {', '.join(set_clauses)}, updated_at = NOW() 
            WHERE id = ${param_idx}
        """
        await db.execute(query, *values)
        return await cls.find_by_id(role_id)

    @classmethod
    async def delete(cls, role_id: int):
        """Soft delete"""
        query = "UPDATE roles SET is_active = FALSE WHERE id = $1"
        await db.execute(query, role_id)

    async def get_permissions(self) -> List[str]:
        """
        Get all permissions including inherited ones via Recursive CTE
        """
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
        rows = await db.query(query, self.id)
        return [row['code'] for row in rows]
