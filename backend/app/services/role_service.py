from typing import List, Optional, Dict, Any
from app.db import db
from app.services.base import BaseService
from app.models.role import Role
from app.models.permission import Permission
from app.models.employee import Employee

class RoleService(BaseService):
    """
    Service for Role Management
    Handles creating roles, assigning permissions, and queries.
    """
    
    async def get_all_roles(self, organization_id: Optional[int] = None, include_system: bool = True) -> List[Dict]:
        """
        Get all roles visible to the organization.
        Returns roles with permission codes.
        """
        roles = await Role.find_all(organization_id=organization_id, include_system=include_system)
        
        result = []
        for role in roles:
            # Filter out super_admin role from list
            if role.code == 'super_admin':
                 continue
                 
            r_dict = dict(role)
            # Fetch assigned permissions (direct only? or inherited? UI usually edits direct permissions)
            # For editing, we usually want DIRECT permissions.
            # But the Role.get_permissions() returns ALL (inherited).
            # I should add get_direct_permissions to Role model or query here.
            # Querying direct permissions for UI checkbox state:
            perms = await self.get_role_direct_permissions(role.id)
            r_dict['permissions'] = perms
            result.append(r_dict)
            
        return result

    async def get_role_direct_permissions(self, role_id: int) -> List[Dict]:
        """Get explicitly assigned permissions for a role (ignoring inheritance)"""
        query = """
            SELECT p.id, p.code, p.name, p.description, p.category
            FROM role_permissions rp
            JOIN permissions p ON rp.permission_id = p.id
            WHERE rp.role_id = $1
        """
        rows = await db.query(query, role_id)
        return rows

    async def create_role(self, data: Dict[str, Any], permission_codes: List[str], created_by: int) -> Role:
        """Create a new role and assign permissions"""
        async with db.transaction():
            # 1. Check for duplicates WITHIN THE SAME ORGANIZATION SCOPE
            # System roles (org_id = NULL) and Org roles (org_id = X) should be separate
            org_id = data.get('organization_id')
            
            if org_id:
                # For org-specific roles, only check within this org
                existing = await db.query_one("""
                    SELECT id FROM roles 
                    WHERE code = $1 AND organization_id = $2
                """, data['code'], org_id)
            else:
                # For system roles, only check system scope
                existing = await db.query_one("""
                    SELECT id FROM roles 
                    WHERE code = $1 AND organization_id IS NULL
                """, data['code'])
                
            if existing:
                raise ValueError(f"Role with code '{data['code']}' already exists in this scope")
                
            role = await Role.create(data)
            
            # 2. Assign Permissions
            if permission_codes:
                await self.assign_permissions(role.id, permission_codes)
                
            return role

    async def update_role(self, role_id: int, data: Dict[str, Any], permission_codes: Optional[List[str]]) -> Optional[Role]:
        """Update role details and permissions"""
        role = await Role.find_by_id(role_id)
        if not role:
            return None
            
        async with db.transaction():
            # 1. Update Role fields
            if data:
                role = await Role.update(role_id, data)
            
            # 2. Update Permissions if provided
            if permission_codes is not None:
                # Clear existing (direct)
                await db.execute("DELETE FROM role_permissions WHERE role_id = $1", role_id)
                # Assign new
                await self.assign_permissions(role_id, permission_codes)
                
        return role

    async def assign_permissions(self, role_id: int, permission_codes: List[str]):
        """Assign permissions to role"""
        # Resolve codes to IDs
        if not permission_codes:
            return
            
        # Get permission map
        perms = await Permission.find_all()
        perm_map = {p.code: p.id for p in perms}
        
        for code in permission_codes:
            if code in perm_map:
                perm_id = perm_map[code]
                await db.execute(
                    "INSERT INTO role_permissions (role_id, permission_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    role_id, perm_id
                )

    async def delete_role(self, role_id: int) -> bool:
        """Soft delete role - only super_admin is protected"""
        role = await Role.find_by_id(role_id)
        if not role:
            return False
        
        # Only protect super_admin
        if role.code == 'super_admin':
            raise ValueError("Cannot delete super_admin role")
             
        await Role.delete(role_id)
        return True

    async def get_all_permissions(self) -> List[Dict]:
        """Get all available permissions grouped by category"""
        perms = await Permission.find_all()
        # Filter out super-admin exclusive permissions
        return [dict(p) for p in perms if p.code != 'orgs.manage']
