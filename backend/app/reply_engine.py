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
from app.models import category as category_model
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
    return int(match.group(1)) if match else 0


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


# Number emoji mapping for dynamic menus
NUMBER_EMOJIS = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']


async def get_categories_for_employee(employee: dict) -> list:
    """Get categories available for an employee based on their unit"""
    unit_id = employee.get('unit_id')
    if unit_id:
        categories = await category_model.find_by_unit(unit_id)
        if categories:
            return categories
    # Fallback to global categories if unit has none
    return await category_model.find_all()


def generate_category_menu(categories: list) -> str:
    """Generate a formatted category menu string"""
    if not categories:
        return "No categories available. Please contact admin."
    
    menu_lines = []
    for i, cat in enumerate(categories):
        emoji = NUMBER_EMOJIS[i] if i < len(NUMBER_EMOJIS) else f"{i+1}."
        menu_lines.append(f"{emoji} {cat['name']}")
    
    return '\n'.join(menu_lines)


def match_category_from_input(text: str, categories: list) -> dict | None:
    """Match user input to a category from the list"""
    if not categories:
        return None
    
    text_lower = text.lower().strip()
    
    # Try to match by number (1, 2, 3...)
    try:
        num = int(text_lower)
        if 1 <= num <= len(categories):
            return categories[num - 1]
    except ValueError:
        pass
    
    # Try to match by name or code (partial match)
    for cat in categories:
        cat_name_lower = cat['name'].lower()
        cat_code_lower = cat['code'].lower()
        if cat_name_lower in text_lower or text_lower in cat_name_lower:
            return cat
        if cat_code_lower in text_lower or text_lower in cat_code_lower:
            return cat
    
    return None



async def process_message(chat_id: str, message: str, employee_id: int = None, media_info: dict = None) -> Optional[str]:
    """
    Wrapper for generate_reply to match webhooks call signature.
    Acts as the public entry point for the reply engine.
    """
    return await generate_reply(message_text=message, chat_id=chat_id, media_info=media_info, employee_id=employee_id)


