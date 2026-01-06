"""
JWT Utilities
Handles JWT token generation and verification for authentication
"""

import jwt
import os
from datetime import datetime, timedelta
from typing import Optional, Dict

# Get JWT secret from environment or use default (change in production!)
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-this-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DAYS = 7


def create_access_token(employee_id: int, name: str, is_admin: bool = False, is_manager: bool = False) -> str:
    """
    Create a JWT access token for an employee
    
    Args:
        employee_id: The employee's ID
        name: The employee's name
        is_admin: Whether the employee is an admin
        is_manager: Whether the employee is a manager
        
    Returns:
        JWT token string
    """
    # Determine role: admin > manager > employee
    if is_admin:
        role = 'admin'
    elif is_manager:
        role = 'manager'
    else:
        role = 'employee'
    
    payload = {
        'employee_id': employee_id,
        'name': name,
        'role': role,
        'is_admin': is_admin,
        'is_manager': is_manager,
        'exp': datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS),
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
