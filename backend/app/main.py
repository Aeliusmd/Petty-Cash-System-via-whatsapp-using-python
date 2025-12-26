"""
WhatsApp Backend Server
Receives webhook events from WAHA and sends auto-replies

FastAPI-based async server replacing Express.js
"""

import os
import asyncio
import random
import time
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Load environment variables from root .env file
# Try multiple locations: root, backend, current directory
for env_path in ['.env', '../.env', '../../.env', Path(__file__).parent.parent.parent.parent / '.env']:
    if Path(env_path).exists():
        load_dotenv(env_path)
        break
else:
    load_dotenv()  # Default behavior

from app.db import db
from app import waha_client
from app import reply_engine
from app.services import textract_service


# Message deduplication cache (prevents processing same message multiple times)
processed_messages: set = set()
MAX_CACHE_SIZE = 1000


def is_message_processed(message_id: str) -> bool:
    """Check if message was already processed"""
    if not message_id:
        return False
    if message_id in processed_messages:
        return True
    # Add to cache and clean up if too large
    processed_messages.add(message_id)
    if len(processed_messages) > MAX_CACHE_SIZE:
        # Remove oldest entry
        processed_messages.pop()
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events"""
    # Startup
    print('🚀 Starting WhatsApp Backend...')
    
    # Test database connection
    try:
        await db.connect()
        if await db.check_connection():
            print('📦 Database connected successfully')
        else:
            print('⚠️ Database not connected - running without DB features')
            print('   Run "python -m app.db.setup" to initialize the database')
    except Exception as e:
        print(f'⚠️ Database connection failed: {e}')
        print('   Run "python -m app.db.setup" to initialize the database')
    
    yield
    
    # Shutdown
    await db.close()


app = FastAPI(
    title="WhatsApp Petty Cash Backend",
    description="Receives webhook events from WAHA and sends auto-replies",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "WhatsApp Petty Cash Backend (Python)",
        "status": "running",
        "endpoints": {
            "health": "GET /health",
            "webhook": "POST /webhooks/waha"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    from datetime import datetime
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }


async def process_message(correlation_id: str, payload: dict, session: str):
    """
    Background task to process incoming WhatsApp message
    """
    try:
        # DEBUG: Log payload structure to understand WAHA format
        print(f'[{correlation_id}] 🔍 DEBUG: Payload keys: {list(payload.keys())}')
        print(f'[{correlation_id}] 🔍 DEBUG: body={payload.get("body")}, text={payload.get("text")}, type={payload.get("type")}')
        
        # Check if message is from us (outgoing)
        is_from_me = payload.get('fromMe') or payload.get('from_me', False)
        if is_from_me:
            print(f'[{correlation_id}] ⏭️ Skipping outgoing message')
            return

        # Extract message text (handle different WAHA field names including nested _data)
        message_text = (
            payload.get('body') or 
            payload.get('text') or 
            payload.get('message') or
            payload.get('_data', {}).get('body') or  # WAHA may send text in nested _data.body
            ''
        )

        # Extract chat ID
        chat_id = (payload.get('chatId') or payload.get('chat_id') or 
                   payload.get('from') or payload.get('remoteJid'))

        if not chat_id:
            print(f'[{correlation_id}] ⚠️ No chatId found in payload')
            return

        # Check for media attachments (image, document, pdf)
        has_media = payload.get('hasMedia') or payload.get('media') or (payload.get('_data') or {}).get('media')
        media_type = payload.get('type') or payload.get('messageType') or (payload.get('_data') or {}).get('type')
        mime_type = payload.get('mimetype') or (payload.get('_data') or {}).get('mimetype', '') or ''

        # Media data from WAHA - use (x or {}) pattern to handle None values
        media_obj = payload.get('media') or {}
        _data_obj = payload.get('_data') or {}
        _data_media_obj = _data_obj.get('media') or {}
        
        media_data = (media_obj.get('data') or 
                      _data_media_obj.get('data') or
                      payload.get('mediaData'))
        media_url = (media_obj.get('url') or 
                     payload.get('mediaUrl') or 
                     _data_obj.get('mediaUrl'))
        media_filename = (media_obj.get('filename') or
                          _data_media_obj.get('filename'))

        # Handle media messages (images, PDFs)
        if has_media and (media_type in ('image', 'document') or 
                          'image' in mime_type or 'pdf' in mime_type):
            print(f'[{correlation_id}] 📎 Media attachment detected: {media_type} ({mime_type})')
            print(f'[{correlation_id}] 📎 Media fields - hasData: {bool(media_data)}, hasUrl: {bool(media_url)}, filename: {media_filename or "none"}')

            try:
                extraction_result = None

                # Option 1: Use base64 data directly from payload
                if media_data:
                    print(f'[{correlation_id}] 📥 Using base64 media data from payload')
                    import base64
                    image_buffer = base64.b64decode(media_data)
                    extraction_result = await textract_service.extract_text_from_image(image_buffer)

                # Option 2: Use media URL if provided
                elif media_url:
                    # Fix URL for Docker networking
                    waha_base_url = os.getenv('WAHA_BASE_URL', 'http://waha:3000')
                    fixed_media_url = (media_url
                        .replace('http://localhost:3000', waha_base_url)
                        .replace('http://127.0.0.1:3000', waha_base_url))
                    print(f'[{correlation_id}] 📥 Downloading from media URL: {fixed_media_url}')
                    extraction_result = await textract_service.extract_text_from_url(fixed_media_url, mime_type)

                # Option 3: Try to download from WAHA files endpoint
                elif media_filename:
                    waha_base_url = os.getenv('WAHA_BASE_URL', 'http://waha:3000')
                    waha_session = os.getenv('WAHA_SESSION', 'default')
                    files_url = f"{waha_base_url}/api/files/{waha_session}/{media_filename}"
                    print(f'[{correlation_id}] 📥 Trying files endpoint: {files_url}')
                    extraction_result = await textract_service.extract_text_from_url(files_url, mime_type)

                if extraction_result and extraction_result.get('success') and extraction_result.get('text'):
                    print(f'[{correlation_id}] 📄 Extracted text: "{extraction_result["text"][:100]}..."')

                    # Extract amount if this is a receipt
                    extracted_amount = textract_service.extract_amount_from_text(extraction_result['text'])
                    if extracted_amount:
                        print(f'[{correlation_id}] 💰 Detected amount: Rs.{extracted_amount}')

                    # Add extracted text to message for processing
                    amount_text = f'\nDetected amount: Rs.{extracted_amount}' if extracted_amount else ''
                    message_text = f"[RECEIPT/DOCUMENT UPLOADED]\nExtracted text: {extraction_result['text']}{amount_text}"
                else:
                    print(f'[{correlation_id}] ⚠️ Could not extract text from media')
                    message_text = "[IMAGE/DOCUMENT UPLOADED - Text extraction pending]"

            except Exception as textract_error:
                print(f'[{correlation_id}] ❌ Textract error: {textract_error}')
                message_text = "[IMAGE/DOCUMENT UPLOADED]"

        # Handle Location Messages
        if media_type in ('location', 'live_location'):
            location = payload.get('location') or payload.get('_data') or {}
            lat = location.get('latitude') or payload.get('lat')
            lon = location.get('longitude') or payload.get('lng')
            
            if lat and lon:
                print(f'[{correlation_id}] 📍 Location detected: {lat}, {lon}')
                message_text = f"[LOCATION_SHARED] lat:{lat} lon:{lon}"

        if not message_text:
            # Debug: Log payload structure to help diagnose empty message issues
            print(f'[{correlation_id}] 🔍 DEBUG: Empty message, payload keys: {list(payload.keys())}')
            if payload.get('_data'):
                print(f'[{correlation_id}] 🔍 DEBUG: _data keys: {list(payload.get("_data", {}).keys())}')
            print(f'[{correlation_id}] ⏭️ Empty message body, skipping')
            return

        display_text = message_text[:100] + '...' if len(message_text) > 100 else message_text
        print(f'[{correlation_id}] 💬 Message from {chat_id}: "{display_text}"')

        # Generate reply using replyEngine
        reply_text = await reply_engine.generate_reply(message_text, chat_id)

        if not reply_text:
            print(f'[{correlation_id}] ⏭️ No reply generated')
            return

        # Show typing indicator (human-like behavior)
        try:
            await waha_client.start_typing(chat_id)
            print(f'[{correlation_id}] ⌨️ Typing indicator sent')
        except Exception as typing_error:
            print(f'[{correlation_id}] ⚠️ Could not send typing indicator: {typing_error}')

        # Add natural delay (500-1200ms) to seem more human
        delay = 0.5 + random.random() * 0.7
        await asyncio.sleep(delay)

        # Stop typing indicator
        try:
            await waha_client.stop_typing(chat_id)
        except:
            pass

        # Send the reply
        await waha_client.send_text(chat_id, reply_text)
        print(f'[{correlation_id}] ✅ Reply sent: "{reply_text}"')

    except Exception as error:
        print(f'[{correlation_id}] ❌ Error processing webhook: {error}')


@app.post("/webhooks/waha")
async def waha_webhook(request: Request):
    """
    WAHA Webhook Endpoint
    Receives message events from WAHA and sends auto-replies
    """
    # Generate correlation ID for request tracking
    correlation_id = f"req_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"

    try:
        body = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    print(f'[{correlation_id}] 📥 Incoming webhook event')
    print(f'[{correlation_id}] Event type: {body.get("event", "unknown")}')

    event = body.get('event')
    payload = body.get('payload')
    session = body.get('session')

    # Only process incoming messages
    if event not in ('message', 'message.any'):
        print(f'[{correlation_id}] ⏭️ Skipping non-message event: {event}')
        return {"received": True, "correlationId": correlation_id}

    if not payload:
        print(f'[{correlation_id}] ⚠️ No payload in webhook')
        print(f'[{correlation_id}] 🔍 DEBUG: Full body keys: {list(body.keys())}')
        return {"received": True, "correlationId": correlation_id}

    # Deduplicate messages
    message_id = payload.get('id') or (payload.get('_data', {}).get('id', {}).get('id'))
    print(f'[{correlation_id}] 🔍 DEBUG: message_id={message_id}, fromMe={payload.get("fromMe")}')
    if is_message_processed(message_id):
        print(f'[{correlation_id}] ⏭️ Duplicate message, skipping: {message_id}')
        return {"received": True, "correlationId": correlation_id}

    # Process message asynchronously using asyncio.create_task (more reliable than BackgroundTasks)
    asyncio.create_task(process_message(correlation_id, payload, session))

    # Return 200 immediately to prevent WAHA retry storms
    return {"received": True, "correlationId": correlation_id}


# App module init
@app.on_event("startup")
async def startup_info():
    """Print startup info"""
    port = os.getenv('PORT', '4101')
    print(f'🚀 WhatsApp Backend running on port {port}')
    print(f'📡 Webhook endpoint: POST /webhooks/waha')
    print(f'🏥 Health check: GET /health')


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', '4101'))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
