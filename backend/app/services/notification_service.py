"""
Notification Service
Sends WhatsApp notifications to staff for claim status updates
"""

from typing import Optional
from pathlib import Path
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
        
        # Build notes section if provided - limit to 100 chars
        notes_section = ""
        if notes:
            # Skip if notes is just OCR text (starts with [RECEIPT or contains "Extracted text")
            if not notes.startswith("[RECEIPT") and "Extracted text" not in notes:
                short_notes = notes[:100] + "..." if len(notes) > 100 else notes
                notes_section = f"\n📝 *Staff Note:* {short_notes}"
        
        # Indicate receipt will be forwarded
        receipt_indicator = "🧾 Receipt: Attached below"
        
        message = f"""🔔 *Claim Appeal Received*

📋 Claim #: *{full_claim['claim_number']}*
👤 Staff: {employee_name}
📁 Category: {full_claim.get('category_name', 'N/A')}
💵 Amount: {format_currency(amount)}
🔄 Appeal #: {full_claim.get('appeal_count', 1)}
{receipt_indicator}{notes_section}

━━━━━━━━━━━━━━━━━━━━
*Reply with one of:*
✅ *Approve {full_claim['id']}*
❌ *Reject {full_claim['id']} [reason]*
━━━━━━━━━━━━━━━━━━━━"""

        await waha_client.send_text(chat_id, message)
        print(f"✅ Sent appeal notification to manager {manager['name']}")
        
        # Forward the receipt if available
        try:
            print(f"🔍 Checking for receipts for claim {claim['id']}...")
            receipts = await claim_model.get_receipts(claim['id'])
            print(f"🔍 Found {len(receipts) if receipts else 0} receipts")
            
            if receipts and len(receipts) > 0:
                receipt = receipts[0]
                print(f"🔍 Receipt data: id={receipt.get('id')}, message_id={receipt.get('message_id')}")
                
                # Check if we have message_id stored
                if receipt.get('message_id'):
                    print(f"📤 Forwarding receipt message_id={receipt['message_id']} to {chat_id}")
                    result = await waha_client.forward_message(chat_id, receipt['message_id'])
                    if result:
                        print(f"✅ Forwarded receipt to manager {manager['name']} for appeal")
                    else:
                        print(f"⚠️ Could not forward receipt to manager for appeal (result=None)")
                else:
                    print(f"⚠️ Receipt found but no message_id available for forwarding (claim was created before this feature)")
            else:
                print(f"⚠️ No receipts found for claim {claim['id']}")
        except Exception as receipt_error:
            print(f"⚠️ Could not check for receipts: {receipt_error}")
            import traceback
            traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"❌ Error notifying manager of appeal: {e}")
        return False


