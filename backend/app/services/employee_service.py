"""
Employee Service
OOP class for employee business logic
"""

from typing import Optional, List, Dict, Any
from fastapi import Request
from app.db import db
from app.services.base import BaseService
from app.services.audit_service import AuditService
from app.models.employee import Employee


class EmployeeService(BaseService):
    """
    Service for employee business logic.
    Handles employee CRUD with audit logging.
    """
    
    def __init__(self, request: Optional[Request] = None, audit_service: AuditService = None):
        """Initialize with optional request and audit service"""
        super().__init__(request)
        self.audit_service = audit_service or AuditService(request)
    
    # ... (get methods remain same) ...
    async def get_employee(self, employee_id: int) -> Optional[Employee]:
        """Get employee by ID"""
        return await Employee.find_by_id(employee_id)
    
    async def get_employee_by_phone(self, phone: str) -> Optional[Employee]:
        """Find employee by phone number"""
        return await Employee.find_by_phone(phone)
    
    async def get_employee_by_chat_id(self, chat_id: str) -> Optional[Employee]:
        """Find employee by WhatsApp chat ID"""
        return await Employee.find_by_chat_id(chat_id)
    
    async def get_all_employees(
        self,
        role: str = None,
        location_id: int = None,
        organization_id: int = None,
        include_inactive: bool = False
    ) -> List[Employee]:
        """Get all employees with optional filters"""
        return await Employee.find_all_with_details(
            role=role,
            location_id=location_id,
            organization_id=organization_id,
            include_inactive=include_inactive
        )
    
    async def _resolve_role_id(self, role_code: str, organization_id: int) -> Optional[int]:
        """Helper to find role ID for a given code and organization"""
        if not role_code or not organization_id:
            return None
            
        # Try to find org-specific role first
        role_id = await db.fetchval("""
            SELECT id FROM roles 
            WHERE code = $1 AND organization_id = $2
        """, role_code, organization_id)
        
        # Fallback to system role if not found (though system roles shouldn't be used directly anymore)
        if not role_id:
            role_id = await db.fetchval("""
                SELECT id FROM roles 
                WHERE code = $1 AND organization_id IS NULL AND is_system_role = TRUE
            """, role_code)
            
        return role_id

    async def create_employee(
        self,
        data: Dict[str, Any],
        created_by: int,
        organization_id: int = None
    ) -> Employee:
        """Create new employee with audit logging"""
        
        # Auto-resolve role_id if missing but role string is present
        if 'role' in data and not data.get('role_id'):
            # Logic to find organization_id if not provided (e.g. from unit)
            # But here we rely on the controller/auth context usually
            org_id = organization_id
            if not org_id and 'unit_id' in data:
                 # Fetch unit to get org_id
                 unit = await db.query_one("SELECT organization_id FROM units WHERE id = $1", data['unit_id'])
                 if unit:
                     org_id = unit['organization_id']
            
            if org_id:
                data['role_id'] = await self._resolve_role_id(data['role'], org_id)

        employee = await Employee.create(data)
        
        await self.audit_service.log_employee_action(
            employee_id=employee.id,
            action='CREATE',
            new_values=data,
            performed_by=created_by,
            organization_id=organization_id
        )
        
        return employee
    
    async def update_employee(
        self,
        employee_id: int,
        data: Dict[str, Any],
        updated_by: int,
        organization_id: int = None
    ) -> Optional[Employee]:
        """Update employee with audit logging"""
        # Get current values for audit
        current = await Employee.find_by_id(employee_id)
        if not current:
            return None
            
        # Auto-resolve role_id if role is being updated but role_id is missing
        if 'role' in data and not data.get('role_id'):
            # Use employee's organization
            org_id = current.organization_id
            if org_id:
                data['role_id'] = await self._resolve_role_id(data['role'], org_id)
        
        old_values = current.to_dict()
        employee = await Employee.update(employee_id, data)
        
        if employee:
            await self.audit_service.log_employee_action(
                employee_id=employee_id,
                action='UPDATE',
                old_values=old_values,
                new_values=data,
                performed_by=updated_by,
                organization_id=organization_id
            )
        
        return employee
    
    async def deactivate_employee(
        self,
        employee_id: int,
        deactivated_by: int,
        organization_id: int = None
    ) -> bool:
        """Soft delete (deactivate) employee with audit logging"""
        current = await Employee.find_by_id(employee_id)
        if not current:
            return False
        
        success = await Employee.delete(employee_id, soft=True)
        
        if success:
            await self.audit_service.log_employee_action(
                employee_id=employee_id,
                action='DEACTIVATE',
                old_values={'is_active': True},
                new_values={'is_active': False},
                performed_by=deactivated_by,
                organization_id=organization_id
            )
        
        return success
    
    async def activate_employee(
        self,
        employee_id: int,
        activated_by: int,
        organization_id: int = None
    ) -> Optional[Employee]:
        """Reactivate an employee with audit logging"""
        employee = await Employee.update(employee_id, {'is_active': True})
        
        if employee:
            await self.audit_service.log_employee_action(
                employee_id=employee_id,
                action='ACTIVATE',
                old_values={'is_active': False},
                new_values={'is_active': True},
                performed_by=activated_by,
                organization_id=organization_id
            )
        
        return employee
    
    async def link_chat_id(self, employee_id: int, chat_id: str) -> Optional[Employee]:
        """Link WhatsApp chat ID to employee"""
        return await Employee.link_chat_id(employee_id, chat_id)
    
    async def change_role(
        self,
        employee_id: int,
        new_role: str,
        is_admin: bool = None,
        is_manager: bool = None,
        changed_by: int = None,
        organization_id: int = None
    ) -> Optional[Employee]:
        """Change employee role with audit logging"""
        current = await Employee.find_by_id(employee_id)
        if not current:
            return None
        
        old_values = {
            'role': current.role,
            'is_admin': current.is_admin,
            'is_manager': current.is_manager
        }
        
        update_data = {'role': new_role}
        
        # Resolve role_id
        org_id = current.organization_id
        if org_id:
            role_id = await self._resolve_role_id(new_role, org_id)
            if role_id:
                update_data['role_id'] = role_id
                
        if is_admin is not None:
            update_data['is_admin'] = is_admin
        if is_manager is not None:
            update_data['is_manager'] = is_manager
        
        employee = await Employee.update(employee_id, update_data)
        
        if employee:
            await self.audit_service.log_employee_action(
                employee_id=employee_id,
                action='ROLE_CHANGE',
                old_values=old_values,
                new_values=update_data,
                performed_by=changed_by,
                organization_id=organization_id
            )
        
        return employee
