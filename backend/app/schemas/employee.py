"""
Employee Schemas
Pydantic models for employee-related endpoints
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class EmployeeBase(BaseModel):
    """Base employee fields"""
    name: str
    phone_number: str
    email: Optional[str] = None
    grade_id: Optional[int] = None
    unit_id: Optional[int] = None
    location_id: Optional[int] = None
    manager_id: Optional[int] = None
    role: str = "staff"
    is_admin: bool = False
    is_manager: bool = False


class EmployeeCreate(EmployeeBase):
    """Request for creating employee"""
    employee_code: Optional[str] = None


class EmployeeUpdate(BaseModel):
    """Request for updating employee - all fields optional"""
    employee_code: Optional[str] = None
    name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    grade_id: Optional[int] = None
    unit_id: Optional[int] = None
    location_id: Optional[int] = None
    manager_id: Optional[int] = None
    role: Optional[str] = None
    role_id: Optional[int] = None  # RBAC role ID
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_manager: Optional[bool] = None


class EmployeeResponse(BaseModel):
    """Employee response with all details"""
    id: int
    employee_code: str
    name: str
    phone_number: str
    email: Optional[str] = None
    role: str
    is_active: bool
    is_admin: bool
    is_manager: bool
    whatsapp_chat_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Joined fields
    grade_id: Optional[int] = None
    grade_code: Optional[str] = None
    grade_name: Optional[str] = None
    unit_id: Optional[int] = None
    unit_code: Optional[str] = None
    unit_name: Optional[str] = None
    location_id: Optional[int] = None
    location_code: Optional[str] = None
    location_name: Optional[str] = None
    manager_id: Optional[int] = None
    manager_name: Optional[str] = None
    manager_phone: Optional[str] = None
    
    class Config:
        from_attributes = True


class EmployeeListResponse(BaseModel):
    """Response for listing employees"""
    employees: List[EmployeeResponse]
    total: Optional[int] = None
