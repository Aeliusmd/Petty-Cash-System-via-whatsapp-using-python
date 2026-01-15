"""
Reply Engine (Database-Integrated)
Handles conversation logic with PostgreSQL backend

Features:
- Only responds to registered employees (phone number check)
- Dynamic batta rate calculation from database
- Claims saved to database
- Persistent conversation state
"""

import re
from typing import Optional

from app.models import employee as employee_model
from app.models import rates as rates_model
from app.models import claim as claim_model
from app.models import conversation as conversation_model
from app.services.location_service import location_service
from app import waha_client


def normalize_text(text: str) -> str:
    """Normalize message text for comparison"""
    return (text or '').lower().strip()


def is_lid_format(chat_id: str) -> bool:
    """Check if chat ID is in Linked ID format (unsaved contact)"""
    return chat_id and '@lid' in chat_id.lower()


def extract_phone_from_chat_id(chat_id: str) -> Optional[str]:
    """
    Extract phone number from chat ID
    Chat IDs are typically in format: 94771234567@c.us
    
    For LID (Linked ID) format like 29545113604243@lid_xxx, returns None
    because the number is not a valid phone number - it's a WhatsApp internal ID.
    """
    if not chat_id:
        return None
    
    # LID format doesn't contain real phone numbers
    if is_lid_format(chat_id):
        print(f"⚠️ LID format detected: {chat_id[:30]}... - this is an unsaved contact")
        return None
    
    # Extract just the number part before @
    number_part = chat_id.split('@')[0]
    phone = re.sub(r'\D', '', number_part)
    
    # Validate it looks like a phone number (9-15 digits for international numbers)
    if len(phone) < 9 or len(phone) > 15:
        print(f"⚠️ Invalid phone number length ({len(phone)} digits): {phone}")
        return None
    
    return phone


def is_group_chat(chat_id: str) -> bool:
    """Check if chat is from a group (we don't respond to groups)"""
    return chat_id and '@g.us' in chat_id


async def find_location_in_text(text: str) -> Optional[dict]:
    """Find location from text input"""
    locations = await rates_model.get_all_locations()
    lower_text = text.lower()
    
    for loc in locations:
        if (loc['name'].lower() in lower_text or 
            loc['code'].lower() in lower_text):
            return loc
    return None


def extract_days(text: str) -> int:
    """Extract days from text (e.g., "2 days", "3days", "5 day")"""
    match = re.search(r'(\d+)\s*days?', text, re.IGNORECASE)
    return int(match.group(1)) if match else 1


def extract_amount(text: str) -> Optional[float]:
    """
    Extract amount from text (e.g., "Rs.5000", "LKR 3000", "5000")
    Prioritizes amounts with currency prefix over bare numbers
    """
    if not text:
        return None
    
    # First try to find amounts with explicit currency prefix (Rs., LKR, රු.)
    currency_match = re.search(r'(?:rs\.?|lkr\.?|රු\.?)\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', text, re.IGNORECASE)
    if currency_match:
        return float(currency_match.group(1).replace(',', ''))
    
    # Look for amounts at end of text or standalone large numbers (likely to be prices)
    # Avoid extracting small numbers like "3" from "3 nights"
    large_num_match = re.search(r'\b(\d{3,}(?:,\d{3})*(?:\.\d{2})?)\b', text)
    if large_num_match:
        return float(large_num_match.group(1).replace(',', ''))
    
    return None


def format_currency(amount: float) -> str:
    """Format amount as currency string"""
    return f"Rs.{amount:,.0f}"


