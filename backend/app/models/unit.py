"""
Unit (Organization) Model
Handles CRUD operations for organizational units/departments
"""
import asyncpg
from typing import Optional, List
from app.db.database import get_db_pool


async def find_all() -> List[dict]:
    """Get all active units"""
    pool = await get_db_pool()
    async with pool.acquire() as db:
        rows = await db.fetch("""
            SELECT id, code, name, is_active, created_at, updated_at
            FROM units
            WHERE is_active = TRUE
            ORDER BY name
        """)
        return [dict(row) for row in rows]


async def find_by_id(unit_id: int) -> Optional[dict]:
    """Find unit by ID"""
    pool = await get_db_pool()
    async with pool.acquire() as db:
        row = await db.fetchrow("""
            SELECT id, code, name, is_active, created_at, updated_at
            FROM units
            WHERE id = $1
        """, unit_id)
        return dict(row) if row else None


async def create(data: dict) -> dict:
    """Create new unit"""
    pool = await get_db_pool()
    async with pool.acquire() as db:
        row = await db.fetchrow("""
            INSERT INTO units (code, name, is_active)
            VALUES ($1, $2, $3)
            RETURNING id, code, name, is_active, created_at, updated_at
        """, data['code'], data['name'], data.get('is_active', True))
        return dict(row)


async def update(unit_id: int, data: dict) -> Optional[dict]:
    """Update unit"""
    pool = await get_db_pool()
    async with pool.acquire() as db:
        row = await db.fetchrow("""
            UPDATE units
            SET code = COALESCE($2, code),
                name = COALESCE($3, name),
                is_active = COALESCE($4, is_active)
            WHERE id = $1
            RETURNING id, code, name, is_active, created_at, updated_at
        """, unit_id, data.get('code'), data.get('name'), data.get('is_active'))
        return dict(row) if row else None


async def delete(unit_id: int) -> bool:
    """Soft delete unit"""
    pool = await get_db_pool()
    async with pool.acquire() as db:
        result = await db.execute("""
            UPDATE units SET is_active = FALSE WHERE id = $1
        """, unit_id)
        return result == "UPDATE 1"
