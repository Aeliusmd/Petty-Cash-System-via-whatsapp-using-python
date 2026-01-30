"""
Audit Service
OOP class for centralized audit logging
"""

from typing import Optional, Dict, Any
from fastapi import Request
from app.services.base import BaseService
from app.models.audit_log import AuditLog


class AuditService(BaseService):
    """
    Service for centralized audit logging.
    Provides methods to log various entity actions with request context.
    """
    
    def __init__(self, request: Optional[Request] = None):
        """Initialize with optional request for IP/user-agent extraction"""
        super().__init__(request)
    
    async def _create_log(
        self,
        entity_type: str,
        entity_id: int,
        action: str,
        old_values: Dict = None,
        new_values: Dict = None,
        performed_by: int = None,
        organization_id: int = None,
        metadata: Dict = None
    ) -> Optional[Dict]:
        """Internal method to create audit log with request info"""
        request_info = self.get_request_info()
        
        log = await AuditLog.create({
            'entity_type': entity_type,
            'entity_id': entity_id,
            'action': action,
            'old_values': old_values,
            'new_values': new_values,
            'performed_by': performed_by,
            'ip_address': request_info['ip_address'],
            'user_agent': request_info['user_agent'],
            'organization_id': organization_id,
            'metadata': metadata
        })
        return log.to_dict() if log else None
    
    async def log_claim_action(
        self,
        claim_id: int,
        action: str,
        old_values: Dict = None,
        new_values: Dict = None,
        performed_by: int = None,
        organization_id: int = None,
        metadata: Dict = None
    ) -> Optional[Dict]:
        """Log a claim-related action (CREATE, UPDATE, APPROVE, REJECT, APPEAL, etc.)"""
        return await self._create_log(
            'claim', claim_id, action,
            old_values, new_values, performed_by, organization_id, metadata
        )
    
    async def log_employee_action(
        self,
        employee_id: int,
        action: str,
        old_values: Dict = None,
        new_values: Dict = None,
        performed_by: int = None,
        organization_id: int = None,
        metadata: Dict = None
    ) -> Optional[Dict]:
        """Log an employee-related action (CREATE, UPDATE, DELETE, ROLE_CHANGE, etc.)"""
        return await self._create_log(
            'employee', employee_id, action,
            old_values, new_values, performed_by, organization_id, metadata
        )
    
    async def log_auth_action(
        self,
        action: str,
        employee_id: int = None,
        metadata: Dict = None,
        organization_id: int = None
    ) -> Optional[Dict]:
        """Log an authentication-related action (LOGIN, LOGOUT, OTP_REQUEST, etc.)"""
        return await self._create_log(
            'auth', employee_id, action,
            performed_by=employee_id, organization_id=organization_id, metadata=metadata
        )
    
    async def log_organization_action(
        self,
        organization_id: int,
        action: str,
        old_values: Dict = None,
        new_values: Dict = None,
        performed_by: int = None,
        metadata: Dict = None
    ) -> Optional[Dict]:
        """Log an organization-related action (CREATE, UPDATE, DELETE, ENTER, EXIT, etc.)"""
        return await self._create_log(
            'organization', organization_id, action,
            old_values, new_values, performed_by, organization_id, metadata
        )
    
    async def log_config_action(
        self,
        entity_type: str,
        entity_id: int,
        action: str,
        old_values: Dict = None,
        new_values: Dict = None,
        performed_by: int = None,
        organization_id: int = None,
        metadata: Dict = None
    ) -> Optional[Dict]:
        """Log a configuration-related action (batta_rate, category_cap, grade, location, etc.)"""
        return await self._create_log(
            entity_type, entity_id, action,
            old_values, new_values, performed_by, organization_id, metadata
        )
    
    async def log_receipt_action(
        self,
        receipt_id: int,
        claim_id: int,
        action: str,
        metadata: Dict = None,
        performed_by: int = None,
        organization_id: int = None
    ) -> Optional[Dict]:
        """Log a receipt-related action (UPLOAD, OCR_EXTRACT, DELETE, etc.)"""
        return await self._create_log(
            'receipt', receipt_id, action,
            metadata={'claim_id': claim_id, **(metadata or {})},
            performed_by=performed_by, organization_id=organization_id
        )


# Backward compatibility - module-level functions that use the class
def extract_request_info(request: Request) -> tuple:
    """Extract IP address and user agent from request"""
    service = AuditService(request)
    info = service.get_request_info()
    return info['ip_address'], info['user_agent']


async def log_claim_action(
    claim_id: int,
    action: str,
    old_values: Dict = None,
    new_values: Dict = None,
    performed_by: int = None,
    request: Request = None,
    organization_id: int = None,
    metadata: Dict = None
):
    service = AuditService(request)
    return await service.log_claim_action(
        claim_id, action, old_values, new_values, performed_by, organization_id, metadata
    )


async def log_employee_action(
    employee_id: int,
    action: str,
    old_values: Dict = None,
    new_values: Dict = None,
    performed_by: int = None,
    request: Request = None,
    organization_id: int = None,
    metadata: Dict = None
):
    service = AuditService(request)
    return await service.log_employee_action(
        employee_id, action, old_values, new_values, performed_by, organization_id, metadata
    )


async def log_auth_action(
    action: str,
    employee_id: int = None,
    metadata: Dict = None,
    request: Request = None,
    organization_id: int = None
):
    service = AuditService(request)
    return await service.log_auth_action(action, employee_id, metadata, organization_id)


async def log_organization_action(
    organization_id: int,
    action: str,
    old_values: Dict = None,
    new_values: Dict = None,
    performed_by: int = None,
    request: Request = None,
    metadata: Dict = None
):
    service = AuditService(request)
    return await service.log_organization_action(
        organization_id, action, old_values, new_values, performed_by, metadata
    )


async def log_config_action(
    entity_type: str,
    entity_id: int,
    action: str,
    old_values: Dict = None,
    new_values: Dict = None,
    performed_by: int = None,
    request: Request = None,
    organization_id: int = None,
    metadata: Dict = None
):
    service = AuditService(request)
    return await service.log_config_action(
        entity_type, entity_id, action, old_values, new_values, performed_by, organization_id, metadata
    )


async def log_receipt_action(
    receipt_id: int,
    claim_id: int,
    action: str,
    metadata: Dict = None,
    performed_by: int = None,
    request: Request = None,
    organization_id: int = None
):
    service = AuditService(request)
    return await service.log_receipt_action(
        receipt_id, claim_id, action, metadata, performed_by, organization_id
    )
