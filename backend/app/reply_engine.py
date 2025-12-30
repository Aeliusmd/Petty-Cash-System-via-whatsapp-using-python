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


def normalize_text(text: str) -> str:
    """Normalize message text for comparison"""
    return (text or '').lower().strip()


def extract_phone_from_chat_id(chat_id: str) -> Optional[str]:
    """
    Extract phone number from chat ID
    Chat IDs are typically in format: 94771234567@c.us
    """
    if not chat_id:
        return None
    # Remove @c.us, @s.whatsapp.net, etc.
    return re.sub(r'\D', '', chat_id.split('@')[0])


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
    """Extract amount from text (e.g., "Rs.5000", "LKR 3000", "5000")"""
    match = re.search(r'(?:rs\.?|lkr\.?|රු\.?)?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', text, re.IGNORECASE)
    if match:
        return float(match.group(1).replace(',', ''))
    return None


def format_currency(amount: float) -> str:
    """Format amount as currency string"""
    return f"Rs.{amount:,.0f}"


async def generate_reply(message_text: str, chat_id: str) -> Optional[str]:
    """
    Main reply generation function
    
    Args:
        message_text: The incoming message text
        chat_id: The chat ID for conversation context
        
    Returns:
        Reply text or None if no reply
    """
    # 1. Skip group chats entirely
    if is_group_chat(chat_id):
        print(f'⏭️ Skipping group chat: {chat_id}')
        return None

    # 2. Extract phone number from chat ID
    phone_number = extract_phone_from_chat_id(chat_id)
    if not phone_number:
        print(f'⚠️ Could not extract phone from chatId: {chat_id}')
        return None

    # 3. Check if this phone number is registered in the database
    employee = await employee_model.find_by_phone(phone_number)
    
    # Also try to find by chat ID if phone lookup fails
    if not employee:
        employee = await employee_model.find_by_chat_id(chat_id)

    # 4. If not registered, don't respond
    if not employee:
        print(f'⏭️ Unregistered number, ignoring: {phone_number}')
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
            
            # Notify staff of appeal submission
            await notification_service.notify_staff_of_appeal_submitted(updated_claim)
            
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
        
        if category and current_step not in ('initial', 'menu'):
            await conversation_model.update(chat_id, {
                'current_step': 'confirm',
                'context': {
                    **context,
                    'receipt_vendor': vendor,
                    'receipt_date': date_str,
                    'user_amount': amount,
                    'details': extracted_text[:500],
                    'has_receipt': True
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

        # If not in any flow, ask which category to use
        await conversation_model.update(chat_id, {
            'current_step': 'receipt_category',
            'context': {
                'receipt_vendor': vendor,
                'receipt_date': date_str,
                'user_amount': amount,
                'extracted_text': extracted_text[:500],
                'has_receipt': True
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
            'current_step': 'confirm',
            'context': {
                **context,
                'days': days,
                'total_amount': total_amount
            }
        })

        return f"""✅ *Batta Claim Summary*

👤 Employee: {employee['name']}
📍 Location: {context.get('location_name')}
🗓️ Days: {days}
💰 Rate: {format_currency(rate_per_day)}/day
💵 *Total: {format_currency(total_amount)}*

Type *confirm* to submit or *menu* to start over."""

    # ===== FUEL FLOW =====
    if current_step == 'fuel_details':
        amount = extract_amount(text)
        
        await conversation_model.update(chat_id, {
            'current_step': 'confirm',
            'context': {
                'details': message_text,
                'user_amount': amount
            }
        })

        amount_line = f"\n💵 Amount: {format_currency(amount)}" if amount else ''

        return f"""✅ *Fuel Expense Summary*

👤 Employee: {employee['name']}
📝 Details: {message_text}{amount_line}

Type *confirm* to submit or *menu* to start over."""

    # ===== ACCOMMODATION FLOW =====
    if current_step == 'accommodation_details':
        amount = extract_amount(text)
        location = await find_location_in_text(text)
        
        await conversation_model.update(chat_id, {
            'current_step': 'confirm',
            'context': {
                'details': message_text,
                'user_amount': amount,
                'location_id': location['id'] if location else None,
                'location_name': location['name'] if location else None
            }
        })

        amount_line = f"\n💵 Amount: {format_currency(amount)}" if amount else ''

        return f"""✅ *Accommodation Claim Summary*

👤 Employee: {employee['name']}
📝 Details: {message_text}{amount_line}

Type *confirm* to submit or *menu* to start over."""

    # ===== SUNDRY FLOW =====
    if current_step == 'sundry_details':
        amount = extract_amount(text)
        
        await conversation_model.update(chat_id, {
            'current_step': 'confirm',
            'context': {
                'details': message_text,
                'user_amount': amount
            }
        })

        amount_line = f"\n💵 Amount: {format_currency(amount)}" if amount else ''

        return f"""✅ *Sundry Expense Summary*

👤 Employee: {employee['name']}
📝 Details: {message_text}{amount_line}

Type *confirm* to submit or *menu* to start over."""

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
