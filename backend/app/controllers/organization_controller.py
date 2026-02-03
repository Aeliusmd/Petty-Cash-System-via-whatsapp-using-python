"""
Organization Controller
API routes for organization management
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from app.controllers.base import BaseController
from app.models.organization import Organization
from app.models.unit import Unit
from app.services.auth_service import AuthService
from app.schemas.organization import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    UnitCreate, UnitUpdate, EnterOrganizationResponse
)
from app.utils.auth import require_permission, require_authenticated


class OrganizationController(BaseController):
    """Controller for organization management endpoints"""
    
    prefix = "/api/organizations"
    tags = ["Organizations"]
    
    def __init__(self):
        super().__init__()
    
    def _register_routes(self):
        """Register organization routes"""
        self.router.get("")(self.get_organizations)
        self.router.get("/{org_id}")(self.get_organization)
        self.router.get("/{org_id}/units")(self.get_organization_units)
        self.router.post("")(self.create_organization)
        self.router.put("/{org_id}")(self.update_organization)
        self.router.delete("/{org_id}")(self.delete_organization)
        self.router.post("/{org_id}/enter")(self.enter_organization)
        self.router.post("/exit")(self.exit_organization)
    
    async def get_organizations(
        self,
        include_inactive: bool = False,
        auth: dict = Depends(require_permission("orgs.manage"))
    ):
        """Get all organizations (super admin only)"""
        print(f"🏢 Accessing get_organizations (inactive={include_inactive})")
        organizations = await Organization.find_all(include_inactive)
        print(f"✅ Found {len(organizations)} organizations")
        return {"organizations": [o.to_dict() for o in organizations]}
    
    async def get_organization(
        self,
        org_id: int,
        auth: dict = Depends(require_permission("orgs.manage"))
    ):
        """Get single organization by ID"""
        org = await Organization.find_by_id(org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        return org.to_dict()
    
    async def get_organization_units(
        self,
        org_id: int,
        auth: dict = Depends(require_permission("orgs.manage"))
    ):
        """Get units for an organization"""
        units = await Organization.get_units(org_id)
        return {"units": units}
    
    async def create_organization(
        self,
        data: OrganizationCreate,
        auth: dict = Depends(require_permission("orgs.manage"))
    ):
        """Create new organization"""
        try:
            org = await Organization.create(data.model_dump(exclude_none=True))
            return self.success_response(data=org.to_dict(), message="Organization created")
        except Exception as e:
            if "duplicate key" in str(e).lower():
                raise HTTPException(status_code=400, detail="Organization code already exists")
            raise e
    
    async def update_organization(
        self,
        org_id: int,
        data: OrganizationUpdate,
        auth: dict = Depends(require_permission("orgs.manage"))
    ):
        """Update existing organization"""
        org = await Organization.update(org_id, data.model_dump(exclude_none=True))
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        return self.success_response(data=org.to_dict(), message="Organization updated")
    
    async def delete_organization(
        self,
        org_id: int,
        auth: dict = Depends(require_permission("orgs.manage"))
    ):
        """Delete organization (soft delete)"""
        success = await Organization.delete(org_id)
        if not success:
            raise HTTPException(status_code=404, detail="Organization not found")
        return self.success_response(message="Organization deleted")
    
    async def enter_organization(
        self,
        org_id: int,
        request: Request,
        auth: dict = Depends(require_permission("orgs.manage"))
    ):
        """Enter organization context"""
        print(f"🏢 Entering organization request: org_id={org_id}, employee_id={auth.get('employee_id')}")
        
        try:
            org = await Organization.find_by_id(org_id)
            if not org:
                raise HTTPException(status_code=404, detail="Organization not found")
            
            auth_service = AuthService(request)
            tokens = await auth_service.enter_organization(
                employee_id=auth['employee_id'],
                organization_id=org.id,
                organization_name=org.name
            )
            
            if not tokens:
                print("❌ Failed to generate token for organization entry")
                raise HTTPException(status_code=500, detail="Failed to generate authentication token")
            
            from app.models.employee import Employee
            employee = await Employee.find_by_id(auth['employee_id'])
            
            # Populate permissions before conversion
            if employee:
                employee.permissions = await employee.get_permissions()
            
            # Inject organization context into employee object for frontend
            employee_dict = employee.to_dict() if employee else {}
            employee_dict['organization_id'] = org.id
            employee_dict['organization_name'] = org.name
            
            print(f"✅ Successfully entered organization: {org.name}")
            return {
                "access_token": tokens['access_token'],
                "refresh_token": tokens['refresh_token'],
                "token_type": "bearer",
                "organization": org.to_dict(),
                "employee": employee_dict
            }
        except Exception as e:
            print(f"❌ Error entering organization: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
    
    async def exit_organization(
        self,
        request: Request,
        auth: dict = Depends(require_authenticated)
    ):
        """Exit organization context"""
        if not auth.get('organization_id'):
            raise HTTPException(status_code=400, detail="Not in an organization context")
        
        auth_service = AuthService(request)
        tokens = await auth_service.exit_organization(
            employee_id=auth['employee_id'],
            organization_id=auth['organization_id']
        )
        
        from app.models.employee import Employee
        employee = await Employee.find_by_id(auth['employee_id'])
        
        # Populate permissions
        if employee:
            employee.permissions = await employee.get_permissions()
        
        return {
            "access_token": tokens['access_token'],
            "refresh_token": tokens['refresh_token'],
            "token_type": "bearer",
            "employee": employee.to_dict() if employee else {}
        }


# Create controller instance and export router
organization_controller = OrganizationController()
router = organization_controller.router
