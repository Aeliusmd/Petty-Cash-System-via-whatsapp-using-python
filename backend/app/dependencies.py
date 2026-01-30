"""
Dependency injection for FastAPI
Provides reusable dependencies for controllers
"""

from typing import Optional
from fastapi import Request, Depends, HTTPException
from app.utils.auth import require_authenticated, require_admin, require_super_admin


class Dependencies:
    """Container for dependency injection functions"""
    
    @staticmethod
    async def get_current_user(auth: dict = Depends(require_authenticated)) -> dict:
        """Get current authenticated user"""
        return auth
    
    @staticmethod
    async def get_admin_user(auth: dict = Depends(require_admin)) -> dict:
        """Get current admin user"""
        return auth
    
    @staticmethod
    async def get_super_admin_user(auth: dict = Depends(require_super_admin)) -> dict:
        """Get current super admin user"""
        return auth
    
    @staticmethod
    def get_organization_id(auth: dict) -> Optional[int]:
        """Extract organization ID from auth context"""
        return auth.get('organization_id')
    
    @staticmethod
    def get_employee_id(auth: dict) -> int:
        """Extract employee ID from auth context"""
        return auth.get('employee_id')


# Export commonly used dependencies
get_current_user = Dependencies.get_current_user
get_admin_user = Dependencies.get_admin_user
get_super_admin_user = Dependencies.get_super_admin_user
