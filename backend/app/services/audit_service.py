"""
Audit Service
Centralized service for logging all audit events
"""

from typing import Optional, Dict, Any
from fastapi import Request
from app.models import audit_log


def extract_request_info(request: Request) -> tuple[str, str]:
    """
    Extract IP address and user agent from request
    
    Args:
        request: FastAPI Request object
    
    Returns:
        Tuple of (ip_address, user_agent)
    """
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    return ip_address, user_agent


async def log_claim_action(
    claim_id: int,
    action: str,
    old_values: Optional[Dict] = None,
    new_values: Optional[Dict] = None,
    performed_by: Optional[int] = None,
    request: Optional[Request] = None,
    organization_id: Optional[int] = None,
    metadata: Optional[Dict] = None
) -> Optional[Dict[str, Any]]:
    """
    Log a claim-related action
    
    Args:
        claim_id: Claim ID
        action: Action type (CREATE, UPDATE, APPROVE, REJECT, APPEAL, etc.)
        old_values: Previous claim values
        new_values: New claim values
        performed_by: Employee ID who performed the action
        request: FastAPI Request object
        organization_id: Organization context
        metadata: Additional metadata
    
    Returns:
        Created audit log entry
    """
    try:
        ip_address, user_agent = extract_request_info(request) if request else ("system", "system")
        
        return await audit_log.create(
            entity_type="claim",
            entity_id=claim_id,
            action=action,
            old_values=old_values,
            new_values=new_values,
            performed_by=performed_by,
            ip_address=ip_address,
            user_agent=user_agent,
            organization_id=organization_id,
            metadata=metadata
        )
    except Exception as e:
        # Log error but don't fail the main operation
        print(f"❌ Error logging claim audit: {e}")
        return None


async def log_employee_action(
    employee_id: int,
    action: str,
    old_values: Optional[Dict] = None,
    new_values: Optional[Dict] = None,
    performed_by: Optional[int] = None,
    request: Optional[Request] = None,
    organization_id: Optional[int] = None,
    metadata: Optional[Dict] = None
) -> Optional[Dict[str, Any]]:
    """
    Log an employee-related action
    
    Args:
        employee_id: Employee ID
        action: Action type (CREATE, UPDATE, DELETE, ROLE_CHANGE, etc.)
        old_values: Previous employee values
        new_values: New employee values
        performed_by: Employee ID who performed the action
        request: FastAPI Request object
        organization_id: Organization context
        metadata: Additional metadata
    
    Returns:
        Created audit log entry
    """
    try:
        ip_address, user_agent = extract_request_info(request) if request else ("system", "system")
        
        return await audit_log.create(
            entity_type="employee",
            entity_id=employee_id,
            action=action,
            old_values=old_values,
            new_values=new_values,
            performed_by=performed_by,
            ip_address=ip_address,
            user_agent=user_agent,
            organization_id=organization_id,
            metadata=metadata
        )
    except Exception as e:
        print(f"❌ Error logging employee audit: {e}")
        return None


async def log_auth_action(
    action: str,
    employee_id: Optional[int] = None,
    metadata: Optional[Dict] = None,
    request: Optional[Request] = None,
    organization_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Log an authentication-related action
    
    Args:
        action: Action type (LOGIN, LOGOUT, OTP_REQUEST, OTP_VERIFY, FAILED_LOGIN, etc.)
        employee_id: Employee ID (if applicable)
        metadata: Additional metadata (e.g., phone_number, success/failure reason)
        request: FastAPI Request object
        organization_id: Organization context
    
    Returns:
        Created audit log entry
    """
    try:
        ip_address, user_agent = extract_request_info(request) if request else ("system", "system")
        
        return await audit_log.create(
            entity_type="auth",
            entity_id=employee_id,
            action=action,
            old_values=None,
            new_values=None,
            performed_by=employee_id,
            ip_address=ip_address,
            user_agent=user_agent,
            organization_id=organization_id,
            metadata=metadata
        )
    except Exception as e:
        print(f"❌ Error logging auth audit: {e}")
        return None


async def log_organization_action(
    organization_id: int,
    action: str,
    old_values: Optional[Dict] = None,
    new_values: Optional[Dict] = None,
    performed_by: Optional[int] = None,
    request: Optional[Request] = None,
    metadata: Optional[Dict] = None
) -> Optional[Dict[str, Any]]:
    """
    Log an organization-related action
    
    Args:
        organization_id: Organization ID
        action: Action type (CREATE, UPDATE, DELETE, ENTER, EXIT, etc.)
        old_values: Previous organization values
        new_values: New organization values
        performed_by: Employee ID who performed the action
        request: FastAPI Request object
        metadata: Additional metadata
    
    Returns:
        Created audit log entry
    """
    try:
        ip_address, user_agent = extract_request_info(request) if request else ("system", "system")
        
        return await audit_log.create(
            entity_type="organization",
            entity_id=organization_id,
            action=action,
            old_values=old_values,
            new_values=new_values,
            performed_by=performed_by,
            ip_address=ip_address,
            user_agent=user_agent,
            organization_id=organization_id,
            metadata=metadata
        )
    except Exception as e:
        print(f"❌ Error logging organization audit: {e}")
        return None


async def log_config_action(
    entity_type: str,
    entity_id: Optional[int],
    action: str,
    old_values: Optional[Dict] = None,
    new_values: Optional[Dict] = None,
    performed_by: Optional[int] = None,
    request: Optional[Request] = None,
    organization_id: Optional[int] = None,
    metadata: Optional[Dict] = None
) -> Optional[Dict[str, Any]]:
    """
    Log a configuration-related action (batta_rate, category_cap, grade, location, etc.)
    
    Args:
        entity_type: Type of configuration entity
        entity_id: Entity ID
        action: Action type (CREATE, UPDATE, DELETE, etc.)
        old_values: Previous values
        new_values: New values
        performed_by: Employee ID who performed the action
        request: FastAPI Request object
        organization_id: Organization context
        metadata: Additional metadata
    
    Returns:
        Created audit log entry
    """
    try:
        ip_address, user_agent = extract_request_info(request) if request else ("system", "system")
        
        return await audit_log.create(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_values=old_values,
            new_values=new_values,
            performed_by=performed_by,
            ip_address=ip_address,
            user_agent=user_agent,
            organization_id=organization_id,
            metadata=metadata
        )
    except Exception as e:
        print(f"❌ Error logging config audit: {e}")
        return None


async def log_receipt_action(
    receipt_id: int,
    claim_id: int,
    action: str,
    metadata: Optional[Dict] = None,
    performed_by: Optional[int] = None,
    request: Optional[Request] = None,
    organization_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Log a receipt-related action
    
    Args:
        receipt_id: Receipt ID
        claim_id: Associated claim ID
        action: Action type (UPLOAD, OCR_EXTRACT, DELETE, etc.)
        metadata: Additional metadata (e.g., file_name, ocr_amount, vendor)
        performed_by: Employee ID who performed the action
        request: FastAPI Request object
        organization_id: Organization context
    
    Returns:
        Created audit log entry
    """
    try:
        ip_address, user_agent = extract_request_info(request) if request else ("system", "system")
        
        # Add claim_id to metadata
        if metadata is None:
            metadata = {}
        metadata['claim_id'] = claim_id
        
        return await audit_log.create(
            entity_type="receipt",
            entity_id=receipt_id,
            action=action,
            old_values=None,
            new_values=None,
            performed_by=performed_by,
            ip_address=ip_address,
            user_agent=user_agent,
            organization_id=organization_id,
            metadata=metadata
        )
    except Exception as e:
        print(f"❌ Error logging receipt audit: {e}")
        return None