async def generate_reply(message_text: str, chat_id: str, media_info: dict = None, employee_id: int = None) -> Optional[str]:
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

    # 2. Identify Employee
    employee = None
    phone_number = None

    # If employee_id provided (trusted from webhook), fetch directly
    if employee_id:
        employee = await employee_model.find_by_id(employee_id)
        if employee:
             # Just ensures we have phone number for logic consistency if needed
             phone_number = employee.get('phone_number')

    # If not found via ID, try to extract from Chat ID
    if not employee:
        # Extract phone number from chat ID
        
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
    # Clean text: remove emojis and extra whitespace for command matching
    clean_text = re.sub(r'[^\w\s#-]', '', text).strip()
    
    # Approve command: flexible matching - "approve 123", "✅ Approve 12", "Approve #12", etc.
    approve_match = re.search(r'\bapprove\s*#?(\d+)\b', clean_text, re.IGNORECASE)
    if approve_match:
        claim_id = int(approve_match.group(1))
        try:
            # Find the claim
            claim = await claim_model.find_by_id(claim_id)
            if not claim:
                return f"❌ Claim #{claim_id} not found."
            
            # Check status
            current_status = claim.get('status_code')
            if current_status not in ('PENDING', 'APPEALED'):
                return f"❌ Claim #{claim_id} is already {claim.get('status_name')}."

            workflow_result = await claim_model.approve_step(claim_id, employee['id'])
            updated_claim = workflow_result.get("claim") or claim

            if workflow_result.get("is_final"):
                await claim_model.record_status_change(
                    claim_id, current_status, 'APPROVED', employee['id'], 'Approved via WhatsApp'
                )
                await notification_service.notify_staff_of_approval(updated_claim)
                return f"""✅ *Claim Approved!*

📋 Claim #: *{claim['claim_number']}*
👤 Staff: {claim.get('employee_name', 'N/A')}
💵 Amount: {format_currency(claim.get('user_amount') or claim.get('system_amount') or 0)}

The employee has been notified."""
            
            await claim_model.record_status_change(
                claim_id, current_status, current_status, employee['id'], 'Step approved via WhatsApp'
            )
            # Notify the claimant about the step approval
            approved_step = workflow_result.get("approved_step", 1)
            next_assignee_id = workflow_result.get("next_assignee_id")
            await notification_service.notify_staff_of_step_approval(
                updated_claim, 
                employee.get('name', 'Approver'), 
                approved_step,
                next_assignee_id
            )
            # Notify the next approver
            await notification_service.notify_next_approver_of_claim(updated_claim)
            return f"""✅ *Step Approved*

📋 Claim #: *{claim['claim_number']}*
➡️ Routed to next approver."""
        except PermissionError as e:
            return f"❌ {str(e)}"
        except Exception as e:
            print(f"❌ Error approving claim via WhatsApp: {e}")
            return f"❌ Error approving claim. Please try again."
    
    # Reject command: flexible matching - "reject 123 reason", "❌ Reject #12 Invalid", etc.
    reject_match = re.search(r'\breject\s*#?(\d+)(?:\s+(.+))?', clean_text, re.IGNORECASE)
    if reject_match:
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
            
            # Check status
            current_status = claim.get('status_code')
            if current_status not in ('PENDING', 'APPEALED'):
                return f"❌ Claim #{claim_id} is already {claim.get('status_name')}."
            result = await claim_model.reject_step(claim_id, employee['id'], reason)
            updated_claim = result.get("claim") or claim
            await claim_model.record_status_change(
                claim_id, current_status, 'REJECTED', employee['id'], reason
            )
            
            is_final = result.get("is_final")
            if is_final:
                await notification_service.notify_staff_of_rejection(updated_claim, reason)
            else:
                rejected_step = result.get("approved_step", 1) # reusing identical logic
                await notification_service.notify_staff_of_step_rejection(updated_claim, employee.get('name', 'Approver'), rejected_step, reason)
                
            
            return f"""❌ *Claim Rejected*

📋 Claim #: *{claim['claim_number']}*
👤 Staff: {claim.get('employee_name', 'N/A')}
📝 Reason: {reason}

The employee has been notified and can appeal."""
        except PermissionError as e:
            return f"❌ {str(e)}"
        except Exception as e:
            print(f"❌ Error rejecting claim via WhatsApp: {e}")
            return f"❌ Error rejecting claim. Please try again."
    



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
        # Exclude advance flow steps - they have their own handler
        elif current_step in ('advance_category_select', 'advance_amount', 'advance_description', 'advance_quotation', 'advance_confirm'):
            pass  # Fall through to advance flow handler
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
            # Get categories for this employee
            categories = await get_categories_for_employee(employee)
            category_menu = generate_category_menu(categories)
            
            await conversation_model.update(chat_id, {
                'current_step': 'receipt_category',
                'context': {
                    'receipt_vendor': vendor,
                    'receipt_date': date_str,
                    'user_amount': amount,
                    'extracted_text': extracted_text[:500],
                    'has_receipt': True,
                    'media_info': media_info,  # Store media for forwarding to manager
                    'available_categories': [cat['id'] for cat in categories]
                }
            })
            
            return f"""📸 *Receipt Received!*

📝 Vendor: {vendor or 'Not detected'}
📅 Date: {date_str or 'Not detected'}
💰 Amount: {format_currency(amount) if amount else 'Not detected'}

Which category is this receipt for?
{category_menu}

Reply with the number."""

    # Handle receipt category selection
    if state.get('current_step') == 'receipt_category':
        # Get available categories from context or fetch fresh
        available_ids = context.get('available_categories')
        all_categories = []
        
        if available_ids:
            all_categories = await get_categories_for_employee(employee)
        else:
            all_categories = await get_categories_for_employee(employee)
            
        selected_cat = match_category_from_input(text, all_categories)
        
        if not selected_cat:
            return """❌ *Invalid Selection*

Please select a valid category number or name."""
        
        category = selected_cat['code'] # Use dynamic code
        category_name = selected_cat['name']
        
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

    # ===== HANDLE GREETINGS - SHOW MAIN MENU =====
    if text in ('hi', 'hello', 'hey', 'menu', 'start'):
        # Reset conversation to ensure clean state
        await conversation_model.update(chat_id, {
            'current_step': 'choose_flow',
            'category': None,
            'context': {}
        })
        
        return f"""👋 Welcome, *{employee['name']}*!

Please select an option:

1️⃣ Reimbursement (After Pay)
2️⃣ Advance Request (Before Pay)

Reply with *1* or *2*."""

    # ===== HANDLE FLOW SELECTION =====
    current_step = state.get('current_step')
    
    if current_step == 'choose_flow':
        if text == '1' or 'reimburse' in text:
            # OPTION 1: REIMBURSEMENT (Existing Flow)
            # Get categories for this employee's unit
            categories = await get_categories_for_employee(employee)
            category_menu = generate_category_menu(categories)
            
            await conversation_model.update(chat_id, {
                'current_step': 'menu',
                'context': {'available_categories': [cat['id'] for cat in categories], 'claim_intent': 'reimbursement'}
            })
            
            return f"""🔄 *Reimbursement Request*

Please select a category:
{category_menu}

Reply with the number or category name."""
            
        elif text == '2' or 'advance' in text or 'before' in text:
            # OPTION 2: ADVANCE REQUEST (New Flow)
            # Get categories for this employee's unit
            categories = await get_categories_for_employee(employee)
            category_menu = generate_category_menu(categories)
            
            await conversation_model.update(chat_id, {
                'current_step': 'advance_category_select',
                'category': 'ADVANCE', # Marker
                'context': {
                    'claim_intent': 'advance',
                    'available_categories': [cat['id'] for cat in categories]
                }
            })
            
            return f"""💰 *Advance Request*

Please select a category for this advance:
{category_menu}

Reply with the number or category name."""
        
        else:
             return """❌ Invalid selection. Please reply with *1* for Reimbursement or *2* for Advance."""

    # ===== ADVANCE FLOW STEPS =====
    
    # Step 0: Advance Category Selection
    if current_step == 'advance_category_select':
        # Get available categories from context or fetch fresh
        available_ids = context.get('available_categories')
        all_categories = []
        
        if available_ids:
            all_categories = await get_categories_for_employee(employee)
        else:
            all_categories = await get_categories_for_employee(employee)
            
        selected_cat = match_category_from_input(text, all_categories)
        
        if not selected_cat:
            return """❌ Invalid selection. Please reply with the *number* or *name* of the category."""
            
        # Store selected category
        context.update({
            'category_id': selected_cat['id'],
            'category_name': selected_cat['name']
        })
        
        await conversation_model.update(chat_id, {
            'current_step': 'advance_amount',
            'context': context
        })
        
        return f"""✅ Selected: *{selected_cat['name']}*

💰 Please enter the *amount* you need:

Example: "Rs. 5000" or just "5000"."""


    # Step 1: Advance Amount
    if current_step == 'advance_amount':
        amount = extract_amount(text)
        if not amount:
             # Try simple number parsing
             try:
                 clean_text = re.sub(r'[^\d.]', '', text)
                 amount = float(clean_text)
             except:
                 pass
        
        if not amount or amount <= 0:
            return """❌ Please enter a valid amount.
            
Example: "5000" or "Rs. 5000"."""
            
        context.update({
            'user_amount': amount,
            'total_amount': amount # System amount matches user amount initially
        })
        
        await conversation_model.update(chat_id, {
            'current_step': 'advance_description',
            'context': context
        })
        
        return f"""💰 Amount: *{format_currency(amount)}*

📝 What is this advance for?
Please provide a brief description."""

    # Step 2: Advance Description
    if current_step == 'advance_description':
        description = message_text.strip()
        if len(description) < 3:
            return "❌ Please provide a valid description (at least 3 characters)."
            
        context.update({
            'details': description
        })
        
        await conversation_model.update(chat_id, {
            'current_step': 'advance_quotation',
            'context': context
        })
        
        return f"""📝 Description: "{description}"

📎 *Upload Quotation (Optional)*

Please upload a Quotation/Invoice image if you have one.
The system will analyze it. You can upload multiple quotations.

Type *skip* to proceed without quotations."""

    # Step 3: Advance Quotation (Optional - Multi-upload)
    if current_step == 'advance_quotation':
        # Handle 'skip' - only on first upload
        receipts = context.get('receipts', [])
        if text in ('skip', 'no', 'none') and len(receipts) == 0:
            await conversation_model.update(chat_id, {
                'current_step': 'advance_confirm',
                'context': context
            })
            
            return _generate_advance_summary(employee, context)
        
        # Handle 'done' - finish uploading
        if text in ('done', 'finish', 'next', 'confirm'):
            if len(receipts) > 0:
                await conversation_model.update(chat_id, {
                    'current_step': 'advance_confirm',
                    'context': context
                })
                return _generate_advance_summary(employee, context)
            else:
                return """⚠️ No quotations uploaded yet. Upload at least one or type *skip*."""

        # Handle Upload
        if media_info or '[RECEIPT/DOCUMENT UPLOADED]' in message_text:
             # If media was uploaded, webhooks.py already processed it partially
             # We just need to link it and maybe update amount if detected
             
             # Extract extraction info if available from text (injected by webhook)
             extracted_amount = None
             extracted_vendor = None
             if '[RECEIPT/DOCUMENT UPLOADED]' in message_text:
                 if 'Detected amount:' in message_text:
                    amount_part = message_text.split('Detected amount:', 1)[1]
                    amount_match = re.search(r'Rs\.?\s*([\d,\.]+)', amount_part)
                    if amount_match:
                         try:
                             extracted_amount = float(amount_match.group(1).replace(',', ''))
                         except: pass
                 
                 if 'Vendor:' in message_text:
                    vendor_part = message_text.split('Vendor:', 1)[1]
                    vendor_match = re.search(r'Vendor:\s*([^\n]+)', message_text)
                    if vendor_match:
                        extracted_vendor = vendor_match.group(1).strip()

             # Save the file info
             receipt_entry = {
                'file_path': media_info.get('saved_filename'),
                'file_name': media_info.get('saved_filename'),
                'ocr_amount': extracted_amount or 0,
                'vendor': extracted_vendor,
                'file_type': media_info.get('mimetype'),
                'message_id': media_info.get('message_id'),
                'file_hash': media_info.get('file_hash')
             }
             
             # Save to list of receipts (quotations)
             receipts.append(receipt_entry)
             context['receipts'] = receipts
             context['has_quotation'] = True
             
             await conversation_model.update(chat_id, {
                'current_step': 'advance_quotation',  # Stay in same step for more uploads
                'context': context
             })
             
             # Show confirmation and prompt for more - match receipt upload style
             quotation_count = len(receipts)
             
             # Calculate running total
             total_from_quotations = sum(float(r.get('ocr_amount', 0) or 0) for r in receipts)
             requested_amount = context.get('user_amount', 0)
             
             # Build attractive message
             vendor_line = f"🏪 Vendor: {extracted_vendor}" if extracted_vendor else ""
             amount_line = f"💰 Amount: Rs. {extracted_amount:,.0f}" if extracted_amount else "💰 Amount: Not detected"
             
             message = f"""✅ *Quotation #{quotation_count} Saved*
{amount_line}
{vendor_line}

🧮 *Running Total:* Rs. {total_from_quotations:,.0f} / Rs. {requested_amount:,.0f}

📎 Upload quotation #{quotation_count + 1} or type *done* to finish"""
             
             return message
        
        return """📎 Please upload an image/document, type *done* to finish, or *skip* to proceed without quotations."""


    # Step 4: Advance Confirm
    if current_step == 'advance_confirm':
        if text in ('confirm', 'yes', 'submit', 'ok'):
            try:
                # Create the claim
                claim = await claim_model.create({
                    'employee_id': employee['id'],
                    'category_id': context.get('category_id') or await _get_advance_category_id(), 
                    'location_id': employee.get('location_id'),
                    'claim_type': 'advance',
                    'duration_days': 1,
                    'user_amount': context.get('user_amount'),
                    'system_amount': context.get('user_amount'), # Use user amount as system amount for advances typically
                    'description': context.get('details'),
                    'manager_id': employee.get('manager_id')
                })
                # Initialize multi-step approval workflow for WhatsApp-created claims.
                await claim_model.initialize_approval_workflow(claim['id'])
                
                # Save quotations (as receipts)
                receipts = context.get('receipts', [])
                media_info_list = []
                
                for r in receipts:
                    # Check for duplicates using file_hash
                    file_hash = r.get('file_hash')
                    if file_hash:
                        duplicate = await claim_model.check_duplicate_receipt(file_hash, current_claim_id=claim['id'])
                        if duplicate:
                            print(f"⚠️ Duplicate receipt detected! Used in claim #{duplicate.get('claim_number')}")
                            r['warning'] = {
                                'type': 'duplicate',
                                'message': f"Potential duplicate: Used in Claim #{duplicate.get('claim_number')} by {duplicate.get('employee_name')} on {duplicate.get('created_at').strftime('%Y-%m-%d') if duplicate.get('created_at') else 'unknown date'}",
                                'original_claim': duplicate
                            }
                    
                    await claim_model.add_receipt(
                        claim_id=claim['id'],
                        file_path=r.get('file_path'),
                        file_name=r.get('file_name'),
                        file_type=r.get('file_type'),
                        ocr_amount=r.get('ocr_amount', 0),
                        message_id=r.get('message_id'),
                        vendor=r.get('vendor'),
                        file_hash=file_hash
                    )
                    media_info_list.append({
                         'saved_filename': r.get('file_path'),
                         'mimetype': r.get('file_type'),
                         'warning': r.get('warning')
                    })
                
                # Recalculate system amount from saved receipts
                if receipts:
                    await claim_model.calculate_system_amount(claim['id'])

                # Notifications: direct manager first, approval policy fallback.
                from app.services import notification_service
                duplicate_warnings = [item['warning'] for item in media_info_list if item.get('warning')]
                if employee.get('manager_id'):
                    await notification_service.notify_manager_of_new_claim(
                        claim,
                        media_info_list,
                        duplicate_warnings=duplicate_warnings,
                    )
                else:
                    routed = await notification_service.notify_next_approver_of_claim(
                        claim, duplicate_warnings=duplicate_warnings
                    )
                    if not routed:
                        print(f"⚠️ No manager or approval policy approver for {employee['name']}")
                
                await conversation_model.reset(chat_id)
                
                return f"""🎉 *Advance Request Submitted!*

📋 Ref: *{claim['claim_number']}*
💵 Amount: {format_currency(claim.get('user_amount'))}
⏳ Status: Pending Approval

Type "menu" to start over."""
            
            except Exception as e:
                print(f"❌ Error creating advance: {e}")
                return "❌ Error submitting request. Please try again."
                
        elif text in ('cancel', 'no'):
            await conversation_model.reset(chat_id)
            return "❌ Request cancelled."
            
        else:
             return "Type *confirm* to submit or *cancel*."


    # ===== HANDLING EXISTING FLOWS (Reimbursement) =====
    
    # Handle category selection from menu (ONLY if Step is 'menu' now)
    if current_step == 'menu': # Changed from 'in' to '==' to be strict
        # Get available categories from context or fetch fresh
        available_ids = context.get('available_categories')
        all_categories = []
        
        if available_ids:
            # We have IDs in context (optimized), but we need full objects for matching
            # So we just fetch for employee again as it's safer and fast enough
            all_categories = await get_categories_for_employee(employee)
        else:
            all_categories = await get_categories_for_employee(employee)
            
        # Match input to category
        selected_cat = match_category_from_input(text, all_categories)
        
        if selected_cat:
            cat_code = selected_cat['code']
            
            # Map old hardcoded codes to new DB codes if needed, or use DB codes directly
            # We assume DB codes will be: BATTA, FUEL, ACCOM, SUNDRY (or similar)
            
            # Check for custom prompt from DB
            custom_prompt = selected_cat.get('prompt_message')
            
            # ===== BATTA FLOW =====
            if 'BATTA' in cat_code or 'DAILY' in cat_code:
                locations = await rates_model.get_all_locations()
                location_list = '\n'.join(f"• {loc['name']}" for loc in locations)
                
                await conversation_model.update(chat_id, {
                    'current_step': 'batta_location',
                    'category': 'BATTA',
                    'context': {'category_id': selected_cat['id']}
                })
                
                if custom_prompt:
                    return custom_prompt
                
                return f"""📍 *{selected_cat['name']}*

Please enter the *location* for your travel:

{location_list}

Example: "Kandy" or "Colombo\""""

            # ===== FUEL FLOW =====
            elif 'FUEL' in cat_code or 'PETROL' in cat_code:
                await conversation_model.update(chat_id, {
                    'current_step': 'fuel_details',
                    'category': 'FUEL',
                    'context': {'category_id': selected_cat['id']}
                })
                
                if custom_prompt:
                    return custom_prompt
                
                return f"""⛽ *{selected_cat['name']}*

Please provide the details:
• Vehicle number
• Amount (Rs.)
• Purpose/trip

Example: "CAB-1234, Rs.5000, Field visit to Kandy\""""

            # ===== ACCOMMODATION FLOW =====
            elif 'ACCOM' in cat_code or 'HOTEL' in cat_code:
                await conversation_model.update(chat_id, {
                    'current_step': 'accommodation_details',
                    'category': 'ACCOM',
                    'context': {'category_id': selected_cat['id']}
                })
                
                if custom_prompt:
                    return custom_prompt
                
                return f"""🏨 *{selected_cat['name']}*

Please provide:
• Hotel/place name
• Location
• Number of nights
• Amount

Example: "Grand Hotel, Galle, 2 nights, Rs.6000\""""

            # ===== SUNDRY/GENERAL FLOW (Default) =====
            else:
                # Default flow for any other category (Sundry etc.)
                await conversation_model.update(chat_id, {
                    'current_step': 'sundry_details',
                    'category': cat_code, # Use the dynamic code
                    'context': {'category_id': selected_cat['id']}
                })
                
                if custom_prompt:
                    return custom_prompt
                    
                cat_name = selected_cat['name']
                return f"📦 *{cat_name}*\n\nPlease describe:\n• What was purchased\n• Amount\n• Purpose\n\nExample: 'Stationery supplies, Rs.1500, Office use'"
        # If no match found
        if current_step == 'menu':
             return """❌ Invalid selection. Please reply with the *number* or *name* of the category."""


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

        context.update({
            'location_id': location['id'],
            'location_name': location['name'],
            'rate_per_day': rate
        })
        
        await conversation_model.update(chat_id, {
            'current_step': 'batta_days',
            'context': context
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

        context.update({
            'days': days,
            'total_amount': total_amount
        })

        await conversation_model.update(chat_id, {
            'current_step': 'receipt_upload',
            'context': context
        })

        return f"""✅ *Batta Claim Details*

👤 Employee: {employee['name']}
📍 Location: {context.get('location_name')}
🗓️ Days: {days}
💰 Rate: {format_currency(rate_per_day)}/day
💵 *Total: {format_currency(total_amount)}*

📎 Please upload your receipt(s) - you can send one or multiple images at once.
Or type *skip* if you don't have any."""

    # ===== FUEL FLOW =====
    if current_step == 'fuel_details':
        amount = extract_amount(text)
        
        context.update({
            'details': message_text,
            'user_amount': amount
        })

        await conversation_model.update(chat_id, {
            'current_step': 'receipt_upload',
            'context': context
        })

        amount_line = f"\n💵 Amount: {format_currency(amount)}" if amount else ''

        return f"""✅ *Fuel Expense Details*

👤 Employee: {employee['name']}
📝 Details: {message_text}{amount_line}

📎 Please upload your receipt(s) - you can send one or multiple images at once.
Or type *skip* if you don't have any."""

    # ===== ACCOMMODATION FLOW =====
    if current_step == 'accommodation_details':
        amount = extract_amount(text)
        location = await find_location_in_text(text)
        
        context.update({
            'details': message_text,
            'user_amount': amount,
            'location_id': location['id'] if location else None,
            'location_name': location['name'] if location else None
        })
        
        await conversation_model.update(chat_id, {
            'current_step': 'receipt_upload',
            'context': context
        })

        amount_line = f"\n💵 Amount: {format_currency(amount)}" if amount else ''

        return f"""✅ *Accommodation Claim Details*

👤 Employee: {employee['name']}
📝 Details: {message_text}{amount_line}

📎 Please upload your receipt(s) - you can send one or multiple images at once.
Or type *skip* if you don't have any."""

    # ===== SUNDRY FLOW =====
    if current_step == 'sundry_details':
        amount = extract_amount(text)
        
        # Determine category name for valid display
        category_code = state.get('category', 'Expense')
        category_name = category_code
        
        # Try to look up nice name if we have ID
        cat_id = context.get('category_id')
        if cat_id:
            try:
                cat_obj = await category_model.find_by_id(cat_id)
                if cat_obj:
                    category_name = cat_obj['name']
            except:
                pass

        context.update({
            'details': message_text,
            'user_amount': amount,
            'category_name': category_name  # Store for later
        })

        await conversation_model.update(chat_id, {
            'current_step': 'receipt_upload',
            'context': context
        })

        amount_line = f"\n💵 Amount: {format_currency(amount)}" if amount else ''

        return f"""✅ *{category_name} Details*

👤 Employee: {employee['name']}
📝 Details: {message_text}{amount_line}

📎 Please upload your receipt(s) - you can send one or multiple images at once.

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
            
            # Helper to get category name
            category_name = category_code
            cat_id = context.get('category_id')
            if cat_id:
                try:
                    cat_obj = await category_model.find_by_id(cat_id)
                    if cat_obj:
                        category_name = cat_obj['name']
                except:
                    pass

            summary = f"""✅ *Claim Summary*

👤 Employee: {employee['name']}
📁 Category: {category_name}
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
            
            # Helper to get category name
            category_name = category_code
            cat_id = context.get('category_id')
            if cat_id:
                try:
                    cat_obj = await category_model.find_by_id(cat_id)
                    if cat_obj:
                        category_name = cat_obj['name']
                except:
                    pass

            summary = f"""✅ *Claim Summary*

👤 Employee: {employee['name']}
📁 Category: {category_name}
📝 Details: {context.get('details', 'N/A')}"""
            
            display_amount = context.get('total_amount') or context.get('user_amount')
            if display_amount:
                summary += f"\n💵 Amount: {format_currency(display_amount)}"
            
            summary += "\n🧾 Receipt: ⏭️ Skipped"
            summary += "\n\nType *confirm* to submit or *menu* to start over."
            return summary
        
        # Handle receipt upload
        if media_info:
            # Extract receipt data from message_text
            extracted_amount = None
            extracted_vendor = None
            extracted_date = None
            
            if '[RECEIPT/DOCUMENT UPLOADED]' in message_text:
                print(f"🔍 DEBUG receipt_upload: Parsing receipt data from message_text")
                print(f"📝 DEBUG: Full message_text = {repr(message_text)}")
                
                # Extract vendor
                if 'Vendor:' in message_text:
                    vendor_part = message_text.split('Vendor:', 1)[1]
                    extracted_vendor = vendor_part.split('\n')[0].strip()
                    print(f"🏪 Extracted vendor: {extracted_vendor}")
                
                # Extract amount - handle both "Rs. 1000" and "Rs.1000" formats
                if 'Detected amount:' in message_text:
                    amount_part = message_text.split('Detected amount:', 1)[1]
                    # Extract everything after "Rs" or "Rs." until newline or end
                    amount_match = re.search(r'Rs\.?\s*([\d,\.]+)', amount_part)
                    if amount_match:
                        amount_str = amount_match.group(1)
                        try:
                            extracted_amount = float(amount_str.replace(',', ''))
                            print(f"💰 Extracted amount: Rs.{extracted_amount}")
                        except Exception as e:
                            print(f"❌ Error parsing amount '{amount_str}': {e}")
                
                # Extract date
                if 'Date:' in message_text:
                    date_part = message_text.split('Date:', 1)[1]
                    extracted_date = date_part.split('\n')[0].strip()
                    print(f"📅 Extracted date: {extracted_date}")
                
                # Extract full OCR text (everything between 'Extracted text:' and 'Detected amount:')
                extracted_ocr_text = None
                if 'Extracted text:' in message_text:
                    ocr_part = message_text.split('Extracted text:', 1)[1]
                    # Stop at 'Detected amount:' if present (that's our appended summary)
                    if 'Detected amount:' in ocr_part:
                        ocr_part = ocr_part.split('Detected amount:', 1)[0]
                    extracted_ocr_text = ocr_part.strip()
            
            # Create receipt object
            new_receipt = {
                'file_path': media_info.get('saved_filename'),
                'file_name': media_info.get('saved_filename'),
                'ocr_amount': extracted_amount or 0,
                'vendor': extracted_vendor or 'Unknown',
                'date': extracted_date,
                'ocr_raw_text': extracted_ocr_text,
                'message_id': media_info.get('message_id'),
                'file_size': media_info.get('file_size'),
                'mimetype': media_info.get('mimetype'),
                'file_hash': media_info.get('file_hash')
            }
            
            # ATOMIC: Add receipt to conversation (prevents race conditions)
            print(f"💾 Atomically adding receipt to conversation for {chat_id}")
            updated_state = await conversation_model.add_receipt(chat_id, new_receipt)
            
            if not updated_state:
                print(f"❌ Failed to add receipt atomically")
                return "❌ Error saving receipt. Please try again."
            
            # Get updated context with all receipts
            updated_context = updated_state.get('context')
            if isinstance(updated_context, str):
                import json
                try:
                    updated_context = json.loads(updated_context)
                except:
                    updated_context = {}
            
            receipts = updated_context.get('receipts', [])
            receipt_num = len(receipts)
            
            # Calculate running total
            receipt_total = sum(r.get('ocr_amount', 0) for r in receipts)
            user_amount = updated_context.get('total_amount') or updated_context.get('user_amount') or 0
            
            print(f"✅ Receipt #{receipt_num} added. Total receipts: {receipt_num}, Running total: Rs.{receipt_total}")
            
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
                
                # Use find_category to accept code or name
                # PRIORITIZE correct ID from context if available
                category = None
                cat_id = context.get('category_id')
                
                if cat_id:
                    try:
                        category = await category_model.find_by_id(cat_id)
                    except:
                        pass
                
                # Fallback to code lookup (legacy or if context lost)
                if not category:
                    category = await rates_model.find_category(category_code)
                
                if not category:
                    return '❌ Error: Category not found. Type "menu" to start over.'

                # Create claim in database
                claim = await claim_model.create({
                    'employee_id': employee['id'],
                    'category_id': category['id'],
                    'location_id': context.get('location_id'), # No fallback to employee.location_id per request
                    'claim_type': 'outright' if category_code == 'BATTA' else 'bill',
                    'duration_days': context.get('days', 1),
                    'user_amount': context.get('user_amount'),
                    'system_amount': context.get('total_amount') or context.get('user_amount'),
                    'description': context.get('details') or f'{category_code} claim',
                    'manager_id': employee.get('manager_id')
                })
                # Initialize multi-step approval workflow for WhatsApp-created claims.
                await claim_model.initialize_approval_workflow(claim['id'])


                # Save ALL receipts to database (supports multi-receipt)
                receipts = context.get('receipts', [])
                media_info_list = []  # For manager notification
                
                if receipts:
                    print(f"💾 Saving {len(receipts)} receipt(s) to database for claim {claim['id']}")
                    for i, receipt in enumerate(receipts, 1):
                        try:
                            # Check for duplicates
                            file_hash = receipt.get('file_hash')
                            duplicate = await claim_model.check_duplicate_receipt(file_hash, current_claim_id=claim['id'])
                            
                            is_duplicate = False
                            if duplicate:
                                print(f"⚠️ Duplicate receipt detected! Used in claim #{duplicate.get('claim_number')}")
                                is_duplicate = True
                                media_info_list.append({
                                    'saved_filename': receipt.get('file_path'),
                                    'message_id': receipt.get('message_id'),
                                    'mimetype': receipt.get('mimetype'),
                                    'warning': {
                                        'type': 'duplicate',
                                        'message': f"Potential duplicate: Used in Claim #{duplicate.get('claim_number')} by {duplicate.get('employee_name')} on {duplicate.get('created_at').strftime('%Y-%m-%d') if duplicate.get('created_at') else 'unknown date'}",
                                        'original_claim': duplicate
                                    }
                                })
                            else:
                                # Build media_info for manager notification (no warning)
                                media_info_list.append({
                                    'saved_filename': receipt.get('file_path'),
                                    'message_id': receipt.get('message_id'),
                                    'mimetype': receipt.get('mimetype')
                                })

                            await claim_model.add_receipt(
                                claim_id=claim['id'],
                                file_path=receipt.get('file_path'),
                                file_name=receipt.get('file_name'),
                                file_type=receipt.get('mimetype'),
                                file_size=receipt.get('file_size'),
                                ocr_amount=receipt.get('ocr_amount'),
                                ocr_raw_text=receipt.get('ocr_raw_text'),  # Full Textract OCR text
                                message_id=receipt.get('message_id'),
                                vendor=receipt.get('vendor'),
                                file_hash=file_hash
                            )
                            print(f"✅ Receipt #{i} saved to database")
                            
                        except Exception as receipt_error:
                            print(f"⚠️ Failed to save receipt #{i}: {receipt_error}")
                else:
                    # Backwards compatibility: Check for old single-receipt format
                    stored_media_info = context.get('media_info')
                    print(f"🔍 DEBUG legacy path: stored_media_info keys={list(stored_media_info.keys()) if stored_media_info else None}")
                    if stored_media_info and stored_media_info.get('saved_filename'):
                        try:
                            print(f"💾 Saving single receipt (legacy) to database for claim {claim['id']}")
                            
                            # Check for duplicates using file_hash
                            file_hash = stored_media_info.get('file_hash')
                            print(f"🔑 Legacy path file_hash: {file_hash[:16] if file_hash else None}")
                            if file_hash:
                                duplicate = await claim_model.check_duplicate_receipt(file_hash, current_claim_id=claim['id'])
                                if duplicate:
                                    print(f"⚠️ Duplicate receipt detected! Used in claim #{duplicate.get('claim_number')}")
                                    stored_media_info['warning'] = {
                                        'type': 'duplicate',
                                        'message': f"Potential duplicate: Used in Claim #{duplicate.get('claim_number')} by {duplicate.get('employee_name')} on {duplicate.get('created_at').strftime('%Y-%m-%d') if duplicate.get('created_at') else 'unknown date'}",
                                        'original_claim': duplicate
                                    }
                            
                            await claim_model.add_receipt(
                                claim_id=claim['id'],
                                file_path=stored_media_info.get('saved_filename'),
                               file_name=stored_media_info.get('saved_filename'),
                                file_type=stored_media_info.get('mimetype'),
                                file_size=stored_media_info.get('saved_file_size'),
                                ocr_amount=stored_media_info.get('extracted_amount'),
                                ocr_raw_text=stored_media_info.get('ocr_text'),
                                message_id=stored_media_info.get('message_id'),
                                vendor=stored_media_info.get('vendor') or context.get('receipt_vendor'),
                                file_hash=file_hash
                            )
                            media_info_list.append(stored_media_info)
                            print(f"✅ Receipt saved to database successfully")
                        except Exception as receipt_error:
                            print(f"⚠️ Failed to save receipt to database: {receipt_error}")
                    else:
                        print(f"⚠️ No media_info found in context - receipt NOT saved!")
                
                # Recalculate system amount from saved receipts
                if receipts or media_info_list:
                    await claim_model.calculate_system_amount(claim['id'])
                
                
                # Notifications: direct manager first, approval policy fallback.
                print(f"🔍 DEBUG: employee.manager_id={employee.get('manager_id')}, manager_name={employee.get('manager_name')}")
                duplicate_warnings = [item['warning'] for item in media_info_list if item.get('warning')]
                if employee.get('manager_id'):
                    print(f"📤 Sending to direct manager ID: {employee.get('manager_id')}")
                    await notification_service.notify_manager_of_new_claim(
                        claim,
                        media_info_list,
                        duplicate_warnings=duplicate_warnings,
                    )
                else:
                    routed = await notification_service.notify_next_approver_of_claim(
                        claim, duplicate_warnings=duplicate_warnings
                    )
                    if not routed:
                        print(f"⚠️ No manager or approval policy approver for {employee['name']}")

                # Reset conversation
                await conversation_model.reset(chat_id)

                # Route notice (who received the approval request).
                manager_notice = ''
                pending_task = await claim_model.get_current_pending_task(claim['id'])
                if pending_task and pending_task.get('assignee_employee_id'):
                    assignee = await employee_model.find_by_id(pending_task['assignee_employee_id'])
                    assignee_name = assignee.get('name') if assignee else None
                    if assignee_name:
                        manager_notice = f"\n\n📤 Sent to *{assignee_name}* for step {pending_task.get('step_order', 1)} approval."
                elif employee.get('manager_name'):
                    manager_notice = f"\n\n📤 Sent to *{employee['manager_name']}* for approval."

                final_amount = claim.get('system_amount') or claim.get('user_amount') or 0

                # Use verified category name from lookup
                category_name = category['name'] if category else 'Expense'
                
                # Check for difference again to show in final message
                diff_section = ""
                # Receipts from context are floats (JSON), Claim amount is Decimal (DB)
                # Must cast to float for comparison
                val_final_amount = float(final_amount)
                receipt_total = sum(float(r.get('ocr_amount', 0)) for r in receipts)
                
                if receipt_total > 0 and val_final_amount > 0:
                     diff = abs(receipt_total - val_final_amount)
                     diff_pct = (diff / val_final_amount) * 100
                     if diff_pct > 5:
                         diff_section = f"\n⚠️ *Difference:* Rs. {diff:,.0f} ({diff_pct:.1f}%)"

                return f"""🎉 *Claim Submitted Successfully!*

📋 Claim #: *{claim['claim_number']}*
📁 Category: {category_name}
💵 Amount: {format_currency(final_amount)}{diff_section}{manager_notice}

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


# ==========================================
# HELPER FUNCTIONS
# ==========================================

async def _get_advance_category_id() -> int:
    """Helper to find or fallback to a category ID for Advance claims"""
    # Try to find 'ADVANCE' category
    try:
        cat = await category_model.find_by_code('ADVANCE')
        if cat:
            return cat['id']
            
        # Try to find 'General' or 'Sundry'
        cat = await category_model.find_by_code('SUNDRY')
        if cat:
            return cat['id']
            
        # Fallback to first available
        cats = await category_model.find_all()
        if cats:
             return cats[0]['id']
    except:
        pass
        
    return 1 # Fallback to ID 1 if all else fails


def _generate_advance_summary(employee: dict, context: dict) -> str:
    """Generate summary string for advance request"""
    amount = context.get('user_amount', 0)
    desc = context.get('details', 'N/A')
    has_quote = context.get('has_quotation', False)
    receipts = context.get('receipts', [])
    
    # Build quotation section
    quote_section = ""
    if receipts and len(receipts) > 0:
        quote_section = f"\n\n📎 *Quotations ({len(receipts)}):*"
        for i, receipt in enumerate(receipts, 1):
            q_amount = receipt.get('ocr_amount', 0)
            q_vendor = receipt.get('vendor', 'Unknown')
            amount_text = f"Rs. {q_amount:,.0f}" if q_amount > 0 else "Amount not detected"
            quote_section += f"\n  {i}. {amount_text} - {q_vendor}"
    else:
        quote_section = "\n\n📎 Quotation: Skipped"
    
    # Calculate total from quotations if any
    total_section = ""
    if receipts and len(receipts) > 0:
        total_from_quotations = sum(float(r.get('ocr_amount', 0) or 0) for r in receipts)
        if total_from_quotations > 0:
            total_section = f"\n\n🧮 *Total from quotations:* Rs. {total_from_quotations:,.0f}"
    
    # Get category name from context
    category_name = context.get('category_name', 'N/A')
    
    return f"""✅ *Claim Summary*

👤 Employee: {employee['name']}
📁 Category: {category_name}
📝 Details: {desc}
💵 Amount: {format_currency(amount)}{quote_section}{total_section}

Type *confirm* to submit or *menu* to start over."""


