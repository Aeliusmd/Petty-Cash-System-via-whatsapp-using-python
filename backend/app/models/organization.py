"""
Organization Model - Database operations for organizations table
"""
from typing import Optional, List
from app.db.database import db


async def find_all() -> List[dict]:
    """Get all active organizations"""
    return await db.query("""
        SELECT id, code, name, description, is_active, created_at, updated_at
        FROM organizations
        WHERE is_active = TRUE
        ORDER BY name
    """)


async def find_by_id(org_id: int) -> Optional[dict]:
    """Find organization by ID"""
    return await db.query_one("""
        SELECT id, code, name, description, is_active, created_at, updated_at
        FROM organizations
        WHERE id = $1
    """, org_id)


async def find_by_code(code: str) -> Optional[dict]:
    """Find organization by code"""
    return await db.query_one("""
        SELECT id, code, name, description, is_active, created_at, updated_at
        FROM organizations
        WHERE code = $1
    """, code)


async def create(data: dict) -> dict:
    """Create new organization"""
    rows = await db.query("""
        INSERT INTO organizations (code, name, description, is_active)
        VALUES ($1, $2, $3, $4)
        RETURNING id, code, name, description, is_active, created_at, updated_at
    """, data['code'], data['name'], data.get('description'), data.get('is_active', True))
    return rows[0] if rows else None


async def update(org_id: int, data: dict) -> Optional[dict]:
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
    return rows[0] if rows else None


async def delete(org_id: int) -> bool:
    """Soft delete organization"""
    result = await db.execute("""
        UPDATE organizations SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
        WHERE id = $1
    """, org_id)
    return result == "UPDATE 1"


async def get_units(org_id: int) -> List[dict]:
    """Get all units (departments) for an organization"""
    return await db.query("""
        SELECT id, code, name, organization_id, is_active, created_at, updated_at
        FROM units
        WHERE organization_id = $1 AND is_active = TRUE
        ORDER BY name
    """, org_id)