async def notify_manager_of_new_claim(claim: dict, media_info: dict = None) -> bool:
    """
    Notify manager of a new claim submission, optionally forwarding the receipt/document
    
    Args:
        claim: The claim dict with all details
        media_info: Optional dict with 'url', 'data', 'mimetype', 'filename' for receipt
        
    Returns:
        True if notification sent successfully
    """
    try:
        # Get manager details
        manager_id = claim.get('manager_id')
        print(f"🔍 notify_manager_of_new_claim: claim_id={claim.get('id')}, manager_id={manager_id}")
        
        if not manager_id:
            print(f"⚠️ No manager assigned to claim {claim.get('id')}")
            return False
            
        manager = await employee_model.find_by_id(manager_id)
        print(f"🔍 Manager lookup result: {manager.get('name') if manager else 'Not found'}, whatsapp_chat_id={manager.get('whatsapp_chat_id') if manager else 'N/A'}")
        
        if not manager:
            print(f"❌ Manager {manager_id} not found in database")
            return False
            
        if not manager.get('whatsapp_chat_id'):
            print(f"⚠️ Manager {manager.get('name')} (ID: {manager_id}) has no WhatsApp chat ID.")
            
            # Fallback: Try to construct Chat ID from phone number
            if manager.get('phone_number'):
                # Basic normalization: remove non-digits
                phone = re.sub(r'[^0-9]', '', manager['phone_number'])
                # If it doesn't start with 94 (Sri Lanka), assuming it needs it for this system or passed as is?
                # Based on logs, phones seem to be 94... 
                # Let's assume the phone number in DB is correct for WAHA or needs minimal cleanup
                manager_chat_id = f"{phone}@c.us"
                print(f"🔄 Attempting fallback with constructed Chat ID: {manager_chat_id}")
            else:
                print(f"❌ Manager has no phone number either. Cannot send notification.")
                return False
        else:
            manager_chat_id = manager['whatsapp_chat_id']
            print(f"✅ Manager {manager.get('name')} has chat ID: {manager_chat_id}")
        
        # Get employee details
        employee = await employee_model.find_by_id(claim['employee_id'])
        employee_name = employee.get('name', 'Unknown') if employee else 'Unknown'
        
        # Get full claim details
        full_claim = await claim_model.find_by_id(claim['id'])
        amount = full_claim.get('user_amount') or full_claim.get('system_amount') or 0
        
        # Get receipts from database to show detailed breakdown
        receipts_from_db = await claim_model.get_receipts(claim['id'])
        
        # Helper to get public URL
        import os
        base_url = os.getenv('PUBLIC_BACKEND_URL', 'http://localhost:4101')
        
        # Build receipt details section with links
        receipt_section = ""
        if receipts_from_db and len(receipts_from_db) > 0:
            receipt_section = f"\n\n📎 *Receipts ({len(receipts_from_db)}):*"
            total_from_receipts = 0
            for i, receipt in enumerate(receipts_from_db, 1):
                receipt_amount = receipt.get('ocr_amount', 0)
                vendor = receipt.get('vendor') or 'Unknown'
                
                # Get link
                file_path = receipt.get('file_path')
                if file_path:
                    filename = Path(file_path).name
                    receipt_link = f"{base_url}/api/receipts/{claim['id']}/{filename}"
                else:
                    receipt_link = "N/A"
                
                receipt_section += f"\n  {i}. Rs. {receipt_amount:,.0f} - {vendor}"
                receipt_section += f"\n     🔗 {receipt_link}"
                
                total_from_receipts += receipt_amount
            
            if total_from_receipts > 0:
                receipt_section += f"\n\n🧮 *Total from receipts:* Rs. {total_from_receipts:,.0f}"
                
                # Validation: Check if receipts match claim amount
                # Validation: Check if receipts match claim amount
                if amount > 0:
                    # Convert both to float to ensure compatibility (Decimal vs Float issues)
                    amount_float = float(amount)
                    total_float = float(total_from_receipts)
                    
                    diff = abs(total_float - amount_float)
                    diff_pct = (diff / amount_float) * 100
                    
                    if diff_pct > 5:  # Alert if difference is > 5%
                        receipt_section += f"\n⚠️ *Difference:* Rs. {diff:,.0f} ({diff_pct:.1f}%)"
        else:
            receipt_section = "\n\n🧾 Receipt: Not provided"
        
        # Build the notification message
        message = f"""🔔 *New Claim Submitted*

📋 Claim #: *{full_claim['claim_number']}*
👤 Staff: {employee_name}
📁 Category: {full_claim.get('category_name', 'N/A')}
📍 Location: {full_claim.get('location_name', 'N/A')}
💵 Amount: {format_currency(amount)}
📝 Details: {full_claim.get('description', 'N/A')[:100]}{receipt_section}

━━━━━━━━━━━━━━━━━━━━
*Reply with one of:*
✅ *Approve {full_claim['id']}*
❌ *Reject {full_claim['id']} [reason]*
━━━━━━━━━━━━━━━━━━━━"""

        # Send the text message
        await waha_client.send_text(manager_chat_id, message)
        print(f"✅ Sent new claim notification to manager {manager['name']}")
        
        # Forward receipts - handle both WhatsApp forwards and Web uploads
        if receipts_from_db:
             for i, receipt in enumerate(receipts_from_db, 1):
                try:
                    # Case 1: WhatsApp Message (Forwarding)
                    if receipt.get('message_id'):
                        print(f"🔄 Forwarding receipt #{i} message to manager")
                        await waha_client.forward_message(manager_chat_id, receipt['message_id'])
                    
                    # Case 2: Web Upload (Send File)
                    elif receipt.get('file_path') and os.path.exists(receipt.get('file_path')):
                        print(f"📤 Sending local receipt file #{i} to manager")
                        file_path = receipt['file_path']
                        filename = receipt.get('file_name', f"receipt_{i}.jpg")
                        
                        # Determine if image or document
                        ext = os.path.splitext(filename)[1].lower()
                        if ext in ['.jpg', '.jpeg', '.png', '.webp']:
                            await waha_client.send_image(manager_chat_id, file_path, caption=f"Receipt #{i} - {receipt.get('vendor', 'Unknown')}")
                        else:
                            await waha_client.send_file(manager_chat_id, file_path, caption=f"Receipt #{i} - {receipt.get('vendor', 'Unknown')}")
                    else:
                        print(f"⚠️ Receipt #{i} has no message_id and file not found locally")
                        
                except Exception as e:
                    print(f"⚠️ Could not send receipt #{i}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error notifying manager of new claim: {e}")
        return False
