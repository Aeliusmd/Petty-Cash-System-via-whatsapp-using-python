"""
Audit Log Description Generator
Creates human-readable descriptions from audit log data
"""

from typing import Dict, Any, Optional


def format_claim_description(log: Dict[str, Any]) -> str:
    """Generate human-readable description for claim audit logs"""
    action = log.get('action', '')
    old_values = log.get('old_values', {})
    new_values = log.get('new_values', {})
    metadata = log.get('metadata', {})
    performed_by = log.get('performed_by_name', 'System')
    claim_number = metadata.get('claim_number', f"#{log.get('entity_id')}")
    
    if action == 'APPROVE':
        old_status = old_values.get('status', 'PENDING')
        final_amount = new_values.get('final_amount', 0)
        return f"**{performed_by}** approved claim **{claim_number}** (Rs.{final_amount:,.2f}) - Status changed from {old_status} to APPROVED"
    
    elif action == 'REJECT':
        old_status = old_values.get('status', 'PENDING')
        reason = metadata.get('reason', 'No reason provided')
        return f"**{performed_by}** rejected claim **{claim_number}** - Reason: \"{reason}\""
    
    elif action == 'CREATE':
        amount = new_values.get('user_amount') or new_values.get('system_amount', 0)
        category = metadata.get('category', 'Unknown')
        return f"**{performed_by}** created claim **{claim_number}** for Rs.{amount:,.2f} ({category})"
    
    elif action == 'DELETE':
        amount = old_values.get('final_amount') or old_values.get('user_amount', 0)
        status = old_values.get('status', 'UNKNOWN')
        return f"**{performed_by}** deleted claim **{claim_number}** (Rs.{amount:,.2f}, Status: {status})"
    
    elif action == 'APPEAL':
        return f"**{performed_by}** appealed rejected claim **{claim_number}**"
    
    elif action == 'UPDATE':
        changes = []
        if 'user_amount' in new_values and old_values.get('user_amount') != new_values.get('user_amount'):
            changes.append(f"amount: Rs.{old_values.get('user_amount', 0):,.2f} → Rs.{new_values.get('user_amount', 0):,.2f}")
        if 'description' in new_values:
            changes.append("description updated")
        change_text = ", ".join(changes) if changes else "claim details"
        return f"**{performed_by}** updated claim **{claim_number}** - Changed: {change_text}"
    
    return f"**{performed_by}** performed {action} on claim **{claim_number}**"


def format_employee_description(log: Dict[str, Any]) -> str:
    """Generate human-readable description for employee audit logs"""
    action = log.get('action', '')
    old_values = log.get('old_values', {})
    new_values = log.get('new_values', {})
    metadata = log.get('metadata', {})
    performed_by = log.get('performed_by_name', 'System')
    employee_name = metadata.get('employee_name', f"Employee #{log.get('entity_id')}")
    
    if action == 'CREATE':
        role = new_values.get('role', 'staff')
        return f"**{performed_by}** created employee **{employee_name}** with role: {role}"
    
    elif action == 'UPDATE':
        changes = []
        if old_values.get('role') != new_values.get('role'):
            changes.append(f"role: {old_values.get('role')} → {new_values.get('role')}")
        if old_values.get('is_active') != new_values.get('is_active'):
            status = "activated" if new_values.get('is_active') else "deactivated"
            changes.append(status)
        change_text = ", ".join(changes) if changes else "employee details"
        return f"**{performed_by}** updated employee **{employee_name}** - Changed: {change_text}"
    
    elif action == 'DELETE':
        return f"**{performed_by}** deleted employee **{employee_name}**"
    
    elif action == 'ROLE_CHANGE':
        old_role = old_values.get('role', 'unknown')
        new_role = new_values.get('role', 'unknown')
        return f"**{performed_by}** changed **{employee_name}**'s role from {old_role} to {new_role}"
    
    return f"**{performed_by}** performed {action} on employee **{employee_name}**"


