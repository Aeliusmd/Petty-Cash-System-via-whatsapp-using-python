"""
Employee Service
OOP class for employee business logic
"""

from typing import Optional, List, Dict, Any
from fastapi import Request
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
    
    async def create_employee(
        self,
        data: Dict[str, Any],
        created_by: int,
        organization_id: int = None
    ) -> Employee:
        """Create new employee with audit logging"""
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
