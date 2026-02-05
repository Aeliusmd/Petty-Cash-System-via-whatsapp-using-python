"""
Provisioning Controller
API endpoints for organization signup and provisioning
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.services.provisioning_service import provisioning_service
from app.models.employee import Employee

router = APIRouter()


class SignupRequest(BaseModel):
    """Request body for organization signup"""
    org_name: str = Field(..., min_length=2, max_length=100, description="Organization name")
    admin_name: str = Field(..., min_length=2, max_length=100, description="Admin full name")
    admin_phone: str = Field(..., min_length=9, max_length=20, description="Admin phone number")
    admin_email: Optional[str] = Field(None, max_length=100, description="Admin email (optional)")


class SignupResponse(BaseModel):
    """Response for successful signup"""
    success: bool
    message: str
    organization: dict
    admin: dict


@router.post("/signup", response_model=SignupResponse)
async def signup(request: SignupRequest):
    """
    Public endpoint for organization self-registration.
    
    Creates:
    - New organization
    - Default unit
    - Admin role with full permissions
    - Admin employee
    
    The admin can then login with their phone number.
    """
    try:
        # Check if phone number already exists
        normalized_phone = Employee.normalize_phone(request.admin_phone)
        existing = await Employee.find_by_phone(request.admin_phone)
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Phone number {request.admin_phone} is already registered"
            )
        
        # Provision the organization
        result = await provisioning_service.provision_organization(
            org_name=request.org_name,
            admin_name=request.admin_name,
            admin_phone=request.admin_phone,
            admin_email=request.admin_email
        )
        
        return SignupResponse(
            success=True,
            message=f"Organization '{request.org_name}' created successfully! You can now login with your phone number.",
            organization=result['organization'],
            admin=result['admin']
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Signup error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create organization. Please try again."
        )
