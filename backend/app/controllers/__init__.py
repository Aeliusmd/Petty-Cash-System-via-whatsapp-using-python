"""
Controllers Package
OOP controller classes for API routes
"""

from app.controllers.base import BaseController
from app.controllers.auth_controller import AuthController, router as auth_router
from app.controllers.employee_controller import EmployeeController, router as employee_router
from app.controllers.claim_controller import ClaimController, router as claim_router
from app.controllers.category_controller import CategoryController, router as category_router
from app.controllers.organization_controller import OrganizationController, router as organization_router
from app.controllers.audit_controller import AuditController, router as audit_router

__all__ = [
    'BaseController',
    'AuthController',
    'EmployeeController', 
    'ClaimController',
    'CategoryController',
    'OrganizationController',
    'AuditController',
    'auth_router',
    'employee_router',
    'claim_router',
    'category_router',
    'organization_router',
    'audit_router'
]
