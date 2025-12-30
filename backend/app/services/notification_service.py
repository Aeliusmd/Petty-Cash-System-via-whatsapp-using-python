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

💡 Reply *appeal* to request another review.
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


async def notify_staff_of_appeal_submitted(claim: dict) -> bool:
    """
    Send WhatsApp notification to staff confirming their appeal was submitted
    
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
        
        message = f"""📤 *Appeal Submitted!*

📋 Claim #: *{full_claim['claim_number']}*
📁 Category: {full_claim.get('category_name', 'N/A')}

Your claim has been sent for review again.
You will be notified of the decision.

Type "hi" or "menu" for more options."""

        await waha_client.send_text(chat_id, message)
        print(f"✅ Sent appeal confirmation to {employee['name']}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending appeal confirmation: {e}")
        return False


async def notify_manager_of_appeal(claim: dict, notes: str = None) -> bool:
    """
    Notify manager that a claim has been appealed
    
    Args:
        claim: The claim dict
        notes: Optional notes from staff explaining the appeal
        
    Returns:
        True if notification sent successfully
    """
    try:
        # Get manager details
        manager_id = claim.get('manager_id')
        if not manager_id:
            print(f"⚠️ No manager assigned to claim {claim.get('id')}")
            return False
            
        manager = await employee_model.find_by_id(manager_id)
        if not manager or not manager.get('whatsapp_chat_id'):
            print(f"⚠️ Manager {manager_id} has no WhatsApp chat ID")
            return False
        
        chat_id = manager['whatsapp_chat_id']
        
        # Get employee details
        employee = await employee_model.find_by_id(claim['employee_id'])
        employee_name = employee.get('name', 'Unknown') if employee else 'Unknown'
        
        # Get full claim details
        full_claim = await claim_model.find_by_id(claim['id'])
        amount = full_claim.get('user_amount') or full_claim.get('system_amount') or 0
        
        # Build notes section if provided
        notes_section = f"\n\n📝 *Staff Note:* {notes}" if notes else ""
        
        message = f"""🔔 *Claim Appeal Received*

📋 Claim #: *{full_claim['claim_number']}*
👤 Staff: {employee_name}
📁 Category: {full_claim.get('category_name', 'N/A')}
💵 Amount: {format_currency(amount)}
🔄 Appeal #: {full_claim.get('appeal_count', 1)}{notes_section}

Please review this appeal in the admin panel."""

        await waha_client.send_text(chat_id, message)
        print(f"✅ Sent appeal notification to manager {manager['name']}")
        return True
        
    except Exception as e:
        print(f"❌ Error notifying manager of appeal: {e}")
        return False
