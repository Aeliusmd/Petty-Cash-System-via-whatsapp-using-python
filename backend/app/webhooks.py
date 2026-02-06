"""
Webhook Controller
API routes for WhatsApp webhook events
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app import waha_client
from app import reply_engine
from app.models.employee import Employee
from app.services import textract_service
import base64
import os
import uuid
import httpx

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Message deduplication
processed_messages: set = set()
MAX_CACHE_SIZE = 1000


def is_message_processed(message_id: str) -> bool:
    """Check if message was already processed"""
    if not message_id:
        return False
    if message_id in processed_messages:
        return True
    processed_messages.add(message_id)
    if len(processed_messages) > MAX_CACHE_SIZE:
        processed_messages.pop()
    return False


@router.post("/waha")
async def webhook_handler(request: Request):
    """
    Handle incoming WhatsApp webhook events from WAHA.
    
    Event types handled:
    - message: Text and media messages
    - message.any: All message types
    - poll.vote: Poll responses
    """
    try:
        body = await request.json()
    except Exception as e:
        print(f"❌ Failed to parse webhook body: {e}")
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    
    event_type = body.get("event")
    payload = body.get("payload", {})
    
    print(f"📨 Webhook received: {event_type}")
    
    # Handle different event types
    if event_type in ["message", "message.any"]:
        return await handle_message_event(payload)
    elif event_type == "poll.vote":
        return await handle_poll_vote_event(payload)
    
    return {"status": "ignored", "event": event_type}


async def handle_message_event(payload: dict):
    """Process incoming message events"""
    # Skip if from self or already processed
    if payload.get("fromMe"):
        return {"status": "skipped", "reason": "own_message"}
    
    message_id = payload.get("id")
    if is_message_processed(message_id):
        return {"status": "skipped", "reason": "duplicate"}
    
    # Extract message info
    chat_id = payload.get("from")
    
    # Handle LID format (get actual phone from remoteJidAlt)
    data_key = payload.get("_data", {}).get("key", {})
    remote_jid_alt = data_key.get("remoteJidAlt", "")
    if remote_jid_alt and "@" in remote_jid_alt:
        phone = remote_jid_alt.split("@")[0]
    else:
        phone = chat_id.split("@")[0] if chat_id else ""
    
    print(f"📱 Message from: {phone} (chat: {chat_id})")
    
    # Find or identify employee
    employee = await Employee.find_by_chat_id(chat_id)
    if not employee:
        employee = await Employee.find_by_phone(phone)
        if employee:
            # Link chat ID to employee
            await Employee.link_chat_id(employee.id, chat_id)
            print(f"✅ Linked chat_id to employee: {employee.name}")
    
    if not employee:
        await waha_client.send_text(
            chat_id,
            "👋 Welcome! Your phone number is not registered in our system. Please contact your administrator."
        )
        return {"status": "error", "reason": "employee_not_found"}
    
    # Show typing indicator
    try:
        await waha_client.start_typing(chat_id)
    except:
        pass
    
    # Check for media (receipt)
    has_media = payload.get("hasMedia", False)
    media_url = payload.get("mediaUrl") or (payload.get("media") or {}).get("url")
    
    # DEBUG: Dump media info
    print(f"🔍 DEBUG: hasMedia={has_media}, mediaUrl={media_url}")
    if payload.get("media"):
        print(f"🔍 DEBUG: payload['media'] keys: {payload['media'].keys()}")
    
    media_data = payload.get("media", {}).get("data") if payload.get("media") else None
    
    media_info = None
    if True: # Force check to debug if has_media is False but media exists
        # Safe access to media dict
        media_obj = payload.get("media") or {}
        
        if has_media or media_obj:
            mimetype = media_obj.get("mimetype", payload.get("mimetype", "image/jpeg"))
            filename = media_obj.get("filename", "receipt")
            media_info = {
                "url": media_url,
                "data": media_data,
                "mimetype": mimetype,
                "filename": filename,
                "message_id": message_id
            }
            print(f"📎 Media attached: {mimetype}")

        if (media_url or media_data) and 'image' in mimetype:
            print("🔍 Processing receipt media...")
            await waha_client.send_text(chat_id, "🔍 Analyzing receipt...")
            
            # 1. Get Image Bytes
            image_bytes = None
            try:
                if media_data:
                    image_bytes = base64.b64decode(media_data)
                elif media_url:
                    # Use WAHA_BASE_URL from config to determine correct hostname
                    from app.config import Config
                    waha_base = Config.WAHA_BASE_URL
                    
                    # If WAHA is at localhost (local dev), keep localhost
                    # If WAHA is at waha:3000 (full Docker), replace localhost with waha
                    if 'localhost' not in waha_base and 'localhost' in media_url:
                        print(f"🔄 Fixing media URL for Docker deployment")
                        media_url = media_url.replace('localhost', 'waha').replace('127.0.0.1', 'waha')
                    
                    print(f"⬇️ Downloading media from: {media_url}")
                    
                    # Add WAHA API key for authentication
                    headers = {}
                    waha_api_key = os.getenv('WAHA_API_KEY')
                    if waha_api_key:
                        headers['X-Api-Key'] = waha_api_key
                    
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(media_url, headers=headers, timeout=30.0)
                        if resp.status_code == 200:
                            image_bytes = resp.content
                        else:
                            print(f"❌ Failed to download media: {resp.status_code}")
            except Exception as e:
                print(f"❌ Error getting media bytes: {e}")

            # 2. Save File & Extract (if we have bytes)
            extraction = None
            saved_filename = None
            
            if image_bytes:
                # Save to disk
                try:
                    # Use shared receipts directory from config
                    from app.config_paths import RECEIPTS_DIR
                    receipts_dir = str(RECEIPTS_DIR)
                    
                    # Generate filename
                    ext = mimetype.split('/')[-1] or 'jpg'
                    saved_filename = f"{uuid.uuid4()}.{ext}"
                    save_path = os.path.join(receipts_dir, saved_filename)
                    
                    # Write file
                    with open(save_path, "wb") as f:
                        f.write(image_bytes)
                    print(f"💾 Saved receipt to {save_path}")
                    
                    # Update media_info with saved filename for reply_engine
                    if media_info:
                        media_info['saved_filename'] = saved_filename
                        media_info['file_size'] = len(image_bytes)

                    # Extract
                    extraction = await textract_service.extract_expense_from_image(image_bytes)
                    
                except Exception as e:
                    print(f"❌ Error saving/extracting: {e}")


            # 3. Append to Message
            if extraction and extraction.get('success'):
                print("✅ Extraction successful, appending to message")
                
                # Construct the magic string for reply_engine
                extracted_text = extraction.get('text', '')
                expense = extraction.get('expense', {})
                
                print(f"🔍 DEBUG webhook: extraction keys: {list(extraction.keys())}")
                print(f"🔍 DEBUG webhook: expense keys: {list(expense.keys())}")
                
                # Try to get best amount
                amount = expense.get('total')
                print(f"🔍 DEBUG webhook: Initial amount from expense['total']: {amount}")
                if not amount:
                    raw_amount = textract_service.extract_amount_from_text(extracted_text)
                    if raw_amount:
                        amount = f"{raw_amount:.2f}"
                
                vendor = expense.get('vendorName', '')
                date_str = expense.get('date', '')
                
                # Append to existing text (caption) or start fresh
                text_content = (payload.get("body") or payload.get("text") or "").strip()
                
                extra_info = f"\nExtracted text: {extracted_text}"
                if amount:
                    extra_info += f"\nDetected amount: Rs.{amount}"
                if vendor:
                    extra_info += f"\nVendor: {vendor}"
                if date_str:
                    extra_info += f"\nDate: {date_str}"
                    
                text = f"{text_content} [RECEIPT/DOCUMENT UPLOADED]{extra_info}"
            else:
                err = extraction.get('error') if extraction else "Processing failed"
                print(f"⚠️ Extraction/Processing failed: {err}")
                text = (payload.get("body") or payload.get("text") or "").strip()
                # Still mark as uploaded so we can ask for details manually
                text = f"{text} [RECEIPT/DOCUMENT UPLOADED]"
        else:
             text = (payload.get("body") or payload.get("text") or "").strip()
    else:
        # Get message text
        text = (payload.get("body") or payload.get("text") or "").strip()
    
    # Process through reply engine
    try:
        response = await reply_engine.process_message(
            chat_id=chat_id,
            message=text,
            employee_id=employee.id if hasattr(employee, 'id') else employee.get('id'),
            media_info=media_info
        )
        
        if response:
            await waha_client.send_text(chat_id, response)
            return {"status": "ok", "replied": True}
        
        return {"status": "ok", "replied": False}
        
    except Exception as e:
        print(f"❌ Error processing message: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


async def handle_poll_vote_event(payload: dict):
    """Process poll vote events"""
    chat_id = payload.get("from")
    vote = payload.get("vote", {})
    selected_options = vote.get("selectedOptions", [])
    
    if not selected_options:
        return {"status": "skipped", "reason": "no_selection"}
    
    # Get employee
    employee = await Employee.find_by_chat_id(chat_id)
    if not employee:
        return {"status": "error", "reason": "employee_not_found"}
    
    # Get selected option text
    selected = selected_options[0].get("name", "")
    print(f"📊 Poll vote: {selected} from {chat_id}")
    
    # Process as menu selection
    try:
        response = await reply_engine.process_message(
            chat_id=chat_id,
            message=selected,
            employee_id=employee.id if hasattr(employee, 'id') else employee.get('id')
        )
        
        if response:
            await waha_client.send_text(chat_id, response)
        
        return {"status": "ok"}
        
    except Exception as e:
        print(f"❌ Error processing poll vote: {e}")
        return {"status": "error", "error": str(e)}


# Export for backwards compatibility
webhook_router = router
