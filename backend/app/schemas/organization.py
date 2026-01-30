"""
Organization Schemas
Pydantic models for organization and unit endpoints
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class OrganizationBase(BaseModel):
    """Base organization fields"""
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool = True


class OrganizationCreate(OrganizationBase):
    """Request for creating organization"""
    pass


class OrganizationUpdate(BaseModel):
    """Request for updating organization"""
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    """Organization response"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class OrganizationListResponse(BaseModel):
    """Response for listing organizations"""
    organizations: List[OrganizationResponse]


# Unit Schemas

class UnitBase(BaseModel):
    """Base unit fields"""
    code: str
    name: str
    organization_id: Optional[int] = None
    is_active: bool = True


class UnitCreate(UnitBase):
    """Request for creating unit"""
    pass


class UnitUpdate(BaseModel):
    """Request for updating unit"""
    code: Optional[str] = None
    name: Optional[str] = None
    organization_id: Optional[int] = None
    is_active: Optional[bool] = None


class UnitResponse(UnitBase):
    """Unit response"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    organization_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class UnitListResponse(BaseModel):
    """Response for listing units"""
    units: List[UnitResponse]


# Enter/Exit Organization

class EnterOrganizationResponse(BaseModel):
    """Response after entering an organization"""
    access_token: str
    token_type: str = "bearer"
    organization: OrganizationResponse
    employee: dict


class ExitOrganizationResponse(BaseModel):
    """Response after exiting an organization"""
    access_token: str
    token_type: str = "bearer"
    employee: dict
