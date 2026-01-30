"""
Category Model
OOP class for claim_categories database operations
"""

from typing import Optional, List, Dict, Any
from app.models.base import BaseModel
from app.db.database import db


class Category(BaseModel):
    """
    Category model with database operations.
    Supports department-specific categories.
    """
    
    table_name = "claim_categories"
    
    # Instance attributes
    id: int = None
    code: str = None
    name: str = None
    description: str = None
    requires_receipt: bool = False
    is_active: bool = True
    display_order: int = 0
    unit_id: int = None
    prompt_message: str = None
    
    def __init__(self, data: Dict[str, Any] = None):
        """Initialize category from data dict"""
        super().__init__(data)
    
    @classmethod
    async def find_all(cls, include_inactive: bool = False) -> List['Category']:
        """Get all global categories (unit_id is NULL)"""
        query = """
            SELECT id, code, name, description, requires_receipt, is_active, 
                   display_order, unit_id, prompt_message, created_at, updated_at
            FROM claim_categories
            WHERE unit_id IS NULL
        """
        if not include_inactive:
            query += " AND is_active = TRUE"
        query += " ORDER BY display_order, name"
        
        result = await db.query(query)
        return [cls(row) for row in result]
    
    @classmethod
    async def find_by_unit(cls, unit_id: int, include_inactive: bool = False) -> List['Category']:
        """Get all categories for a specific unit (department)"""
        query = """
            SELECT id, code, name, description, requires_receipt, is_active, 
                   display_order, unit_id, prompt_message, created_at, updated_at
            FROM claim_categories
            WHERE unit_id = $1
        """
        if not include_inactive:
            query += " AND is_active = TRUE"
        query += " ORDER BY display_order, name"
        
        result = await db.query(query, unit_id)
        return [cls(row) for row in result]
    
    @classmethod
    async def find_by_id(cls, category_id: int) -> Optional['Category']:
        """Find category by ID"""
        result = await db.query_one("""
            SELECT id, code, name, description, requires_receipt, is_active, 
                   display_order, unit_id, prompt_message, created_at, updated_at
            FROM claim_categories
            WHERE id = $1
        """, category_id)
        return cls(result) if result else None
    
    @classmethod
    async def find_by_code(cls, code: str, unit_id: int = None) -> Optional['Category']:
        """Find category by code, optionally scoped to a unit"""
        if unit_id:
            result = await db.query_one("""
                SELECT id, code, name, description, requires_receipt, is_active, 
                       display_order, unit_id, prompt_message, created_at, updated_at
                FROM claim_categories
                WHERE code = $1 AND unit_id = $2
            """, code, unit_id)
        else:
            result = await db.query_one("""
                SELECT id, code, name, description, requires_receipt, is_active, 
                       display_order, unit_id, prompt_message, created_at, updated_at
                FROM claim_categories
                WHERE code = $1 AND unit_id IS NULL
            """, code)
        return cls(result) if result else None
    
    @classmethod
    async def create(cls, data: Dict[str, Any]) -> 'Category':
        """Create new category"""
        rows = await db.query("""
            INSERT INTO claim_categories (code, name, description, requires_receipt, 
                                          display_order, unit_id, prompt_message, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, code, name, description, requires_receipt, is_active, 
                      display_order, unit_id, prompt_message, created_at, updated_at
        """, data['code'], data['name'], data.get('description'), 
            data.get('requires_receipt', False), data.get('display_order', 0), 
            data.get('unit_id'), data.get('prompt_message'), data.get('is_active', True))
        return cls(rows[0]) if rows else None
    
    @classmethod
    async def update(cls, category_id: int, data: Dict[str, Any]) -> Optional['Category']:
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
            RETURNING id, code, name, description, requires_receipt, is_active, 
                      display_order, unit_id, prompt_message, created_at, updated_at
        """, category_id, data.get('code'), data.get('name'), data.get('description'),
            data.get('requires_receipt'), data.get('display_order'), 
            data.get('prompt_message'), data.get('is_active'))
        return cls(rows[0]) if rows else None
    
    @classmethod
    async def delete(cls, category_id: int, soft: bool = True) -> bool:
        """Soft delete category"""
        result = await db.execute("""
            UPDATE claim_categories SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """, category_id)
        return result == "UPDATE 1"
    
    @classmethod
    async def copy_to_unit(cls, category_id: int, unit_id: int) -> Optional['Category']:
        """Copy a global category to a specific unit"""
        source = await cls.find_by_id(category_id)
        if not source:
            return None
        
        return await cls.create({
            'code': source.code,
            'name': source.name,
            'description': source.description,
            'requires_receipt': source.requires_receipt,
            'display_order': source.display_order,
            'prompt_message': source.prompt_message,
            'unit_id': unit_id,
            'is_active': True
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert category to dictionary"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'requires_receipt': self.requires_receipt,
            'is_active': self.is_active,
            'display_order': self.display_order,
            'unit_id': self.unit_id,
            'prompt_message': self.prompt_message
        }


# Backward compatibility - expose class methods as module functions
async def find_all():
    categories = await Category.find_all()
    return [c.to_dict() for c in categories]

async def find_by_unit(unit_id: int):
    categories = await Category.find_by_unit(unit_id)
    return [c.to_dict() for c in categories]

async def find_by_id(category_id: int):
    cat = await Category.find_by_id(category_id)
    return cat.to_dict() if cat else None

async def find_by_code(code: str, unit_id: int = None):
    cat = await Category.find_by_code(code, unit_id)
    return cat.to_dict() if cat else None

async def create(data: dict):
    cat = await Category.create(data)
    return cat.to_dict() if cat else None

async def update(category_id: int, data: dict):
    cat = await Category.update(category_id, data)
    return cat.to_dict() if cat else None

async def delete(category_id: int):
    return await Category.delete(category_id)

async def copy_to_unit(category_id: int, unit_id: int):
    cat = await Category.copy_to_unit(category_id, unit_id)
    return cat.to_dict() if cat else None
