"""
Organization Model
OOP class for organizations database operations
"""

from typing import Optional, List, Dict, Any
from app.models.base import BaseModel
from app.db.database import db


class Organization(BaseModel):
    """
    Organization model with database operations.
    Handles multi-tenant organization management.
    """
    
    table_name = "organizations"
    
    # Instance attributes
    id: int = None
    code: str = None
    name: str = None
    description: str = None
    is_active: bool = True
    
    def __init__(self, data: Dict[str, Any] = None):
        """Initialize organization from data dict"""
        super().__init__(data)
    
    @classmethod
    async def find_all(cls, include_inactive: bool = False) -> List['Organization']:
        """Get all organizations"""
        query = """
            SELECT id, code, name, description, is_active, created_at, updated_at
            FROM organizations
        """
        if not include_inactive:
            query += " WHERE is_active = TRUE"
        query += " ORDER BY name"
        
        result = await db.query(query)
        return [cls(row) for row in result]
    
    @classmethod
    async def find_by_id(cls, org_id: int) -> Optional['Organization']:
        """Find organization by ID"""
        result = await db.query_one("""
            SELECT id, code, name, description, is_active, created_at, updated_at
            FROM organizations
            WHERE id = $1
        """, org_id)
        return cls(result) if result else None
    
    @classmethod
    async def find_by_code(cls, code: str) -> Optional['Organization']:
        """Find organization by code"""
        result = await db.query_one("""
            SELECT id, code, name, description, is_active, created_at, updated_at
            FROM organizations
            WHERE code = $1
        """, code)
        return cls(result) if result else None
    
    @classmethod
    async def create(cls, data: Dict[str, Any]) -> 'Organization':
        """Create new organization"""
        rows = await db.query("""
            INSERT INTO organizations (code, name, description, is_active)
            VALUES ($1, $2, $3, $4)
            RETURNING id, code, name, description, is_active, created_at, updated_at
        """, data['code'], data['name'], data.get('description'), data.get('is_active', True))
        return cls(rows[0]) if rows else None
    
    @classmethod
    async def update(cls, org_id: int, data: Dict[str, Any]) -> Optional['Organization']:
        """Update organization"""
        rows = await db.query("""
            UPDATE organizations
            SET code = COALESCE($2, code),
                name = COALESCE($3, name),
                description = COALESCE($4, description),
                is_active = COALESCE($5, is_active),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING id, code, name, description, is_active, created_at, updated_at
        """, org_id, data.get('code'), data.get('name'), data.get('description'), data.get('is_active'))
        return cls(rows[0]) if rows else None
    
    @classmethod
    async def delete(cls, org_id: int, soft: bool = True) -> bool:
        """Soft delete organization"""
        result = await db.execute("""
            UPDATE organizations SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """, org_id)
        return result == "UPDATE 1"
    
    @classmethod
    async def get_units(cls, org_id: int) -> List[Dict[str, Any]]:
        """Get all units (departments) for an organization"""
        return await db.query("""
            SELECT id, code, name, organization_id, is_active, created_at, updated_at
            FROM units
            WHERE organization_id = $1 AND is_active = TRUE
            ORDER BY name
        """, org_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert organization to dictionary"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active
        }


# Backward compatibility - expose class methods as module functions
async def find_all():
    orgs = await Organization.find_all()
    return [o.to_dict() for o in orgs]

async def find_by_id(org_id: int):
    org = await Organization.find_by_id(org_id)
    return org.to_dict() if org else None

async def find_by_code(code: str):
    org = await Organization.find_by_code(code)
    return org.to_dict() if org else None

async def create(data: dict):
    org = await Organization.create(data)
    return org.to_dict() if org else None

async def update(org_id: int, data: dict):
    org = await Organization.update(org_id, data)
    return org.to_dict() if org else None

async def delete(org_id: int):
    return await Organization.delete(org_id)

async def get_units(org_id: int):
    return await Organization.get_units(org_id)
