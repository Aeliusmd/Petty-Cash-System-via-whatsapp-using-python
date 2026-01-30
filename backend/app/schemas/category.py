"""
Category Schemas
Pydantic models for category endpoints
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CategoryBase(BaseModel):
    """Base category fields"""
    code: str
    name: str
    description: Optional[str] = None
    requires_receipt: bool = False
    display_order: int = 0
    unit_id: Optional[int] = None
    prompt_message: Optional[str] = None
    is_active: bool = True


class CategoryCreate(CategoryBase):
    """Request for creating category"""
    pass


class CategoryUpdate(BaseModel):
    """Request for updating category"""
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    requires_receipt: Optional[bool] = None
    display_order: Optional[int] = None
    unit_id: Optional[int] = None
    prompt_message: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryResponse(CategoryBase):
    """Category response"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    unit_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    """Response for listing categories"""
    categories: List[CategoryResponse]
