"""
Unit Model
OOP class for units (departments) database operations
"""

from typing import Optional, List, Dict, Any
from app.models.base import BaseModel
from app.db.database import db


class Unit(BaseModel):
    """
    Unit model with database operations.
    Represents organizational units/departments.
    """
    
    table_name = "units"
    
    # Instance attributes
    id: int = None
    code: str = None
    name: str = None
    organization_id: int = None
    is_active: bool = True
    
    def __init__(self, data: Dict[str, Any] = None):
        """Initialize unit from data dict"""
        super().__init__(data)
    
    @classmethod
    async def find_by_organization(cls, organization_id: int) -> List['Unit']:
        """Get units for an organization"""
        result = await db.query(f"""
            SELECT * FROM {cls.table_name} 
            WHERE organization_id = $1 AND is_active = TRUE
            ORDER BY name
        """, organization_id)
        return [cls(row) for row in result]

    @classmethod
    async def find_all(cls, include_inactive: bool = False) -> List['Unit']:
        """Get all units"""
        query = """
            SELECT id, code, name, organization_id, is_active, created_at, updated_at
            FROM units
        """
        if not include_inactive:
            query += " WHERE is_active = TRUE"
        query += " ORDER BY name"
        
        result = await db.query(query)
        return [cls(row) for row in result]
    
    @classmethod
    async def find_by_organization(cls, organization_id: int, include_inactive: bool = False) -> List['Unit']:
        """Get all units for an organization"""
        query = """
            SELECT id, code, name, organization_id, is_active, created_at, updated_at
            FROM units
            WHERE organization_id = $1
        """
        if not include_inactive:
            query += " AND is_active = TRUE"
        query += " ORDER BY name"
        
        result = await db.query(query, organization_id)
        return [cls(row) for row in result]
    
    @classmethod
    async def find_by_id(cls, unit_id: int) -> Optional['Unit']:
        """Find unit by ID"""
        result = await db.query_one("""
            SELECT id, code, name, organization_id, is_active, created_at, updated_at
            FROM units
            WHERE id = $1
        """, unit_id)
        return cls(result) if result else None
    
    @classmethod
    async def create(cls, data: Dict[str, Any]) -> 'Unit':
        """Create new unit"""
        rows = await db.query("""
            INSERT INTO units (code, name, organization_id, is_active)
            VALUES ($1, $2, $3, $4)
            RETURNING id, code, name, organization_id, is_active, created_at, updated_at
        """, data['code'], data['name'], data.get('organization_id'), data.get('is_active', True))
        return cls(rows[0]) if rows else None
    
    @classmethod
    async def update(cls, unit_id: int, data: Dict[str, Any]) -> Optional['Unit']:
        """Update unit"""
        rows = await db.query("""
            UPDATE units
            SET code = COALESCE($2, code),
                name = COALESCE($3, name),
                organization_id = COALESCE($4, organization_id),
                is_active = COALESCE($5, is_active),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING id, code, name, organization_id, is_active, created_at, updated_at
        """, unit_id, data.get('code'), data.get('name'), data.get('organization_id'), data.get('is_active'))
        return cls(rows[0]) if rows else None
    
    @classmethod
    async def delete(cls, unit_id: int, soft: bool = True) -> bool:
        """Soft delete unit"""
        result = await db.execute("""
            UPDATE units SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """, unit_id)
        return result == "UPDATE 1"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert unit to dictionary"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'organization_id': self.organization_id,
            'is_active': self.is_active
        }


# Backward compatibility - expose class methods as module functions
async def find_all():
    units = await Unit.find_all()
    return [u.to_dict() for u in units]

async def find_by_id(unit_id: int):
    unit = await Unit.find_by_id(unit_id)
    return unit.to_dict() if unit else None

async def create(data: dict):
    unit = await Unit.create(data)
    return unit.to_dict() if unit else None

async def update(unit_id: int, data: dict):
    unit = await Unit.update(unit_id, data)
    return unit.to_dict() if unit else None

async def delete(unit_id: int):
    return await Unit.delete(unit_id)
