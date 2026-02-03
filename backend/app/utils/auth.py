"""
Authentication Utilities
Role-based access control middleware for FastAPI
"""

from fastapi import HTTPException, Header, Depends
from typing import Optional
from app.utils import jwt_utils


async def get_current_user(authorization: str = Header(None)) -> dict:
    """
    Extract and validate the current user from JWT token
    Returns the decoded token payload
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Extract token from "Bearer <token>" format
    token = authorization.replace("Bearer ", "")
    payload = jwt_utils.verify_access_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return payload


async def require_super_admin(authorization: str = Header(None)) -> dict:
    """
    Middleware to require super admin role
    Use this to protect organization management endpoints
    """
    payload = await get_current_user(authorization)
    
    role = payload.get("role", "employee")
    if role != "super_admin":
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Super admin privileges required"
        )
    
    return payload


async def require_manager(authorization: str = Header(None)) -> dict:
    """
    Middleware to require manager, admin or super admin role
    """
    payload = await get_current_user(authorization)
    
    role = payload.get("role", "employee")
    if role not in ["manager", "admin", "super_admin"]:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Manager privileges required"
        )
    
    return payload


async def require_admin(authorization: str = Header(None)) -> dict:
    """
    Middleware to require admin or super admin role
    Use this to protect admin-level endpoints
    """
    payload = await get_current_user(authorization)
    
    role = payload.get("role", "employee")
    if role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Admin privileges required"
        )
    
    return payload


async def require_authenticated(authorization: str = Header(None)) -> dict:
    """
    Middleware to require any authenticated user
    Use this to protect general endpoints
    """
    return await get_current_user(authorization)


def check_role(user: dict, required_role: str) -> bool:
    """
    Check if user has the required role or higher
    Role hierarchy: super_admin > admin > employee
    """
    role_hierarchy = {
        "employee": 0,
        "admin": 1,
        "super_admin": 2
    }
    
    user_role = user.get("role", "employee")
    user_level = role_hierarchy.get(user_role, 0)
    required_level = role_hierarchy.get(required_role, 0)
    
    return user_level >= required_level


def require_permission(required_perm: str):
    """
    Dependency factory to check for specific permission.
    
    IMPORTANT: Loads permissions fresh from database on each request
    to ensure permission changes take effect immediately without re-login.
    
    Usage: user = Depends(require_permission("claims.create"))
    """
    async def _check_permission(authorization: str = Header(None)) -> dict:
        payload = await get_current_user(authorization)
        
        # Super admin bypass - always has all permissions
        if payload.get("role") == "super_admin":
            return payload
        
        # Load permissions FRESH from database (not from cached JWT)
        from app.models.employee import Employee
        
        employee_id = payload.get("employee_id")
        if not employee_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing employee_id")
        
        employee = await Employee.find_by_id(employee_id)
        if not employee:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Get current permissions from database (reflects latest role changes)
        permissions = await employee.get_permissions()
        
        if required_perm not in permissions:
            raise HTTPException(
                status_code=403, 
                detail=f"Access denied: Missing permission '{required_perm}'"
            )
        
        # Add fresh permissions to payload for downstream use
        payload['permissions'] = permissions
        
        # Update payload with fresh data from DB to ensure controllers have latest context
        if hasattr(employee, 'organization_id'):
            payload['organization_id'] = employee.organization_id
        if hasattr(employee, 'role'):
            payload['role'] = employee.role
            
        return payload
    
    return _check_permission