async def generate_reply(message_text: str, chat_id: str, media_info: dict = None) -> Optional[str]:
    """
    Main reply generation function
    
    Args:
        message_text: The incoming message text
        chat_id: The chat ID for conversation context
        media_info: Optional dict with media info (url, data, mimetype, filename)
        
    Returns:
        Reply text or None if no reply
    """
    from app.services import notification_service
    
    # 1. Skip group chats entirely
    if is_group_chat(chat_id):
        print(f'⏭️ Skipping group chat: {chat_id}')
        return None

    # 2. Extract phone number from chat ID
    phone_number = None
    
    # Check for LID format (unsaved contact in WhatsApp)
    if is_lid_format(chat_id):
        print(f'🔍 LID format detected ({chat_id[:30]}...), attempting to resolve to phone via WAHA API...')
        lid_info = await waha_client.get_lid_info(chat_id)
        if lid_info and lid_info.get('pn'):
            phone_number = str(lid_info.get('pn'))
            print(f"✅ Resolved LID {chat_id[:15]}... to phone: {phone_number}")
        else:
            print(f"⚠️ Failed to resolve LID {chat_id[:30]}...")
    else:
        # Standard format
        phone_number = extract_phone_from_chat_id(chat_id)
    
    # 3. If can't extract phone, silently ignore (no error message)
    if not phone_number:
        print(f'⏭️ Could not extract valid phone from chatId: {chat_id[:50]}... - silently ignoring')
        return None

    # 4. Check if this phone number is registered in the database
    employee = await employee_model.find_by_phone(phone_number)
    
    # Also try to find by chat ID if phone lookup fails
    if not employee:
        employee = await employee_model.find_by_chat_id(chat_id)

    # 5. If not registered, silently ignore (no response)
    if not employee:
        print(f'⏭️ Unregistered number, silently ignoring: {phone_number}')
        return None

    # 5. Link chat ID to employee if not already linked
    if not employee.get('whatsapp_chat_id'):
        await employee_model.link_chat_id(employee['id'], chat_id)
        print(f"🔗 Linked chat ID to employee: {employee['name']}")

    # Get or create conversation state
    state = await conversation_model.get_or_create(chat_id)
    if not state.get('employee_id'):
        await conversation_model.link_employee(chat_id, employee['id'])
        state = await conversation_model.get_with_employee(chat_id)

    text = normalize_text(message_text)
    context = state.get('context') or {}
    
    # Handle JSON context if it's a string
    if isinstance(context, str):
        import json
        try:
            context = json.loads(context)
        except:
            context = {}

    # ===== HANDLE LOCATION SHARED =====
    if '[LOCATION_SHARED]' in message_text:
        match = re.search(r'lat:([0-9.-]+) lon:([0-9.-]+)', message_text)
        if match:
            lat, lon = float(match.group(1)), float(match.group(2))
            
            # 1. Reverse geocode to get city
            city = await location_service.get_city_from_coordinates(lat, lon)
            
            if not city:
                return "❌ Could not detect city from location. Please enter it manually (e.g., 'Kandy')."
            
            # 2. Find nearest business location
            location = await location_service.find_nearest_business_location(city)
            
            if not location:
                return f"📍 Detected City: *{city}*\n❌ This location is not in our system. Please enter a valid business location manually."
            
            # 3. Auto-start Batta Claim
            # Get batta rate
            rate = await rates_model.get_batta_rate(employee['grade_id'], location['id'])
            
            if not rate:
                return f"📍 Detected: *{location['name']}*\n⚠️ No batta rate found for Grade {employee.get('grade_code')}. Please contact admin."

            await conversation_model.update(chat_id, {
                'current_step': 'batta_days',
                'category': 'BATTA',
                'context': {
                    'location_id': location['id'],
                    'location_name': location['name'],
                    'rate_per_day': rate,
                    'detected_from_gps': True
                }
            })

            return f"""📍 Location Detected: *{location['name']}*
💰 Rate: *{format_currency(rate)}/day* (Grade {employee.get('grade_code')})

How many days?"""

    # ===== HANDLE MANAGER APPROVE/REJECT COMMANDS =====
    # Check if employee is a manager and handle approve/reject commands
    is_manager = employee.get('is_manager', False) or employee.get('is_admin', False)
    
    # Clean text: remove emojis and extra whitespace for command matching
    clean_text = re.sub(r'[^\w\s#-]', '', text).strip()
    
    # Approve command: flexible matching - "approve 123", "✅ Approve 12", "Approve #12", etc.
    approve_match = re.search(r'\bapprove\s*#?(\d+)\b', clean_text, re.IGNORECASE)
    if approve_match and is_manager:
        claim_id = int(approve_match.group(1))
        try:
            # Find the claim
            claim = await claim_model.find_by_id(claim_id)
            if not claim:
                return f"❌ Claim #{claim_id} not found."
            
            # Verify this manager is authorized to approve this claim
            if claim.get('manager_id') != employee['id']:
                return f"❌ You are not authorized to approve this claim."
            
            # Check status
            current_status = claim.get('status_code')
            if current_status not in ('PENDING', 'APPEALED'):
                return f"❌ Claim #{claim_id} is already {claim.get('status_name')}."
            
            # Record status change
            await claim_model.record_status_change(
                claim_id, current_status, 'APPROVED', employee['id'], 'Approved via WhatsApp'
            )
            
            # Approve the claim
            await claim_model.approve(claim_id, employee['id'])
            
            # Notify the employee
            await notification_service.notify_staff_of_approval(claim)
            
            return f"""✅ *Claim Approved!*

📋 Claim #: *{claim['claim_number']}*
👤 Staff: {claim.get('employee_name', 'N/A')}
💵 Amount: {format_currency(claim.get('user_amount') or claim.get('system_amount') or 0)}

The employee has been notified."""
        except Exception as e:
            print(f"❌ Error approving claim via WhatsApp: {e}")
            return f"❌ Error approving claim. Please try again."
    
    # Reject command: flexible matching - "reject 123 reason", "❌ Reject #12 Invalid", etc.
    reject_match = re.search(r'\breject\s*#?(\d+)(?:\s+(.+))?', clean_text, re.IGNORECASE)
    if reject_match and is_manager:
        claim_id = int(reject_match.group(1))
        reason = reject_match.group(2).strip() if reject_match.group(2) else None
        
        # If no reason provided, ask for it
        if not reason or len(reason) < 3:
            return f"""❌ Please provide a rejection reason.

Example: *Reject {claim_id} Invalid receipt* or *Reject {claim_id} Missing details*"""
        
        try:
            # Find the claim
            claim = await claim_model.find_by_id(claim_id)
            if not claim:
                return f"❌ Claim #{claim_id} not found."
            
            # Verify this manager is authorized
            if claim.get('manager_id') != employee['id']:
                return f"❌ You are not authorized to reject this claim."
            
            # Check status
            current_status = claim.get('status_code')
            if current_status not in ('PENDING', 'APPEALED'):
                return f"❌ Claim #{claim_id} is already {claim.get('status_name')}."
            
            # Record status change
            await claim_model.record_status_change(
                claim_id, current_status, 'REJECTED', employee['id'], reason
            )
            
            # Reject the claim
            await claim_model.reject(claim_id, employee['id'], reason)
            
            # Notify the employee
            await notification_service.notify_staff_of_rejection(claim, reason)
            
            return f"""❌ *Claim Rejected*

📋 Claim #: *{claim['claim_number']}*
👤 Staff: {claim.get('employee_name', 'N/A')}
📝 Reason: {reason}

The employee has been notified and can appeal."""
        except Exception as e:
            print(f"❌ Error rejecting claim via WhatsApp: {e}")
            return f"❌ Error rejecting claim. Please try again."
    


    # ===== HANDLE GREETINGS - SHOW MAIN MENU =====
    if text in ('hi', 'hello', 'hey', 'menu', 'start'):
        await conversation_model.update(chat_id, {
            'current_step': 'menu',
            'category': None,
            'context': {}
        })
        
        return f"""🙏 Welcome, *{employee['name']}*!

You are registered as Grade {employee.get('grade_code') or 'N/A'} at {employee.get('location_name') or 'N/A'}.

Please select a category:
1️⃣ Batta (Daily Allowance)
2️⃣ Fuel Expenses
3️⃣ Accommodation
4️⃣ Sundry Expenses

Reply with the number or category name."""

    # ===== HANDLE APPEAL COMMAND =====
    if text == 'appeal':
        # Find the most recent rejected claim for this employee
        rejected_claim = await claim_model.find_latest_rejected_for_employee(employee['id'])
        
        if not rejected_claim:
            return """❌ *No rejected claims found*

You don't have any rejected claims to appeal.
Type "hi" for the main menu."""
        
        # Start appeal flow - ask for notes
        await conversation_model.update(chat_id, {
            'current_step': 'appeal_notes',
            'category': 'APPEAL',
            'context': {
                'claim_id': rejected_claim['id'],
                'claim_number': rejected_claim['claim_number'],
                'category_name': rejected_claim.get('category_name', 'N/A')
            }
        })
        
        return f"""🔄 *Appeal Claim #{rejected_claim['claim_number']}*

📁 Category: {rejected_claim.get('category_name', 'N/A')}
📝 Previous Rejection: {rejected_claim.get('rejection_reason', 'No reason provided')}

Please add a note explaining why you are appealing:
_(You can also upload additional documents/receipts)_

Or type *skip* to submit without notes."""

    # ===== HANDLE APPEAL NOTES STEP =====
    current_step = state.get('current_step', 'initial')
    
    if current_step == 'appeal_notes':
        from app.services import notification_service
        
        claim_id = context.get('claim_id')
        claim_number = context.get('claim_number')
        category_name = context.get('category_name')
        
        if not claim_id:
            await conversation_model.reset(chat_id)
            return "❌ Session expired. Type *appeal* to try again."
        
        # User wants to skip adding notes
        if text == 'skip':
            appeal_notes = None
        else:
            appeal_notes = message_text  # Use original text to preserve formatting
        
        try:
            # Appeal the claim with notes
            updated_claim = await claim_model.appeal(claim_id, employee['id'], appeal_notes)
            
            # Reset conversation
            await conversation_model.reset(chat_id)
            
            # Notify staff of appeal submission - REMOVED: reply_engine already sends detailed message
            # await notification_service.notify_staff_of_appeal_submitted(updated_claim)
            
            # Notify manager of appeal (with notes)
            await notification_service.notify_manager_of_appeal(updated_claim, appeal_notes)
            
            notes_msg = f"\n📝 *Your Note:* {appeal_notes[:100]}..." if appeal_notes and len(appeal_notes) > 100 else (f"\n📝 *Your Note:* {appeal_notes}" if appeal_notes else "")
            
            return f"""📤 *Appeal Submitted!*

📋 Claim #: *{claim_number}*
📁 Category: {category_name}{notes_msg}

Your claim has been sent for review again.
You will be notified of the decision.

Type "hi" or "menu" for more options."""
        except ValueError as e:
            await conversation_model.reset(chat_id)
            return f"❌ {str(e)}\nType \"hi\" for the main menu."
        except Exception as e:
            print(f"❌ Appeal error: {e}")
            await conversation_model.reset(chat_id)
            return "❌ Could not process appeal. Please try again or contact support."

    # ===== HANDLE RECEIPT/DOCUMENT UPLOADED =====
    if '[RECEIPT/DOCUMENT UPLOADED]' in message_text:
        # Extract info from the uploaded receipt
        extracted_match = re.search(r'Extracted text: ([\s\S]*?)(?:\nDetected amount|$)', message_text)
        extracted_text = extracted_match.group(1) if extracted_match else ''
        
        amount_match = re.search(r'Detected amount: Rs\.([0-9,]+(?:\.\d{2})?)', message_text)
        detected_amount = amount_match.group(1) if amount_match else None
        amount = float(detected_amount.replace(',', '')) if detected_amount else extract_amount(extracted_text)
        
        # Extract vendor if present
        vendor_match = re.search(r'Vendor: ([^\n]+)', extracted_text)
        vendor = vendor_match.group(1) if vendor_match else ''
        
        date_match = re.search(r'Date: ([^\n]+)', extracted_text)
        date_str = date_match.group(1) if date_match else ''
        
        # If user is in a category flow, use the receipt for that category
        current_step = state.get('current_step', 'initial')
        category = state.get('category')
        
        # If in receipt_upload step, DON'T process here - let the dedicated multi-receipt handler below handle it
        if current_step == 'receipt_upload':
            pass  # Fall through to the receipt_upload handler below
        elif category and current_step not in ('initial', 'menu'):
            await conversation_model.update(chat_id, {
                'current_step': 'confirm',
                'context': {
                    **context,
                    'receipt_vendor': vendor,
                    'receipt_date': date_str,
                    'user_amount': amount,
                    'details': extracted_text[:500],
                    'has_receipt': True,
                    'media_info': media_info  # Store media for forwarding to manager
                }
            })
            
            location_line = f"📍 Location: {context.get('location_name')}\n" if context.get('location_name') else ''
            
            return f"""📸 *Receipt Captured!*

📝 Vendor: {vendor or 'Unknown'}
📅 Date: {date_str or 'Unknown'}
💰 Amount: {format_currency(amount) if amount else 'Not detected'}

✅ *{category} Claim Summary*
👤 Employee: {employee['name']}
{location_line}
Type *confirm* to submit or *menu* to start over."""

        # If not in any flow (and not in receipt_upload), ask which category to use
        else:
            await conversation_model.update(chat_id, {
                'current_step': 'receipt_category',
                'context': {
                    'receipt_vendor': vendor,
                    'receipt_date': date_str,
                    'user_amount': amount,
                    'extracted_text': extracted_text[:500],
                    'has_receipt': True,
                    'media_info': media_info  # Store media for forwarding to manager
                }
            })
            
            return f"""📸 *Receipt Received!*

📝 Vendor: {vendor or 'Not detected'}
📅 Date: {date_str or 'Not detected'}
💰 Amount: {format_currency(amount) if amount else 'Not detected'}

Which category is this receipt for?
2️⃣ Fuel Expenses
3️⃣ Accommodation
4️⃣ Sundry Expenses

Reply with the number."""

    # Handle receipt category selection
    if state.get('current_step') == 'receipt_category':
        category = None
        category_name = ''
        
        if text == '2' or 'fuel' in text:
            category = 'FUEL'
            category_name = 'Fuel Expense'
        elif text == '3' or 'accommodation' in text or 'hotel' in text:
            category = 'ACCOM'
            category_name = 'Accommodation'
        elif text == '4' or 'sundry' in text or 'other' in text:
            category = 'SUNDRY'
            category_name = 'Sundry Expense'
        
        if not category:
            return """❌ *Invalid Selection*

Please select a valid category:

2️⃣ *Fuel Expenses*
3️⃣ *Accommodation*
4️⃣ *Sundry Expenses*

Reply with the number (2, 3, or 4)."""
        
        await conversation_model.update(chat_id, {
            'current_step': 'confirm',
            'category': category,
            'context': context
        })
        
        return f"""✅ *{category_name} Claim Summary*

👤 Employee: {employee['name']}
📝 Vendor: {context.get('receipt_vendor') or 'Unknown'}
📅 Date: {context.get('receipt_date') or 'Unknown'}
💰 Amount: {format_currency(context.get('user_amount')) if context.get('user_amount') else 'Not specified'}
🧾 Receipt: Attached

Type *confirm* to submit or *menu* to start over."""

    # Handle greetings - show main menu
    if text in ('hi', 'hello', 'hey', 'menu', 'start'):
        await conversation_model.update(chat_id, {
            'current_step': 'menu',
            'category': None,
            'context': {}
        })
        
        grade = employee.get('grade_code', 'N/A')
        location = employee.get('location_name', 'N/A')
        
        return f"""🙏 Welcome, *{employee['name']}*!

You are registered as Grade {grade} at {location}.

Please select a category:
1️⃣ Batta (Daily Allowance)
2️⃣ Fuel Expenses
3️⃣ Accommodation
4️⃣ Sundry Expenses

Reply with the number or category name."""

    # Handle category selection from menu
    current_step = state.get('current_step', 'initial')
    if current_step in ('menu', 'initial'):
        # Batta
        if text == '1' or 'batta' in text or 'daily' in text:
            locations = await rates_model.get_all_locations()
            location_list = '\n'.join(f"• {loc['name']}" for loc in locations)
            
            await conversation_model.update(chat_id, {
                'current_step': 'batta_location',
                'category': 'BATTA',
                'context': {}
            })
            
            return f"""📍 *Batta Claim*

Please enter the *location* for your travel:

{location_list}

Example: "Kandy" or "Colombo\""""

        # Fuel
        if text == '2' or 'fuel' in text or 'petrol' in text or 'diesel' in text:
            await conversation_model.update(chat_id, {
                'current_step': 'fuel_details',
                'category': 'FUEL',
                'context': {}
            })
            
            return """⛽ *Fuel Expense*

Please provide the details:
• Vehicle number
• Amount (Rs.)
• Purpose/trip

Example: "CAB-1234, Rs.5000, Field visit to Kandy\""""

        # Accommodation
        if text == '3' or 'accommodation' in text or 'hotel' in text or 'stay' in text:
            await conversation_model.update(chat_id, {
                'current_step': 'accommodation_details',
                'category': 'ACCOM',
                'context': {}
            })
            
            return """🏨 *Accommodation Claim*

Please provide:
• Hotel/place name
• Location
• Number of nights
• Amount

Example: "Grand Hotel, Galle, 2 nights, Rs.6000\""""

        # Sundry
        if text == '4' or 'sundry' in text or 'other' in text or 'misc' in text:
            await conversation_model.update(chat_id, {
                'current_step': 'sundry_details',
                'category': 'SUNDRY',
                'context': {}
            })
            
            return """📦 *Sundry Expenses*

Please describe:
• What was purchased
• Amount
• Purpose

Example: "Stationery supplies, Rs.1500, Office use\""""

    # ===== BATTA FLOW =====
    if current_step == 'batta_location':
        location = await find_location_in_text(text)
        
        if not location:
            return """❌ Location not recognized. Please enter a valid location:

Example: "Colombo", "Kandy", "Galle", etc."""

        # Get batta rate for this employee's grade and selected location
        rate = await rates_model.get_batta_rate(employee['grade_id'], location['id'])
        
        if not rate:
            return f"⚠️ No batta rate found for Grade {employee.get('grade_code')} at {location['name']}. Please contact admin."

        await conversation_model.update(chat_id, {
            'current_step': 'batta_days',
            'context': {
                'location_id': location['id'],
                'location_name': location['name'],
                'rate_per_day': rate
            }
        })

        return f"""📍 Location: *{location['name']}*
💰 Rate: *{format_currency(rate)}/day* (Grade {employee.get('grade_code')})

How many days?"""

    if current_step == 'batta_days':
        days = extract_days(text)
        if not days:
            try:
                days = int(text.strip())
            except ValueError:
                days = 0
        
        if not days or days < 1 or days > 30:
            return "❌ Please enter a valid number of days (1-30)."

        rate_per_day = context.get('rate_per_day', 0)
        total_amount = rate_per_day * days

        await conversation_model.update(chat_id, {
            'current_step': 'receipt_upload',
            'context': {
                **context,
                'days': days,
                'total_amount': total_amount
            }
        })

        return f"""✅ *Batta Claim Details*

👤 Employee: {employee['name']}
📍 Location: {context.get('location_name')}
🗓️ Days: {days}
💰 Rate: {format_currency(rate_per_day)}/day
💵 *Total: {format_currency(total_amount)}*

📎 Please upload your receipt/supporting document (image or PDF).
Or type *skip* if you don't have one."""

    # ===== FUEL FLOW =====
    if current_step == 'fuel_details':
        amount = extract_amount(text)
        
        await conversation_model.update(chat_id, {
            'current_step': 'receipt_upload',
            'context': {
                'details': message_text,
                'user_amount': amount
            }
        })

        amount_line = f"\n💵 Amount: {format_currency(amount)}" if amount else ''

        return f"""✅ *Fuel Expense Details*

👤 Employee: {employee['name']}
📝 Details: {message_text}{amount_line}

📎 Please upload your fuel receipt (image or PDF).
Or type *skip* if you don't have one."""

    # ===== ACCOMMODATION FLOW =====
    if current_step == 'accommodation_details':
        amount = extract_amount(text)
        location = await find_location_in_text(text)
        
        await conversation_model.update(chat_id, {
            'current_step': 'receipt_upload',
            'context': {
                'details': message_text,
                'user_amount': amount,
                'location_id': location['id'] if location else None,
                'location_name': location['name'] if location else None
            }
        })

        amount_line = f"\n💵 Amount: {format_currency(amount)}" if amount else ''

        return f"""✅ *Accommodation Claim Details*

👤 Employee: {employee['name']}
📝 Details: {message_text}{amount_line}

📎 Please upload your hotel bill/invoice (image or PDF).
Or type *skip* if you don't have one."""

    # ===== SUNDRY FLOW =====
    if current_step == 'sundry_details':
        amount = extract_amount(text)
        
        await conversation_model.update(chat_id, {
            'current_step': 'receipt_upload',
            'context': {
                'details': message_text,
                'user_amount': amount
            }
        })

        amount_line = f"\n💵 Amount: {format_currency(amount)}" if amount else ''

        return f"""✅ *Sundry Expense Details*

👤 Employee: {employee['name']}
📝 Details: {message_text}{amount_line}

📎 Please upload receipt #1 (image or PDF).

Or type:
• *done* - if you've finished uploading
• *skip* - to continue without receipts"""

    # ===== RECEIPT UPLOAD (Modified for Multi-Receipt Support) =====
    if current_step == 'receipt_upload':
        # Handle 'done' command - user has finished uploading receipts
        if text in ('done', 'finish', 'complete'):
            receipts = context.get('receipts', [])
            
            # Require at least one receipt for most categories (except maybe BATTA)
            if not receipts and state.get('category') != 'BATTA':
                return """⚠️ Please upload at least one receipt or type *skip* to continue without receipts."""
            
            # Calculate total from all receipts
            receipt_total = sum(r.get('ocr_amount', 0) for r in receipts)
            user_amount = context.get('total_amount') or context.get('user_amount') or 0
            
            # Update state to confirmation
            await conversation_model.update(chat_id, {
                'current_step': 'confirm',
                'context': context
            })
            
            # Build summary with all receipts
            category_code = state.get('category')
            summary = f"""✅ *Claim Summary*

👤 Employee: {employee['name']}
📁 Category: {category_code}
📝 Details: {context.get('details', 'N/A')}"""
            
            if context.get('location_name'):
                summary += f"\n📍 Location: {context['location_name']}"
            if context.get('days'):
                summary += f"\n🗓️ Days: {context['days']}"
            
            # Show amount
            if user_amount:
                summary += f"\n💵 Amount: {format_currency(user_amount)}"
            
            # Show receipts summary
            if receipts:
                summary += f"\n\n📎 *Receipts ({len(receipts)}):*"
                for i, receipt in enumerate(receipts, 1):
                    amount = receipt.get('ocr_amount', 0)
                    vendor = receipt.get('vendor', 'Unknown')
                    summary += f"\n  {i}. Rs. {amount:,.0f} - {vendor}"
                
                if receipt_total > 0:
                    summary += f"\n\n🧮 *Total from receipts:* Rs. {receipt_total:,.0f}"
                    
                    # Validate if differs significantly from user amount
                    if user_amount > 0:
                        diff = abs(receipt_total - user_amount)
                        diff_pct = (diff / user_amount) * 100
                        
                        if diff_pct > 5:  # More than 5% difference
                            summary += f"\n⚠️ *Difference:* Rs. {diff:,.0f} ({diff_pct:.1f}%)"
            else:
                summary += "\n🧾 Receipt: ⏭️ Skipped"
            
            summary += "\n\nType *confirm* to submit or *menu* to start over."
            return summary
        
        # Handle 'skip' - skip all receipts
        if text in ('skip', 'no', 'none'):
            await conversation_model.update(chat_id, {
                'current_step': 'confirm',
                'context': context
            })
            
            category_code = state.get('category')
            summary = f"""✅ *Claim Summary*

👤 Employee: {employee['name']}
📁 Category: {category_code}
📝 Details: {context.get('details', 'N/A')}"""
            
            display_amount = context.get('total_amount') or context.get('user_amount')
            if display_amount:
                summary += f"\n💵 Amount: {format_currency(display_amount)}"
            
            summary += "\n🧾 Receipt: ⏭️ Skipped"
            summary += "\n\nType *confirm* to submit or *menu* to start over."
            return summary
        
        # Handle receipt upload
        if media_info:
            # Initialize receipts array if not exists
            receipts = context.get('receipts', [])
            receipt_num = len(receipts) + 1
            
            # Extract receipt data from message_text
            extracted_amount = None
            extracted_vendor = None
            extracted_date = None
            
            if '[RECEIPT/DOCUMENT UPLOADED]' in message_text:
                print(f"🔍 DEBUG receipt_upload: Parsing receipt data from message_text")
                
                # Extract vendor
                if 'Vendor:' in message_text:
                    vendor_part = message_text.split('Vendor:', 1)[1]
                    extracted_vendor = vendor_part.split('\n')[0].strip()
                    print(f"🏪 Extracted vendor: {extracted_vendor}")
                
                # Extract amount
                if 'Detected amount: Rs.' in message_text:
                    amount_str = message_text.split('Detected amount: Rs.', 1)[1].split('\n')[0].strip()
                    try:
                        extracted_amount = float(amount_str.replace(',', ''))
                        print(f"💰 Extracted amount: Rs.{extracted_amount}")
                    except Exception as e:
                        print(f"❌ Error parsing amount: {e}")
                
                # Extract date
                if 'Date:' in message_text:
                    date_part = message_text.split('Date:', 1)[1]
                    extracted_date = date_part.split('\n')[0].strip()
                    print(f"📅 Extracted date: {extracted_date}")
            
            # Create receipt obj object
            new_receipt = {
                'file_path': media_info.get('saved_filename'),
                'file_name': media_info.get('saved_filename'),
                'ocr_amount': extracted_amount or 0,
                'vendor': extracted_vendor or 'Unknown',
                'date': extracted_date,
                'message_id': media_info.get('message_id'),
                'file_size': media_info.get('file_size'),
                'mimetype': media_info.get('mimetype')
            }
            
            # Add to receipts array
            receipts.append(new_receipt)
            context['receipts'] = receipts
            
            # Calculate running total
            receipt_total = sum(r.get('ocr_amount', 0) for r in receipts)
            user_amount = context.get('total_amount') or context.get('user_amount') or 0
            
            # Update context
            await conversation_model.update(chat_id, {
                'current_step': 'receipt_upload',
                'context': context
            })
            
            # Build response
            response = f"""✅ *Receipt #{receipt_num} Saved*"""
            
            if extracted_amount:
                response += f"\n💰 Amount: Rs. {extracted_amount:,.0f}"
            if extracted_vendor:
                response += f"\n🏪 Vendor: {extracted_vendor}"
            
            # Show running total
            if user_amount > 0:
                response += f"\n\n🧮 *Running Total:* Rs. {receipt_total:,.0f} / Rs. {user_amount:,.0f}"
                
                # Check if close to target
                if abs(receipt_total - user_amount) < 1:
                    response += " ✅"
                elif receipt_total > user_amount:
                    response += f" ⚠️ (Over by Rs. {receipt_total - user_amount:,.0f})"
            
            response += f"\n\n📎 Upload receipt #{receipt_num + 1} or type *done* to finish"
            return response
        
        # If no media and not done/skip, remind user
        receipts = context.get('receipts', [])
        receipt_num = len(receipts) + 1
        return f"""📎 Please upload receipt #{receipt_num} (image or PDF).

Or type:
• *done* - if you've finished uploading
• *skip* - to continue without receipts"""

    # ===== CONFIRMATION =====
    if current_step == 'confirm':
        if text in ('confirm', 'yes', 'submit'):
            try:
                # Get category ID
                category_code = state.get('category')
                category = await rates_model.find_category(category_code)
                if not category:
                    return '❌ Error: Category not found. Type "menu" to start over.'

                # Create claim in database
                claim = await claim_model.create({
                    'employee_id': employee['id'],
                    'category_id': category['id'],
                    'location_id': context.get('location_id') or employee.get('location_id'),
                    'claim_type': 'outright' if category_code == 'BATTA' else 'bill',
                    'duration_days': context.get('days', 1),
                    'user_amount': context.get('user_amount'),
                    'system_amount': context.get('total_amount') or context.get('user_amount'),
                    'description': context.get('details') or f'{category_code} claim',
                    'manager_id': employee.get('manager_id')
                })


                # Save ALL receipts to database (supports multi-receipt)
                receipts = context.get('receipts', [])
                media_info_list = []  # For manager notification
                
                if receipts:
                    print(f"💾 Saving {len(receipts)} receipt(s) to database for claim {claim['id']}")
                    for i, receipt in enumerate(receipts, 1):
                        try:
                            await claim_model.add_receipt(
                                claim_id=claim['id'],
                                file_path=receipt.get('file_path'),
                                file_name=receipt.get('file_name'),
                                file_type=receipt.get('mimetype'),
                                file_size=receipt.get('file_size'),
                                ocr_amount=receipt.get('ocr_amount'),
                                ocr_raw_text=None,  # Not storing full OCR text for now
                                message_id=receipt.get('message_id')
                            )
                            print(f"✅ Receipt #{i} saved to database")
                            
                            # Build media_info for manager notification
                            media_info_list.append({
                                'saved_filename': receipt.get('file_path'),
                                'message_id': receipt.get('message_id'),
                                'mimetype': receipt.get('mimetype')
                            })
                        except Exception as receipt_error:
                            print(f"⚠️ Failed to save receipt #{i}: {receipt_error}")
                else:
                    # Backwards compatibility: Check for old single-receipt format
                    stored_media_info = context.get('media_info')
                    if stored_media_info and stored_media_info.get('saved_filename'):
                        try:
                            print(f"💾 Saving single receipt (legacy) to database for claim {claim['id']}")
                            await claim_model.add_receipt(
                                claim_id=claim['id'],
                                file_path=stored_media_info.get('saved_filename'),
                               file_name=stored_media_info.get('saved_filename'),
                                file_type=stored_media_info.get('mimetype'),
                                file_size=stored_media_info.get('saved_file_size'),
                                ocr_amount=stored_media_info.get('extracted_amount'),
                                ocr_raw_text=stored_media_info.get('ocr_text'),
                                message_id=stored_media_info.get('message_id')
                            )
                            media_info_list.append(stored_media_info)
                            print(f"✅ Receipt saved to database successfully")
                        except Exception as receipt_error:
                            print(f"⚠️ Failed to save receipt to database: {receipt_error}")
                
                
                # Notify manager with claim details and receipt
                print(f"🔍 DEBUG: employee.manager_id={employee.get('manager_id')}, manager_name={employee.get('manager_name')}")
                if employee.get('manager_id'):
                    print(f"📤 Sending notification to manager ID: {employee.get('manager_id')}")
                    await notification_service.notify_manager_of_new_claim(claim, media_info_list)
                else:
                    print(f"⚠️ No manager assigned to employee {employee['name']} - skipping manager notification")

                # Reset conversation
                await conversation_model.reset(chat_id)

                # Manager notice
                manager_notice = ''
                if employee.get('manager_name'):
                    manager_notice = f"\n\n📤 Sent to *{employee['manager_name']}* for approval."

                final_amount = claim.get('system_amount') or claim.get('user_amount') or 0

                return f"""🎉 *Claim Submitted Successfully!*

📋 Claim #: *{claim['claim_number']}*
📁 Category: {category['name']}
💵 Amount: {format_currency(final_amount)}{manager_notice}

Type "menu" to submit another claim."""

            except Exception as e:
                print(f'❌ Error creating claim: {e}')
                return '❌ Error saving claim. Please try again or contact admin.'

    # Handle cancel/reset
    if text in ('cancel', 'reset', 'exit'):
        await conversation_model.reset(chat_id)
        return '❌ Cancelled. Type "hi" or "menu" to start again.'

    # Default response
    return """🤔 I didn't understand that.

Type "hi" or "menu" to see available options, or select:
1️⃣ Batta | 2️⃣ Fuel | 3️⃣ Accommodation | 4️⃣ Sundry"""
