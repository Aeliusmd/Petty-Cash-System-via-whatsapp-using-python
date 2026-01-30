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
