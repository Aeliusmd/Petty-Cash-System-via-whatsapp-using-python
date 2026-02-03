"""
Category Controller
API routes for category management
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from app.controllers.base import BaseController
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.utils.auth import require_permission, require_authenticated


class CategoryController(BaseController):
    """Controller for category management endpoints"""
    
    prefix = "/api/categories"
    tags = ["Categories"]
    
    def __init__(self):
        super().__init__()
    
    def _register_routes(self):
        """Register category routes"""
        self.router.get("/")(self.get_categories)
        self.router.get("/{category_id}")(self.get_category)
        self.router.post("/")(self.create_category)
        self.router.put("/{category_id}")(self.update_category)
        self.router.delete("/{category_id}")(self.delete_category)
    
    async def get_categories(
        self,
        unit_id: Optional[int] = None,
        include_inactive: bool = False,
        auth: dict = Depends(require_authenticated)
    ):
        """Get all categories, optionally filtered by unit"""
        if unit_id:
            categories = await Category.find_by_unit(unit_id, include_inactive)
        else:
            categories = await Category.find_all(include_inactive)
        
        return {"categories": [c.to_dict() for c in categories]}
    
    async def get_category(
        self,
        category_id: int,
        auth: dict = Depends(require_authenticated)
    ):
        """Get single category by ID"""
        category = await Category.find_by_id(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return category.to_dict()
    
    async def create_category(
        self,
        data: CategoryCreate,
        auth: dict = Depends(require_permission("config.manage"))
    ):
        """Create new category"""
        category = await Category.create(data.model_dump(exclude_none=True))
        return self.success_response(data=category.to_dict(), message="Category created")
    
    async def update_category(
        self,
        category_id: int,
        data: CategoryUpdate,
        auth: dict = Depends(require_permission("config.manage"))
    ):
        """Update existing category"""
        category = await Category.update(category_id, data.model_dump(exclude_none=True))
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return self.success_response(data=category.to_dict(), message="Category updated")
    
    async def delete_category(
        self,
        category_id: int,
        auth: dict = Depends(require_permission("config.manage"))
    ):
        """Delete category (soft delete)"""
        success = await Category.delete(category_id)
        if not success:
            raise HTTPException(status_code=404, detail="Category not found")
        return self.success_response(message="Category deleted")


# Create controller instance and export router
category_controller = CategoryController()
router = category_controller.router
