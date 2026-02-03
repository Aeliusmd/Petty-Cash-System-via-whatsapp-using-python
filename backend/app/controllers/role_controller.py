from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from app.controllers.base import BaseController
from app.services.role_service import RoleService
from app.schemas.role import RoleResponse, RoleCreate, RoleUpdate, PermissionResponse
from app.utils.auth import require_permission, get_current_user

class RoleController(BaseController):
    """Controller for Role Management"""
    
    prefix = "/api/roles"
    tags = ["Roles"]
    
    def __init__(self):
        super().__init__()
        self.role_service = RoleService()
    
    def _register_routes(self):
        """Register API routes"""
        self.router.get("", response_model=List[RoleResponse])(self.get_roles)
        self.router.post("", response_model=RoleResponse)(self.create_role)
        self.router.get("/permissions", response_model=List[PermissionResponse])(self.get_permissions)
        self.router.get("/{role_id}", response_model=RoleResponse)(self.get_role)
        self.router.put("/{role_id}", response_model=RoleResponse)(self.update_role)
        self.router.delete("/{role_id}")(self.delete_role)
        
    async def get_roles(self, request: Request, 
                        user: dict = Depends(require_permission("roles.read"))):
        """List all roles for the current organization"""
        # Determine organization context
        # Use org_id from user context to ensure we filter by the current organization
        org_id = user.get('organization_id')
        
        # Return org-specific roles and system roles
        return await self.role_service.get_all_roles(organization_id=org_id, include_system=True)

    async def get_permissions(self, request: Request,
                              user: dict = Depends(require_permission("roles.read"))):
        """List all available permissions"""
        return await self.role_service.get_all_permissions()

    async def get_role(self, role_id: int, 
                       user: dict = Depends(require_permission("roles.read"))):
        """Get role by ID"""
        # Logic to check org access should be here or in service
        roles = await self.role_service.get_all_roles() # Inefficient but reuses logic with permissions
        # Better: Add get_role_details in service
        filtered = [r for r in roles if r['id'] == role_id]
        if not filtered:
             raise HTTPException(status_code=404, detail="Role not found")
        return filtered[0]

    async def create_role(self, data: RoleCreate, request: Request,
                          user: dict = Depends(require_permission("roles.create"))):
        """Create new custom role"""
        role_data = data.model_dump(exclude={'permission_codes'})
        
        # Enforce organization scope for non-super-admins
        if user.get('role') != 'super_admin':
            org_id = user.get('organization_id')
            if not org_id:
                # Should not happen if auth middleware is working, but safety check
                raise HTTPException(status_code=400, detail="Cannot create role: Organization context missing")
                
            role_data['organization_id'] = org_id
            role_data['is_system_role'] = False
        else:
            # Super admin: use their current organization context if they've entered one
            org_id = user.get('organization_id')
            if org_id:
                # Super admin is working within an organization context
                role_data['organization_id'] = org_id
                role_data['is_system_role'] = False
            # else: Creating a global system role (org_id stays None)
            
        role_data['created_by'] = user.get('employee_id')
        
        try:
            role = await self.role_service.create_role(
                role_data, 
                data.permission_codes, 
                user.get('employee_id')
            )
            
            # Fetch back with permissions to match response model
            perms = await self.role_service.get_role_direct_permissions(role.id)
            role_dict = dict(role)
            role_dict['permissions'] = perms
            return role_dict
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def update_role(self, role_id: int, data: RoleUpdate, request: Request,
                          user: dict = Depends(require_permission("roles.update"))):
        """Update existing role"""
        role_data = data.model_dump(exclude={'permission_codes'}, exclude_unset=True)
        
        try:
            role = await self.role_service.update_role(
                role_id, 
                role_data, 
                data.permission_codes
            )
            
            if not role:
                 raise HTTPException(status_code=404, detail="Role not found")
                 
            # Fetch permissions
            perms = await self.role_service.get_role_direct_permissions(role.id)
            role_dict = dict(role)
            role_dict['permissions'] = perms
            return role_dict
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def delete_role(self, role_id: int, 
                          user: dict = Depends(require_permission("roles.delete"))):
        """Delete a role"""
        try:
            success = await self.role_service.delete_role(role_id)
            if not success:
                raise HTTPException(status_code=404, detail="Role not found")
            return self.success_response(message="Role deleted successfully")
        except ValueError as e:
             raise HTTPException(status_code=400, detail=str(e))

# Create controller instance and export router
role_controller = RoleController()
router = role_controller.router
