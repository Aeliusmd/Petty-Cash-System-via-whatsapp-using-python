"""
Rates Model - Database operations for batta rates and category caps
"""

from typing import Optional
from app.db.database import db


async def get_batta_rate(grade_id: int, location_id: int) -> float:
    """Get batta rate for grade and location"""
    result = await db.query("""
        SELECT rate_per_day FROM batta_rates
        WHERE grade_id = $1 AND location_id = $2 AND is_active = TRUE
          AND effective_from <= CURRENT_DATE
          AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)
        ORDER BY effective_from DESC LIMIT 1
    """, grade_id, location_id)
    
    return float(result[0]['rate_per_day']) if result else 0


async def get_batta_rate_by_code(grade_code: str, location_code: str) -> Optional[dict]:
    """Get batta rate by grade code and location code"""
    result = await db.query("""
        SELECT br.rate_per_day, g.code as grade_code, g.name as grade_name,
               l.code as location_code, l.name as location_name
        FROM batta_rates br
        JOIN grades g ON br.grade_id = g.id
        JOIN locations l ON br.location_id = l.id
        WHERE g.code = $1 AND l.code = $2 AND br.is_active = TRUE
          AND br.effective_from <= CURRENT_DATE
          AND (br.effective_to IS NULL OR br.effective_to >= CURRENT_DATE)
        ORDER BY br.effective_from DESC LIMIT 1
    """, grade_code.upper(), location_code.upper())
    
    return result[0] if result else None


async def get_all_locations() -> list[dict]:
    """Get all active locations"""
    return await db.query("""
        SELECT id, code, name FROM locations
        WHERE is_active = TRUE ORDER BY name
    """)


async def find_location(search: str) -> Optional[dict]:
    """Find location by name or code (fuzzy match)"""
    normalized = search.strip().lower()
    
    result = await db.query("""
        SELECT id, code, name FROM locations
        WHERE is_active = TRUE AND (
            LOWER(code) = $1 OR LOWER(name) = $1 OR LOWER(name) LIKE $2
        )
        ORDER BY CASE WHEN LOWER(code) = $1 THEN 1
                      WHEN LOWER(name) = $1 THEN 2 ELSE 3 END
        LIMIT 1
    """, normalized, f"%{normalized}%")
    
    return result[0] if result else None


async def get_category_cap(category_id: int, grade_id: Optional[int] = None) -> Optional[dict]:
    """Get category cap"""
    result = await db.query("""
        SELECT cc.max_amount, cc.period, c.code as category_code, c.name as category_name
        FROM category_caps cc
        JOIN claim_categories c ON cc.category_id = c.id
        WHERE cc.category_id = $1 AND (cc.grade_id IS NULL OR cc.grade_id = $2)
          AND cc.is_active = TRUE AND cc.effective_from <= CURRENT_DATE
          AND (cc.effective_to IS NULL OR cc.effective_to >= CURRENT_DATE)
        ORDER BY cc.grade_id NULLS LAST LIMIT 1
    """, category_id, grade_id)
    
    return result[0] if result else None


async def get_all_categories() -> list[dict]:
    """Get all claim categories"""
    return await db.query("""
        SELECT id, code, name, description, requires_receipt
        FROM claim_categories WHERE is_active = TRUE ORDER BY display_order
    """)


async def find_category(search: str) -> Optional[dict]:
    """Find category by code or name"""
    normalized = search.strip().lower()
    
    result = await db.query("""
        SELECT id, code, name, description, requires_receipt
        FROM claim_categories
        WHERE is_active = TRUE AND (LOWER(code) = $1 OR LOWER(name) LIKE $2)
        LIMIT 1
    """, normalized, f"%{normalized}%")
    
    return result[0] if result else None


async def get_all_grades() -> list[dict]:
    """Get all grades"""
    return await db.query("""
        SELECT id, code, name FROM grades
        WHERE is_active = TRUE ORDER BY code
    """)