def format_auth_description(log: Dict[str, Any]) -> str:
    """Generate human-readable description for auth audit logs"""
    action = log.get('action', '')
    metadata = log.get('metadata', {})
    performed_by = log.get('performed_by_name', 'Unknown User')
    
    if action == 'LOGIN':
        return f"**{performed_by}** logged in successfully"
    
    elif action == 'LOGOUT':
        return f"**{performed_by}** logged out"
    
    elif action == 'OTP_REQUEST':
        phone = metadata.get('phone_number', 'Unknown')
        return f"OTP requested for phone number {phone}"
    
    elif action == 'OTP_VERIFY':
        success = metadata.get('success', False)
        if success:
            return f"**{performed_by}** verified OTP successfully"
        return f"Failed OTP verification attempt for {performed_by}"
    
    elif action == 'FAILED_LOGIN':
        reason = metadata.get('reason', 'Unknown')
        return f"Failed login attempt - Reason: {reason}"
    
    return f"{action} - {performed_by}"


def format_organization_description(log: Dict[str, Any]) -> str:
    """Generate human-readable description for organization audit logs"""
    action = log.get('action', '')
    metadata = log.get('metadata', {})
    performed_by = log.get('performed_by_name', 'System')
    org_name = log.get('organization_name', f"Organization #{log.get('entity_id')}")
    
    if action == 'ENTER':
        return f"**{performed_by}** (Super Admin) entered organization **{org_name}**"
    
    elif action == 'EXIT':
        return f"**{performed_by}** (Super Admin) exited organization **{org_name}**"
    
    elif action == 'CREATE':
        return f"**{performed_by}** created organization **{org_name}**"
    
    elif action == 'UPDATE':
        return f"**{performed_by}** updated organization **{org_name}**"
    
    elif action == 'DELETE':
        return f"**{performed_by}** deleted organization **{org_name}**"
    
    return f"**{performed_by}** performed {action} on organization **{org_name}**"


def format_receipt_description(log: Dict[str, Any]) -> str:
    """Generate human-readable description for receipt audit logs"""
    action = log.get('action', '')
    metadata = log.get('metadata', {})
    performed_by = log.get('performed_by_name', 'System')
    claim_number = metadata.get('claim_number', 'Unknown')
    file_name = metadata.get('file_name', 'receipt')
    
    if action == 'UPLOAD':
        if claim_number != 'Unknown' and claim_number != '0':
            return f"**{performed_by}** uploaded receipt **{file_name}** for claim **{claim_number}**"
        else:
            return f"**{performed_by}** uploaded receipt **{file_name}**"
    
    elif action == 'OCR_EXTRACT':
        amount = metadata.get('ocr_amount', 0)
        vendor = metadata.get('vendor', 'Unknown')
        return f"OCR extracted from receipt for claim **{claim_number}** - Amount: Rs.{amount:,.2f}, Vendor: {vendor}"
    
    elif action == 'DELETE':
        return f"**{performed_by}** deleted receipt **{file_name}** from claim **{claim_number}**"
    
    return f"**{performed_by}** performed {action} on receipt for claim **{claim_number}**"


def get_audit_description(log: Dict[str, Any]) -> str:
    """
    Generate human-readable description for any audit log entry
    
    Args:
        log: Audit log dictionary
    
    Returns:
        Human-readable description string
    """
    entity_type = log.get('entity_type', '')
    
    if entity_type == 'claim':
        return format_claim_description(log)
    elif entity_type == 'employee':
        return format_employee_description(log)
    elif entity_type == 'auth':
        return format_auth_description(log)
    elif entity_type == 'organization':
        return format_organization_description(log)
    elif entity_type == 'receipt':
        return format_receipt_description(log)
    else:
        # Generic fallback
        action = log.get('action', 'UNKNOWN')
        performed_by = log.get('performed_by_name', 'System')
        entity_id = log.get('entity_id', 'Unknown')
        return f"**{performed_by}** performed {action} on {entity_type} #{entity_id}"
