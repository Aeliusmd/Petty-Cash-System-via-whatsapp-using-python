"""
Rates Model
OOP classes for batta rates, category caps, locations, and grades
"""

from typing import Optional, List, Dict, Any
from app.models.base import BaseModel
from app.db.database import db


class Location(BaseModel):
    """Location model"""
    
    table_name = "locations"
    
    id: int = None
    code: str = None
    name: str = None
    is_active: bool = True
    
    def __init__(self, data: Dict[str, Any] = None):
        super().__init__(data)
    
    @classmethod
    async def find_all(cls, include_inactive: bool = False) -> List['Location']:
        """Get all locations"""
        query = "SELECT id, code, name, is_active FROM locations"
        if not include_inactive:
            query += " WHERE is_active = TRUE"
        query += " ORDER BY name"
        result = await db.query(query)
        return [cls(row) for row in result]
    
    @classmethod
    async def find_by_id(cls, location_id: int) -> Optional['Location']:
        """Find location by ID"""
        result = await db.query_one("SELECT id, code, name, is_active FROM locations WHERE id = $1", location_id)
        return cls(result) if result else None
    
    @classmethod
    async def find(cls, search: str) -> Optional['Location']:
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
        return cls(result[0]) if result else None
    
    def to_dict(self) -> Dict[str, Any]:
        return {'id': self.id, 'code': self.code, 'name': self.name, 'is_active': self.is_active}


class Grade(BaseModel):
    """Grade model"""
    
    table_name = "grades"
    
    id: int = None
    code: str = None
    name: str = None
    is_active: bool = True
    
    def __init__(self, data: Dict[str, Any] = None):
        super().__init__(data)
    
    @classmethod
    async def find_all(cls, include_inactive: bool = False) -> List['Grade']:
        """Get all grades"""
        query = "SELECT id, code, name, is_active FROM grades"
        if not include_inactive:
            query += " WHERE is_active = TRUE"
        query += " ORDER BY code"
        result = await db.query(query)
        return [cls(row) for row in result]
    
    @classmethod
    async def find_by_id(cls, grade_id: int) -> Optional['Grade']:
        """Find grade by ID"""
        result = await db.query_one("SELECT id, code, name, is_active FROM grades WHERE id = $1", grade_id)
        return cls(result) if result else None
    
    def to_dict(self) -> Dict[str, Any]:
        return {'id': self.id, 'code': self.code, 'name': self.name, 'is_active': self.is_active}


class BattaRate(BaseModel):
    """Batta Rate model"""
    
    table_name = "batta_rates"
    
    id: int = None
    grade_id: int = None
    location_id: int = None
    rate_per_day: float = None
    effective_from: str = None
    effective_to: str = None
    is_active: bool = True
    
    # Joined fields
    grade_code: str = None
    grade_name: str = None
    location_code: str = None
    location_name: str = None
    
    def __init__(self, data: Dict[str, Any] = None):
        super().__init__(data)
    
    @classmethod
    async def get_rate(cls, grade_id: int, location_id: int) -> float:
        """Get current batta rate for grade and location"""
        result = await db.query("""
            SELECT rate_per_day FROM batta_rates
            WHERE grade_id = $1 AND location_id = $2 AND is_active = TRUE
              AND effective_from <= CURRENT_DATE
              AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)
            ORDER BY effective_from DESC LIMIT 1
        """, grade_id, location_id)
        return float(result[0]['rate_per_day']) if result else 0
    
    @classmethod
    async def get_rate_by_code(cls, grade_code: str, location_code: str) -> Optional['BattaRate']:
        """Get batta rate by grade and location codes"""
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
        return cls(result[0]) if result else None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'grade_id': self.grade_id,
            'grade_code': self.grade_code,
            'grade_name': self.grade_name,
            'location_id': self.location_id,
            'location_code': self.location_code,
            'location_name': self.location_name,
            'rate_per_day': self.rate_per_day,
            'is_active': self.is_active
        }


class CategoryCap(BaseModel):
    """Category Cap model"""
    
    table_name = "category_caps"
    
    id: int = None
    category_id: int = None
    grade_id: int = None
    max_amount: float = None
    period: str = None
    is_active: bool = True
    
    # Joined fields
    category_code: str = None
    category_name: str = None
    
    def __init__(self, data: Dict[str, Any] = None):
        super().__init__(data)
    
    @classmethod
    async def get_cap(cls, category_id: int, grade_id: Optional[int] = None) -> Optional['CategoryCap']:
        """Get category cap for a category, optionally by grade"""
        result = await db.query("""
            SELECT cc.max_amount, cc.period, c.code as category_code, c.name as category_name
            FROM category_caps cc
            JOIN claim_categories c ON cc.category_id = c.id
            WHERE cc.category_id = $1 AND (cc.grade_id IS NULL OR cc.grade_id = $2)
              AND cc.is_active = TRUE AND cc.effective_from <= CURRENT_DATE
              AND (cc.effective_to IS NULL OR cc.effective_to >= CURRENT_DATE)
            ORDER BY cc.grade_id NULLS LAST LIMIT 1
        """, category_id, grade_id)
        return cls(result[0]) if result else None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'category_id': self.category_id,
            'category_code': self.category_code,
            'category_name': self.category_name,
            'grade_id': self.grade_id,
            'max_amount': self.max_amount,
            'period': self.period
        }


# Backward compatibility - expose class methods as module functions
async def get_batta_rate(grade_id: int, location_id: int):
    return await BattaRate.get_rate(grade_id, location_id)

async def get_batta_rate_by_code(grade_code: str, location_code: str):
    rate = await BattaRate.get_rate_by_code(grade_code, location_code)
    return rate.to_dict() if rate else None

async def get_all_locations():
    locations = await Location.find_all()
    return [l.to_dict() for l in locations]

async def find_location(search: str):
    loc = await Location.find(search)
    return loc.to_dict() if loc else None

async def get_category_cap(category_id: int, grade_id: int = None):
    cap = await CategoryCap.get_cap(category_id, grade_id)
    return cap.to_dict() if cap else None

async def get_all_categories():
    from app.models.category import Category
    categories = await Category.find_all()
    return [c.to_dict() for c in categories]

async def find_category(search: str):
    from app.models.category import Category
    cat = await Category.find_by_code(search)
    return cat.to_dict() if cat else None

async def find_category_by_id(category_id: int):
    from app.models.category import Category
    cat = await Category.find_by_id(category_id)
    return cat.to_dict() if cat else None

async def get_all_grades():
    grades = await Grade.find_all()
    return [g.to_dict() for g in grades]
