from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

# Permission Schemas
class PermissionBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None

class PermissionResponse(PermissionBase):
    id: int
    resource: str
    action: str
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Simplified permission info for role responses
class RolePermissionInfo(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    
    class Config:
        from_attributes = True

# Role Schemas
class RoleBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    parent_role_id: Optional[int] = None
    
class RoleCreate(RoleBase):
    permission_codes: List[str] = [] # List of permission codes to assign

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_role_id: Optional[int] = None
    permission_codes: Optional[List[str]] = None
    is_active: Optional[bool] = None

class RoleResponse(RoleBase):
    id: int
    organization_id: Optional[int] = None
    is_system_role: bool
    is_active: bool
    permissions: List[RolePermissionInfo] = []  # List of permission objects
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

