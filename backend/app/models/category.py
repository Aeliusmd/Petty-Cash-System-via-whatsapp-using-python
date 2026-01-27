"""
Category Model - Database operations for claim_categories table
Supports department-specific categories
"""
from typing import Optional, List
from app.db.database import db


async def find_all() -> List[dict]:
    """Get all active categories (global, unit_id is NULL)"""
    return await db.query("""
        SELECT id, code, name, description, requires_receipt, is_active, display_order, unit_id, prompt_message, created_at, updated_at
        FROM claim_categories
        WHERE is_active = TRUE AND unit_id IS NULL
        ORDER BY display_order, name
    """)


async def find_by_unit(unit_id: int) -> List[dict]:
    """Get all active categories for a specific unit (department)"""
    return await db.query("""
        SELECT id, code, name, description, requires_receipt, is_active, display_order, unit_id, prompt_message, created_at, updated_at
        FROM claim_categories
        WHERE is_active = TRUE AND unit_id = $1
        ORDER BY display_order, name
    """, unit_id)


async def find_by_id(category_id: int) -> Optional[dict]:
    """Find category by ID"""
    return await db.query_one("""
        SELECT id, code, name, description, requires_receipt, is_active, display_order, unit_id, prompt_message, created_at, updated_at
        FROM claim_categories
        WHERE id = $1
    """, category_id)


async def find_by_code(code: str, unit_id: int = None) -> Optional[dict]:
    """Find category by code, optionally scoped to a unit"""
    if unit_id:
        return await db.query_one("""
            SELECT id, code, name, description, requires_receipt, is_active, display_order, unit_id, prompt_message, created_at, updated_at
            FROM claim_categories
            WHERE code = $1 AND unit_id = $2
        """, code, unit_id)
    else:
        return await db.query_one("""
            SELECT id, code, name, description, requires_receipt, is_active, display_order, unit_id, prompt_message, created_at, updated_at
            FROM claim_categories
            WHERE code = $1 AND unit_id IS NULL
        """, code)


async def create(data: dict) -> dict:
    """Create new category"""
    rows = await db.query("""
        INSERT INTO claim_categories (code, name, description, requires_receipt, display_order, unit_id, prompt_message, is_active)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id, code, name, description, requires_receipt, is_active, display_order, unit_id, prompt_message, created_at, updated_at
    """, data['code'], data['name'], data.get('description'), 
        data.get('requires_receipt', False), data.get('display_order', 0), 
        data.get('unit_id'), data.get('prompt_message'), data.get('is_active', True))
    return rows[0] if rows else None


async def update(category_id: int, data: dict) -> Optional[dict]:
    """Update category"""
    rows = await db.query("""
        UPDATE claim_categories
        SET code = COALESCE($2, code),
            name = COALESCE($3, name),
            description = COALESCE($4, description),
            requires_receipt = COALESCE($5, requires_receipt),
            display_order = COALESCE($6, display_order),
            prompt_message = COALESCE($7, prompt_message),
            is_active = COALESCE($8, is_active),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $1
        RETURNING id, code, name, description, requires_receipt, is_active, display_order, unit_id, prompt_message, created_at, updated_at
    """, category_id, data.get('code'), data.get('name'), data.get('description'),
        data.get('requires_receipt'), data.get('display_order'), 
        data.get('prompt_message'), data.get('is_active'))
    return rows[0] if rows else None


async def delete(category_id: int) -> bool:
    """Soft delete category"""
    result = await db.execute("""
        UPDATE claim_categories SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
        WHERE id = $1
    """, category_id)
    return result == "UPDATE 1"


async def copy_to_unit(category_id: int, unit_id: int) -> Optional[dict]:
    """Copy a global category to a specific unit"""
    source = await find_by_id(category_id)
    if not source:
        return None
    
    return await create({
        'code': source['code'],
        'name': source['name'],
        'description': source['description'],
        'requires_receipt': source['requires_receipt'],
        'display_order': source['display_order'],
        'prompt_message': source.get('prompt_message'),
        'unit_id': unit_id,
        'is_active': True
    })

