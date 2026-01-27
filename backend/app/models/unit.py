"""
Unit (Organization) Model
Handles CRUD operations for organizational units/departments
"""
from typing import Optional, List
from app.db.database import db


async def find_all() -> List[dict]:
    """Get all active units"""
    return await db.query("""
        SELECT id, code, name, organization_id, is_active, created_at, updated_at
        FROM units
        WHERE is_active = TRUE
        ORDER BY name
    """)


async def find_by_id(unit_id: int) -> Optional[dict]:
    """Find unit by ID"""
    return await db.query_one("""
        SELECT id, code, name, organization_id, is_active, created_at, updated_at
        FROM units
        WHERE id = $1
    """, unit_id)


async def create(data: dict) -> dict:
    """Create new unit"""
    rows = await db.query("""
        INSERT INTO units (code, name, organization_id, is_active)
        VALUES ($1, $2, $3, $4)
        RETURNING id, code, name, organization_id, is_active, created_at, updated_at
    """, data['code'], data['name'], data.get('organization_id'), data.get('is_active', True))
    return rows[0] if rows else None


async def update(unit_id: int, data: dict) -> Optional[dict]:
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
    return rows[0] if rows else None


async def delete(unit_id: int) -> bool:
    """Soft delete unit"""
    result = await db.execute("""
        UPDATE units SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
        WHERE id = $1
    """, unit_id)
    return result == "UPDATE 1"

