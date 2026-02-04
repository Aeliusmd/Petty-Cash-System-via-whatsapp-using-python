"""
JWT Utilities
Handles JWT token generation and verification for authentication
"""

import jwt
import os
from datetime import datetime, timedelta
from typing import Optional, Dict

from app.config import config

# Get JWT secret from config
JWT_SECRET = config.JWT_SECRET
JWT_ALGORITHM = config.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = config.ACCESS_TOKEN_EXPIRE_MINUTES


def create_access_token(
    employee_id: int, 
    name: str, 
    is_admin: bool = False, 
    is_manager: bool = False, 
    role: str = None,
    organization_id: int = None,
    organization_name: str = None
) -> str:
    """
    Create a JWT access token for an employee
    
    Args:
        employee_id: The employee's ID
        name: The employee's name
        is_admin: Whether the employee is an admin
        is_manager: Whether the employee is a manager
        role: Explicit role (super_admin, admin, manager, employee) - takes priority
        organization_id: Current organization context (for super admin entering an org)
        organization_name: Name of current organization
        
    Returns:
        JWT token string
    """
    # Use explicit role if provided, otherwise derive from flags
    if role and role in ('super_admin', 'admin', 'manager', 'employee'):
        final_role = role
    elif is_admin:
        final_role = 'admin'
    elif is_manager:
        final_role = 'manager'
    else:
        final_role = 'employee'
    
    payload = {
        'employee_id': employee_id,
        'name': name,
        'role': final_role,
        'is_admin': is_admin or final_role in ('admin', 'super_admin'),
        'is_manager': is_manager or final_role in ('manager', 'admin', 'super_admin'),
        'organization_id': organization_id,
        'organization_name': organization_name,
        'exp': datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_access_token(token: str) -> Optional[Dict]:
    """
    Verify and decode a JWT access token
    
    Args:
        token: The JWT token string
        
    Returns:
        Decoded payload if valid, None if invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
