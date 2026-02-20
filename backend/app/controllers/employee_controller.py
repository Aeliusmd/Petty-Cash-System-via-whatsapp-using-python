"""
Employee Controller
API routes for employee management
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from app.controllers.base import BaseController
from app.services.employee_service import EmployeeService
from app.schemas.employee import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeListResponse
)
from app.utils.auth import require_permission, require_authenticated
from app.services.event_service import event_service

class EmployeeController(BaseController):
    """Controller for employee management endpoints"""
    
    prefix = "/api/employees"
    tags = ["Employees"]
    
    def __init__(self):
        super().__init__()
    
    def _register_routes(self):
        """Register employee routes"""
        # List all: requires employees.read.all
        self.router.get("/")(self.get_employees)
        # Get one: requires authenticated (checked inside)
        self.router.get("/{employee_id}")(self.get_employee)
        # Create: requires employees.create
        self.router.post("/")(self.create_employee)
        # Update: requires employees.update.all (for now, assuming admin update)
        self.router.put("/{employee_id}")(self.update_employee)
        # Delete: requires employees.delete
        self.router.delete("/{employee_id}")(self.delete_employee)
        # Activate: requires employees.activate
        self.router.post("/{employee_id}/activate")(self.activate_employee)
    
    async def get_employees(
        self,
        request: Request,
        role: Optional[str] = None,
        location_id: Optional[int] = None,
        unit_id: Optional[int] = None,
        include_inactive: bool = False,
        auth: dict = Depends(require_permission("employees.read.all"))
    ):
        """Get all employees with optional filters"""
        service = EmployeeService(request)
        
        employees = await service.get_all_employees(
            role=role,
            location_id=location_id,
            unit_id=unit_id,
            organization_id=auth.get('organization_id'),
            include_inactive=include_inactive
        )
        
        return {"employees": [e.to_dict() for e in employees]}
    
    async def get_employee(
        self,
        employee_id: int,
        request: Request,
        auth: dict = Depends(require_authenticated)
    ):
        """Get single employee by ID"""
        service = EmployeeService(request)
        
        permissions = auth.get('permissions', [])
        is_self = auth['employee_id'] == employee_id
        
        # Check permissions
        if is_self:
            if 'employees.read.own' not in permissions and 'employees.read.all' not in permissions:
                raise HTTPException(status_code=403, detail="Access denied")
        else:
             if 'employees.read.all' not in permissions:
                 raise HTTPException(status_code=403, detail="Access denied")
        
        employee = await service.get_employee(employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        return employee.to_dict()
    
    async def create_employee(
        self,
        data: EmployeeCreate,
        request: Request,
        auth: dict = Depends(require_permission("employees.create"))
    ):
        """Create new employee"""
        service = EmployeeService(request)
        
        employee = await service.create_employee(
            data=data.model_dump(exclude_none=True),
            created_by=auth['employee_id'],
            organization_id=auth.get('organization_id')
        )
        
        return self.success_response(data=employee.to_dict(), message="Employee created successfully")
    
    async def update_employee(
        self,
        employee_id: int,
        data: EmployeeUpdate,
        request: Request,
        auth: dict = Depends(require_permission("employees.update.all"))
    ):
        """Update existing employee"""
        service = EmployeeService(request)
        
        employee = await service.update_employee(
            employee_id=employee_id,
            data=data.model_dump(exclude_none=True),
            updated_by=auth['employee_id'],
            organization_id=auth.get('organization_id')
        )
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
            
        # Notify the specific employee's active browsers to refresh permissions instantly
        await event_service.notify_employee(employee_id, "PERMISSIONS_UPDATED")
        
        return self.success_response(data=employee.to_dict(), message="Employee updated successfully")
    
    async def delete_employee(
        self,
        employee_id: int,
        request: Request,
        auth: dict = Depends(require_permission("employees.delete"))
    ):
        """Deactivate employee (soft delete)"""
        service = EmployeeService(request)
        
        success = await service.deactivate_employee(
            employee_id=employee_id,
            deactivated_by=auth['employee_id'],
            organization_id=auth.get('organization_id')
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        return self.success_response(message="Employee deactivated successfully")
    
    async def activate_employee(
        self,
        employee_id: int,
        request: Request,
        auth: dict = Depends(require_permission("employees.activate"))
    ):
        """Reactivate a deactivated employee"""
        service = EmployeeService(request)
        
        employee = await service.activate_employee(
            employee_id=employee_id,
            activated_by=auth['employee_id'],
            organization_id=auth.get('organization_id')
        )
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        return self.success_response(data=employee.to_dict(), message="Employee activated successfully")


# Create controller instance and export router
employee_controller = EmployeeController()
router = employee_controller.router
