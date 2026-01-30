"""
Base Model Class
Provides common database operations for all models using OOP patterns
"""

from abc import ABC
from typing import Optional, List, Dict, Any, TypeVar, Generic
from app.db.database import db

T = TypeVar('T', bound='BaseModel')


class BaseModel(ABC):
    """
    Abstract base class for all database models.
    Provides common CRUD operations with a consistent interface.
    """
    
    # Override in subclass
    table_name: str = ""
    primary_key: str = "id"
    
    def __init__(self, data: Dict[str, Any] = None):
        """Initialize model instance from data dictionary"""
        self._data = data or {}
        if data:
            for key, value in data.items():
                setattr(self, key, value)
    
    @classmethod
    async def find_by_id(cls, id: int) -> Optional[Dict[str, Any]]:
        """
        Find a single record by primary key.
        
        Args:
            id: The primary key value
            
        Returns:
            Record dict or None if not found
        """
        result = await db.query(
            f"SELECT * FROM {cls.table_name} WHERE {cls.primary_key} = $1",
            id
        )
        return result[0] if result else None
    
    @classmethod
    async def find_all(cls, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        Find all records, optionally including inactive ones.
        
        Args:
            include_inactive: Whether to include inactive records
            
        Returns:
            List of record dicts
        """
        query = f"SELECT * FROM {cls.table_name}"
        if not include_inactive and 'is_active' in cls._get_columns():
            query += " WHERE is_active = TRUE"
        query += f" ORDER BY {cls.primary_key}"
        return await db.query(query)
    
    @classmethod
    async def create(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new record.
        
        Args:
            data: Dictionary of column values
            
        Returns:
            Created record dict with all fields
        """
        columns = list(data.keys())
        values = list(data.values())
        placeholders = [f"${i+1}" for i in range(len(values))]
        
        query = f"""
            INSERT INTO {cls.table_name} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """
        result = await db.query(query, *values)
        return result[0] if result else {}
    
    @classmethod
    async def update(cls, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing record.
        
        Args:
            id: The primary key value
            data: Dictionary of column values to update
            
        Returns:
            Updated record dict or None if not found
        """
        if not data:
            return await cls.find_by_id(id)
        
        set_clauses = []
        values = []
        param_idx = 1
        
        # Always update updated_at if it exists
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        
        for key, value in data.items():
            set_clauses.append(f"{key} = ${param_idx}")
            values.append(value)
            param_idx += 1
        
        values.append(id)
        
        query = f"""
            UPDATE {cls.table_name}
            SET {', '.join(set_clauses)}
            WHERE {cls.primary_key} = ${param_idx}
            RETURNING *
        """
        result = await db.query(query, *values)
        return result[0] if result else None
    
    @classmethod
    async def delete(cls, id: int, soft: bool = True) -> bool:
        """
        Delete a record (soft or hard delete).
        
        Args:
            id: The primary key value
            soft: If True, set is_active=False; if False, actually delete
            
        Returns:
            True if deleted, False if not found
        """
        if soft:
            result = await db.query(
                f"""
                UPDATE {cls.table_name} 
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE {cls.primary_key} = $1
                RETURNING {cls.primary_key}
                """,
                id
            )
        else:
            result = await db.query(
                f"DELETE FROM {cls.table_name} WHERE {cls.primary_key} = $1 RETURNING {cls.primary_key}",
                id
            )
        return len(result) > 0
    
    @classmethod
    async def exists(cls, id: int) -> bool:
        """Check if a record exists by ID"""
        result = await db.query(
            f"SELECT 1 FROM {cls.table_name} WHERE {cls.primary_key} = $1",
            id
        )
        return len(result) > 0
    
    @classmethod
    async def count(cls, include_inactive: bool = False) -> int:
        """Count total records"""
        query = f"SELECT COUNT(*) as count FROM {cls.table_name}"
        if not include_inactive:
            query += " WHERE is_active = TRUE"
        result = await db.query(query)
        return result[0]['count'] if result else 0
    
    @classmethod
    def _get_columns(cls) -> List[str]:
        """Get column names - override if needed for optimization"""
        return ['is_active']  # Minimal default
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        return self._data.copy()
    
    def __repr__(self) -> str:
        """String representation"""
        return f"<{self.__class__.__name__}({self._data})>"
