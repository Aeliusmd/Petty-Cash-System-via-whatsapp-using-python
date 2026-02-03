from datetime import datetime
from typing import Optional, List
from app.db import db
from pydantic import BaseModel

class Permission(BaseModel):
    id: Optional[int] = None
    code: str
    resource: str
    action: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    @classmethod
    async def find_all(cls, category: str = None):
        query = "SELECT * FROM permissions WHERE is_active = TRUE"
        params = []
        if category:
            query += " AND category = $1"
            params.append(category)
        query += " ORDER BY category, code"
        rows = await db.query(query, *params)
        return [cls(**row) for row in rows]

    @classmethod
    async def find_by_code(cls, code: str):
        query = "SELECT * FROM permissions WHERE code = $1"
        row = await db.query_one(query, code)
        return cls(**row) if row else None

    @classmethod
    async def get_categories(cls) -> List[str]:
        query = "SELECT DISTINCT category FROM permissions WHERE category IS NOT NULL ORDER BY category"
        rows = await db.query(query)
        return [row['category'] for row in rows]
