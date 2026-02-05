"""
Provisioning Service
Handles automatic organization and admin setup for new signups
"""

from typing import Dict, Any
from app.db import db
from app.models.organization import Organization
from app.models.role import Role
from app.models.employee import Employee
from app.models.permission import Permission
from app.services.base import BaseService


class ProvisioningService(BaseService):
    """
    Service for provisioning new organizations with admin access.
    Called after signup to create org + admin role + admin user.
    """

    async def provision_organization(
        self,
        org_name: str,
        admin_name: str,
        admin_phone: str,
        admin_email: str = None
    ) -> Dict[str, Any]:
        """
        Provision a new organization with full admin setup.
        
        Creates:
        1. Organization with auto-generated code
        2. Default unit for the organization
        3. Admin role with ALL permissions (scoped to org)
        4. Admin employee linked to the role
        
        Args:
            org_name: Name of the organization
            admin_name: Full name of the admin user
            admin_phone: Phone number for admin login
            admin_email: Optional email for admin
            
        Returns:
            Dict with organization and admin details
        """
        # Note: Using regular operations without explicit transaction
        # Each model method uses the global db connection pool
        
        # 1. Generate unique organization code
        org_code = await self._generate_org_code(org_name)
        # 2. Create Organization
        org = await Organization.create({
            'code': org_code,
            'name': org_name,
            'description': f'Organization for {org_name}',
            'is_active': True
        })
        
        print(f"✅ Created Organization: {org.name} (ID: {org.id})")
        
        # 3. Create Default Unit for the organization
        unit_result = await db.query("""
            INSERT INTO units (code, name, organization_id, is_active)
            VALUES ($1, $2, $3, TRUE)
            RETURNING id, code, name
        """, f"{org_code}-DEFAULT", "Default Unit", org.id)
        
        unit_id = unit_result[0]['id'] if unit_result else None
        print(f"✅ Created Default Unit: {unit_result[0]['name']} (ID: {unit_id})")
        
        # 4. Create Admin Role with ALL permissions (scoped to this org)
        admin_role = await Role.create({
            'code': 'admin',
            'name': 'Administrator',
            'description': f'Full access administrator for {org_name}',
            'organization_id': org.id,
            'is_system_role': False,
            'is_active': True
        })
        
        print(f"✅ Created Admin Role: {admin_role.name} (ID: {admin_role.id})")
        
        # 5. Assign ALL permissions to admin role (except orgs.manage)
        all_permissions = await Permission.find_all()
        permission_count = 0
        
        for perm in all_permissions:
            # Skip super-admin exclusive permissions
            if perm.code == 'orgs.manage':
                continue
                
            await db.execute("""
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
            """, admin_role.id, perm.id)
            permission_count += 1
        
        print(f"✅ Assigned {permission_count} permissions to Admin Role")
        
        # 6. Generate employee code
        emp_code_result = await db.query("""
            SELECT COALESCE(MAX(CAST(SUBSTRING(employee_code FROM 5) AS INTEGER)), 0) + 1 as next_num
            FROM employees WHERE employee_code LIKE 'EMP-%'
        """)
        next_num = emp_code_result[0]['next_num'] if emp_code_result else 1
        employee_code = f"EMP-{next_num:04d}"
        
        # 7. Create Admin Employee
        admin_result = await db.query("""
            INSERT INTO employees (
                employee_code, name, phone_number, email,
                organization_id, unit_id, role, role_id, is_admin, is_active
            )
            VALUES ($1, $2, $3, $4, $5, $6, 'admin', $7, TRUE, TRUE)
            RETURNING id, employee_code, name, phone_number, email
        """, employee_code, admin_name, admin_phone, admin_email, 
            org.id, unit_id, admin_role.id)
        
        admin_employee = admin_result[0] if admin_result else None
        print(f"✅ Created Admin Employee: {admin_employee['name']} (ID: {admin_employee['id']})")
        
        return {
            'success': True,
            'organization': {
                'id': org.id,
                'code': org.code,
                'name': org.name
            },
            'unit': {
                'id': unit_id,
                'name': 'Default Unit'
            },
            'admin_role': {
                'id': admin_role.id,
                'code': admin_role.code,
                'name': admin_role.name,
                'permissions_count': permission_count
            },
            'admin': {
                'id': admin_employee['id'],
                'employee_code': admin_employee['employee_code'],
                'name': admin_employee['name'],
                'phone_number': admin_employee['phone_number'],
                'email': admin_employee['email']
            }
        }
    
    async def _generate_org_code(self, org_name: str) -> str:
        """Generate unique organization code from name"""
        # Create base code from name (uppercase, no spaces)
        base_code = ''.join(c for c in org_name.upper() if c.isalnum())[:8]
        if not base_code:
            base_code = "ORG"
        
        # Check if code exists, add number if needed
        code = base_code
        counter = 1
        
        while True:
            existing = await db.query_one(
                "SELECT id FROM organizations WHERE code = $1", 
                code
            )
            if not existing:
                break
            code = f"{base_code}-{counter:03d}"
            counter += 1
        
        return code


# Module-level instance for easy import
provisioning_service = ProvisioningService()
