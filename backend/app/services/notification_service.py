"""
Notification Service
Sends WhatsApp notifications to staff for claim status updates
"""

from typing import Optional
from app import waha_client
from app.models import employee as employee_model
from app.models import claim as claim_model


def format_currency(amount: float) -> str:
    """Format amount as currency string"""
    return f"Rs.{amount:,.0f}"


async def notify_staff_of_approval(claim: dict) -> bool:
    """
    Send WhatsApp notification to staff when their claim is approved
    
    Args:
        claim: The claim dict with employee_id and claim details
        
    Returns:
        True if notification sent successfully
    """
    try:
        # Get employee details
        employee = await employee_model.find_by_id(claim['employee_id'])
        if not employee or not employee.get('whatsapp_chat_id'):
            print(f"⚠️ Cannot notify employee {claim['employee_id']}: No WhatsApp chat ID")
            return False
        
        chat_id = employee['whatsapp_chat_id']
        
        # Get full claim details
        full_claim = await claim_model.find_by_id(claim['id'])
        
        amount = full_claim.get('final_amount') or full_claim.get('system_amount') or 0
        
        message = f"""✅ *Claim Approved!*

📋 Claim #: *{full_claim['claim_number']}*
📁 Category: {full_claim.get('category_name', 'N/A')}
💵 Amount: {format_currency(amount)}

Your claim has been approved and will be processed for payment.

Type "hi" or "menu" to submit another claim."""

        await waha_client.send_text(chat_id, message)
        print(f"✅ Sent approval notification to {employee['name']}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending approval notification: {e}")
        return False


async def notify_staff_of_rejection(claim: dict, reason: str) -> bool:
    """
    Send WhatsApp notification to staff when their claim is rejected
    
    Args:
        claim: The claim dict with employee_id and claim details
        reason: The rejection reason from manager
        
    Returns:
        True if notification sent successfully
    """
    try:
        # Get employee details
        employee = await employee_model.find_by_id(claim['employee_id'])
        if not employee or not employee.get('whatsapp_chat_id'):
            print(f"⚠️ Cannot notify employee {claim['employee_id']}: No WhatsApp chat ID")
            return False
        
        chat_id = employee['whatsapp_chat_id']
        
        # Get full claim details
        full_claim = await claim_model.find_by_id(claim['id'])
        
        amount = full_claim.get('user_amount') or full_claim.get('system_amount') or 0
        
        message = f"""❌ *Claim Rejected*

📋 Claim #: *{full_claim['claim_number']}*
📁 Category: {full_claim.get('category_name', 'N/A')}
💵 Amount: {format_currency(amount)}

📝 *Reason:* {reason}

If you have questions, please contact your manager.
Type "hi" or "menu" to submit a new claim."""

        await waha_client.send_text(chat_id, message)
        print(f"✅ Sent rejection notification to {employee['name']}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending rejection notification: {e}")
        return False


async def notify_staff_claim_submitted(claim: dict, employee: dict) -> bool:
    """
    Send confirmation to staff when claim is submitted (optional enhanced message)
    
    Args:
        claim: The claim dict
        employee: The employee dict
        
    Returns:
        True if notification sent successfully
    """
    # This is optional - the reply_engine already sends confirmation
    # This can be used for additional notifications if needed
    return True
