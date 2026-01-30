"""
Auth Service
OOP class for authentication business logic
"""

import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import Request
import jwt
from app.services.base import BaseService
from app.services.audit_service import AuditService
from app.models.employee import Employee
from app.models.otp import OTP
from app.config import config


class AuthService(BaseService):
    """
    Service for authentication business logic.
    Handles OTP, JWT tokens, and login/logout.
    """
    
    def __init__(self, request: Optional[Request] = None, audit_service: AuditService = None):
        """Initialize with optional request and audit service"""
        super().__init__(request)
        self.audit_service = audit_service or AuditService(request)
    
    async def request_otp(self, phone_number: str) -> Optional[str]:
        """
        Generate and return OTP for phone number.
        Returns None if rate limited.
        """
        # Check rate limit
        if await OTP.check_rate_limit(phone_number):
            await self.audit_service.log_auth_action(
                action='OTP_RATE_LIMITED',
                metadata={'phone_number': phone_number}
            )
            return None
        
        otp = await OTP.generate(phone_number)
        
        await self.audit_service.log_auth_action(
            action='OTP_REQUEST',
            metadata={'phone_number': phone_number}
        )
        
        return otp.code
    
    async def verify_otp(self, phone_number: str, otp_code: str) -> Optional[Dict[str, Any]]:
        """
        Verify OTP and return login result with JWT token.
        Returns None if verification fails.
        """
        if not await OTP.verify(phone_number, otp_code):
            await self.audit_service.log_auth_action(
                action='OTP_FAILED',
                metadata={'phone_number': phone_number}
            )
            return None
        
        # Find employee by phone
        employee = await Employee.find_by_phone(phone_number)
        if not employee:
            await self.audit_service.log_auth_action(
                action='LOGIN_FAILED',
                metadata={'phone_number': phone_number, 'reason': 'Employee not found'}
            )
            return None
        
        # Generate JWT token
        token = self.create_token(employee)
        
        await self.audit_service.log_auth_action(
            action='LOGIN',
            employee_id=employee.id
        )
        
        return {
            'access_token': token,
            'token_type': 'bearer',
            'employee': employee.to_dict()
        }
    
    def create_token(self, employee: Employee, organization_id: int = None, organization_name: str = None) -> str:
        """Create JWT token for employee"""
        payload = {
            'employee_id': employee.id,
            'name': employee.name,
            'role': employee.role,
            'is_admin': employee.is_admin,
            'is_manager': employee.is_manager,
            'exp': datetime.utcnow() + timedelta(hours=config.JWT_EXPIRY_HOURS)
        }
        
        if organization_id:
            payload['organization_id'] = organization_id
        elif getattr(employee, 'organization_id', None):
            payload['organization_id'] = getattr(employee, 'organization_id')
            
        if organization_name:
            payload['organization_name'] = organization_name
        elif getattr(employee, 'organization_name', None):
            payload['organization_name'] = getattr(employee, 'organization_name')
        
        return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate JWT token"""
        try:
            return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    async def logout(self, employee_id: int) -> bool:
        """Log logout event"""
        await self.audit_service.log_auth_action(
            action='LOGOUT',
            employee_id=employee_id
        )
        return True
    
    async def enter_organization(
        self,
        employee_id: int,
        organization_id: int,
        organization_name: str
    ) -> Optional[str]:
        """Create token with organization context"""
        employee = await Employee.find_by_id(employee_id)
        if not employee:
            return None
        
        token = self.create_token(employee, organization_id, organization_name)
        
        await self.audit_service.log_organization_action(
            organization_id=organization_id,
            action='ENTER',
            performed_by=employee_id
        )
        
        return token
    
    async def exit_organization(self, employee_id: int, organization_id: int) -> Optional[str]:
        """Create token without organization context"""
        employee = await Employee.find_by_id(employee_id)
        if not employee:
            return None
        
        token = self.create_token(employee)
        
        await self.audit_service.log_organization_action(
            organization_id=organization_id,
            action='EXIT',
            performed_by=employee_id
        )
        
        return token
