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
from typing import Any, Optional, List

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
from app.services import notification_service
from app.models import claim as claim_model
from app.models import employee as employee_model
from app.models import otp as otp_model
from app.utils import jwt_utils


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

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Next.js domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API requests
class RejectClaimRequest(BaseModel):
    reason: str


class ApproveClaimRequest(BaseModel):
    final_amount: Optional[float] = None


class RequestOTPRequest(BaseModel):
    phone_number: str


class VerifyOTPRequest(BaseModel):
    phone_number: str
    otp_code: str


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


# ==============================================
# Authentication Endpoints
# ==============================================

@app.post("/api/auth/init-db")
async def init_auth_database():
    """
    Initialize authentication database tables
    Creates otp_codes table and adds is_admin column to employees
    """
    try:
        # Create OTP codes table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS otp_codes (
                id SERIAL PRIMARY KEY,
                phone_number VARCHAR(20) NOT NULL,
                code VARCHAR(6) NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        await db.execute("CREATE INDEX IF NOT EXISTS idx_phone_number_otp ON otp_codes(phone_number)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_expires_at_otp ON otp_codes(expires_at)")
        
        # Add is_admin and is_manager columns to employees
        await db.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE")
        await db.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS is_manager BOOLEAN DEFAULT FALSE")
        
        return {"message": "Authentication database initialized successfully"}
    except Exception as e:
        print(f"❌ Error initializing auth database: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/request-otp")
async def request_otp(request: RequestOTPRequest):
    """
    Request an OTP code for login
    Generates a 6-digit code and sends it via WhatsApp
    """
    try:
        phone_number = request.phone_number.strip()
        
        # Normalize phone number (remove spaces, dashes)
        import re
        phone_number = re.sub(r'[\s\-+]', '', phone_number)
        
        # Check if employee exists
        employee = await employee_model.find_by_phone(phone_number)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found with this phone number")
        
        # Check rate limit
        if await otp_model.check_rate_limit(phone_number):
            raise HTTPException(status_code=429, detail="Too many OTP requests. Please wait 1 hour.")
        
        # Generate OTP
        otp_code = await otp_model.generate_otp(phone_number)
        
        # Send OTP via WhatsApp
        chat_id = employee.get('whatsapp_chat_id')
        if chat_id:
            message = f"""🔐 *Login Verification Code*

Your OTP code is: *{otp_code}*

This code will expire in 5 minutes.

Do not share this code with anyone."""
            await waha_client.send_text(chat_id, message)
            print(f"✅ Sent OTP {otp_code} to {employee['name']}")
        else:
            print(f"⚠️ No WhatsApp chat ID for {employee['name']}, OTP: {otp_code}")
        
        return {
            "message": "OTP sent successfully",
            "phone_number": phone_number,
            # For testing/dev: include OTP in response (remove in production!)
            "otp_code": otp_code if not os.getenv('PRODUCTION') else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error requesting OTP: {e}")
        raise HTTPException(status_code=500, detail="Failed to send OTP")


@app.post("/api/auth/verify-otp")
async def verify_otp(request: VerifyOTPRequest):
    """
    Verify OTP code and return JWT token
    """
    try:
        phone_number = request.phone_number.strip()
        otp_code = request.otp_code.strip()
        
        # Normalize phone number
        import re
        phone_number = re.sub(r'[\s\-+]', '', phone_number)
        
        # Verify OTP
        is_valid = await otp_model.verify_otp(phone_number, otp_code)
        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid or expired OTP code")
        
        # Get employee details
        employee = await employee_model.find_by_phone(phone_number)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Determine role: admin > manager > employee
        is_admin = employee.get('is_admin', False)
        is_manager = employee.get('is_manager', False)
        
        if is_admin:
            role = 'admin'
        elif is_manager:
            role = 'manager'
        else:
            role = 'employee'
        
        # Generate JWT token
        token = jwt_utils.create_access_token(
            employee_id=employee['id'],
            name=employee['name'],
            is_admin=is_admin,
            is_manager=is_manager
        )
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "employee": {
                "id": employee['id'],
                "name": employee['name'],
                "employee_code": employee['employee_code'],
                "role": role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error verifying OTP: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify OTP")


async def process_message(correlation_id: str, payload: dict, session: str):
    """
    Background task to process incoming WhatsApp message
    """
    try:
        # Extract message_id early for use throughout processing
        message_id = payload.get('id') or (payload.get('_data', {}).get('id', {}).get('id'))
        
        # DEBUG: Log complete payload structure to understand WAHA format
        import json
        print(f'[{correlation_id}] 🔍 DEBUG: Full payload structure:')
        print(f'[{correlation_id}] {json.dumps(payload, indent=2, default=str)[:2000]}')
        
        print(f'[{correlation_id}] 🔍 DEBUG: Payload keys: {list(payload.keys())}')
        print(f'[{correlation_id}] 🔍 DEBUG: body={payload.get("body")}, text={payload.get("text")}, type={payload.get("type")}')
        print(f'[{correlation_id}] 🔍 DEBUG: message_id={message_id}, fromMe={payload.get("fromMe")}')
        
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

        # Extract chat ID - try multiple possible fields
        # WAHA may use different formats: phone@c.us, lid@lid, etc.
        chat_id = (
            payload.get('chatId') or 
            payload.get('chat_id') or 
            payload.get('from') or 
            payload.get('remoteJid') or
            payload.get('_data', {}).get('from') or
            payload.get('_data', {}).get('chatId')
        )
        
        # DEBUG: Log all potential phone number sources
        print(f'[{correlation_id}] 🔍 DEBUG: chatId={chat_id}')
        print(f'[{correlation_id}] 🔍 DEBUG: from={payload.get("from")}')
        print(f'[{correlation_id}] 🔍 DEBUG: _data.from={payload.get("_data", {}).get("from")}')
        print(f'[{correlation_id}] 🔍 DEBUG: notifyName={payload.get("notifyName")}')
        
        # Check for phone number in sender/participant fields (for LID format)
        sender = payload.get('sender') or payload.get('_data', {}).get('sender') or {}
        if isinstance(sender, dict):
            print(f'[{correlation_id}] 🔍 DEBUG: sender={sender}')
            # sender might contain: {id: "phone@c.us", pushname: "Name"}
            sender_id = sender.get('id') or sender.get('_serialized')
            if sender_id and '@c.us' in str(sender_id):
                print(f'[{correlation_id}] 📱 Found phone in sender: {sender_id}')
                chat_id = sender_id

        if not chat_id:
            print(f'[{correlation_id}] ⚠️ No chatId found in payload')
            return

        # Check for media attachments (image, document, pdf)
        has_media = payload.get('hasMedia') or payload.get('media') or (payload.get('_data') or {}).get('media')
        print(f'[{correlation_id}] 🔍 DEBUG: has_media={has_media}')
        
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

        # Extract message content
        message_text = payload.get('body') or (payload.get('_data') or {}).get('body') or ''
        
        # If user explicitly typed a caption, use that. 
        # CAREFUL: WAHA might put OCR text in body if configured to do so?
        # Assuming body is user caption or empty.

        # MEDIA HANDLING
        if has_media:
            print(f'[{correlation_id}] 📎 Processing media: type={media_type}, mime={mime_type}')
            try:
                extraction_result = None
                
                # Option 1: Use base64 data directly from payload
                if media_data:
                    print(f'[{correlation_id}] 📥 Using base64 media data from payload')
                    import base64
                    image_buffer = base64.b64decode(media_data)
                    print(f'[{correlation_id}] 🔄 Calling Textract...')
                    extraction_result = await textract_service.extract_text_from_image(image_buffer)
                    print(f'[{correlation_id}] ✅ Textract complete')

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
                
                else:
                    print(f'[{correlation_id}] ⚠️ No media data/url/filename found')

                if extraction_result and extraction_result.get('success') and extraction_result.get('text'):
                    print(f'[{correlation_id}] 📄 Extracted text (len={len(extraction_result["text"])})')

                    # Use OpenAI to intelligently parse the receipt text
                    from app.services import openai_service
                    ai_result = await openai_service.parse_receipt_text(extraction_result['text'])
                    
                    extracted_amount = None
                    extracted_vendor = None
                    extracted_date = None
                    
                    if ai_result.get('success'):
                        extracted_amount = ai_result.get('total_amount')
                        extracted_vendor = ai_result.get('vendor_name')
                        extracted_date = ai_result.get('date')
                        print(f'[{correlation_id}] 🤖 OpenAI parsed: Amount={extracted_amount}, Vendor={extracted_vendor}, Date={extracted_date}')
                    else:
                        # Fallback to regex extraction
                        print(f'[{correlation_id}] ⚠️ OpenAI parsing failed/skipped, using regex fallback')
                        extracted_amount = textract_service.extract_amount_from_text(extraction_result['text'])

                    if extracted_amount:
                        print(f'[{correlation_id}] 💰 Final detected amount: Rs.{extracted_amount}')

                    # Add parsed data to message for processing
                    details_text = ""
                    if extracted_amount:
                        details_text += f"\nDetected amount: Rs.{extracted_amount}"
                    if extracted_vendor:
                        details_text += f"\nVendor: {extracted_vendor}"
                    if extracted_date:
                        details_text += f"\nDate: {extracted_date}"
                        
                    message_text = f"[RECEIPT/DOCUMENT UPLOADED]\nExtracted text: {extraction_result['text']}{details_text}"
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

        # Only skip if BOTH no text AND no media
        if not message_text and not has_media:
            # Debug: Log payload structure to help diagnose empty message issues
            print(f'[{correlation_id}] 🔍 DEBUG: Empty message, payload keys: {list(payload.keys())}')
            if payload.get('_data'):
                print(f'[{correlation_id}] 🔍 DEBUG: _data keys: {list(payload.get("_data", {}).keys())}')
            print(f'[{correlation_id}] ⏭️ Empty message body and no media, skipping')
            return
        
        # If has media but no text, set a placeholder message
        if not message_text and has_media:
            message_text = "[MEDIA_UPLOADED]"
            print(f'[{correlation_id}] 📎 Media uploaded without caption, will process media')

        display_text = message_text[:100] + '...' if len(message_text) > 100 else message_text
        print(f'[{correlation_id}] 💬 Message from {chat_id}: "{display_text}"')

        # Build media_info dict for forwarding to manager
        current_media_info = None
        if has_media and (media_data or media_url):
            current_media_info = {
                'url': media_url,
                'data': media_data,
                'mimetype': mime_type,
                'filename': media_filename,
                'message_id': message_id
            }
            print(f'[{correlation_id}] 📎 Media info prepared for forwarding')

        # Generate reply using replyEngine (pass media_info for forwarding)
        reply_text = await reply_engine.generate_reply(message_text, chat_id, current_media_info)

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
    print(f'📡 API endpoints: /api/claims, /api/stats')
    print(f'🏥 Health check: GET /health')


# =============================================
# CLAIMS MANAGEMENT API ENDPOINTS
# =============================================

@app.get("/api/claims")
async def get_claims(
    status: Optional[str] = Query(None, description="Filter by status: PENDING, APPROVED, REJECTED"),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    manager_id: Optional[int] = Query(None, description="Filter by manager ID"),
    appealed: Optional[bool] = Query(None, description="Filter by claims that went through appeal process"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Get list of claims with optional filters
    """
    try:
        from app.db import db
        
        # Build query based on filters
        query = """
            SELECT c.*, e.name as employee_name, e.employee_code, e.phone_number,
                   g.code as grade_code, cat.code as category_code, cat.name as category_name,
                   l.name as location_name, s.code as status_code, s.name as status_name,
                   m.name as manager_name, a.name as approver_name
            FROM claims c
            JOIN employees e ON c.employee_id = e.id
            LEFT JOIN grades g ON e.grade_id = g.id
            JOIN claim_categories cat ON c.category_id = cat.id
            LEFT JOIN locations l ON c.location_id = l.id
            JOIN claim_statuses s ON c.status_id = s.id
            LEFT JOIN employees m ON c.manager_id = m.id
            LEFT JOIN employees a ON c.approved_by = a.id
            WHERE 1=1
        """
        params = []
        param_index = 1
        
        # DEBUG: Print filters
        print(f"🔍 get_claims filters: employee_id={employee_id}, status={status}, user_role={role if 'role' in locals() else 'unknown'}")

        if status:
            query += f" AND s.code = ${param_index}"
            params.append(status.upper())
            param_index += 1
        
        # Filter by claims that went through appeal process
        if appealed is True:
            query += " AND COALESCE(c.appeal_count, 0) > 0"
        elif appealed is False:
            query += " AND COALESCE(c.appeal_count, 0) = 0"
            
        if employee_id:
            query += f" AND c.employee_id = ${param_index}"
            params.append(employee_id)
            param_index += 1
            
        if manager_id:
            query += f" AND c.manager_id = ${param_index}"
            params.append(manager_id)
            param_index += 1
        
        query += f" ORDER BY c.created_at DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.extend([limit, offset])
        
        claims = await db.query(query, *params)
        
        # Get total count for pagination
        count_query = "SELECT COUNT(*) as total FROM claims c JOIN claim_statuses s ON c.status_id = s.id WHERE 1=1"
        count_params = []
        param_index = 1
        
        if status:
            count_query += f" AND s.code = ${param_index}"
            count_params.append(status.upper())
            param_index += 1
        if employee_id:
            count_query += f" AND c.employee_id = ${param_index}"
            count_params.append(employee_id)
            param_index += 1
        if manager_id:
            count_query += f" AND c.manager_id = ${param_index}"
            count_params.append(manager_id)
            
        count_result = await db.query(count_query, *count_params)
        total = count_result[0]['total'] if count_result else 0
        
        return {
            "claims": claims,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        print(f"❌ Error fetching claims: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/claims/{claim_id}")
async def get_claim(claim_id: int):
    """
    Get a single claim by ID with full details
    """
    try:
        claim = await claim_model.find_by_id(claim_id)
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        return claim
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching claim {claim_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/claims/{claim_id}/approve")
async def approve_claim(claim_id: int, request: ApproveClaimRequest = None):
    """
    Approve a claim and notify the staff via WhatsApp
    """
    try:
        # Get claim first
        claim = await claim_model.find_by_id(claim_id)
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        current_status = claim.get('status_code')
        if current_status not in ('PENDING', 'APPEALED'):
            raise HTTPException(status_code=400, detail=f"Claim is already {claim.get('status_name')}")
        
        # Approve the claim (using manager_id as approver for now)
        final_amount = request.final_amount if request else None
        approver_id = claim.get('manager_id') or claim.get('employee_id')
        
        # Record status change in history
        await claim_model.record_status_change(
            claim_id, current_status, 'APPROVED', approver_id, 'Approved by manager'
        )
        
        updated_claim = await claim_model.approve(claim_id, approver_id, final_amount)
        
        # Notify staff via WhatsApp
        await notification_service.notify_staff_of_approval(updated_claim)
        
        # Fetch updated claim with full details
        full_claim = await claim_model.find_by_id(claim_id)
        
        return {
            "success": True,
            "message": "Claim approved successfully",
            "claim": full_claim
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error approving claim {claim_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/claims/{claim_id}/reject")
async def reject_claim(claim_id: int, request: RejectClaimRequest):
    """
    Reject a claim with a reason and notify the staff via WhatsApp
    """
    try:
        # Get claim first
        claim = await claim_model.find_by_id(claim_id)
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        current_status = claim.get('status_code')
        if current_status not in ('PENDING', 'APPEALED'):
            raise HTTPException(status_code=400, detail=f"Claim is already {claim.get('status_name')}")
        
        if not request.reason or len(request.reason.strip()) < 3:
            raise HTTPException(status_code=400, detail="Rejection reason is required (minimum 3 characters)")
        
        # Reject the claim
        approver_id = claim.get('manager_id') or claim.get('employee_id')
        
        # Record status change in history
        await claim_model.record_status_change(
            claim_id, current_status, 'REJECTED', approver_id, request.reason.strip()
        )
        
        updated_claim = await claim_model.reject(claim_id, approver_id, request.reason.strip())
        
        # Notify staff via WhatsApp
        await notification_service.notify_staff_of_rejection(updated_claim, request.reason.strip())
        
        # Fetch updated claim with full details
        full_claim = await claim_model.find_by_id(claim_id)
        
        return {
            "success": True,
            "message": "Claim rejected",
            "claim": full_claim
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error rejecting claim {claim_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/claims/{claim_id}/history")
async def get_claim_history(claim_id: int):
    """
    Get status change history for a claim
    """
    try:
        claim = await claim_model.find_by_id(claim_id)
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        history = await claim_model.get_history(claim_id)
        
        return {
            "claim_id": claim_id,
            "claim_number": claim.get('claim_number'),
            "current_status": claim.get('status_code'),
            "appeal_count": claim.get('appeal_count', 0),
            "history": history
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching claim history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """
    Get dashboard statistics for claims
    """
    try:
        from app.db import db
        
        # Overall stats
        stats_query = """
            SELECT 
                COUNT(*) as total_claims,
                COUNT(*) FILTER (WHERE s.code = 'PENDING') as pending_claims,
                COUNT(*) FILTER (WHERE s.code = 'APPROVED') as approved_claims,
                COUNT(*) FILTER (WHERE s.code = 'REJECTED') as rejected_claims,
                COALESCE(SUM(c.final_amount) FILTER (WHERE s.code = 'APPROVED'), 0) as total_approved_amount,
                COALESCE(SUM(c.user_amount) FILTER (WHERE s.code = 'PENDING'), 0) as pending_amount
            FROM claims c
            JOIN claim_statuses s ON c.status_id = s.id
        """
        stats = await db.query(stats_query)
        
        # Category breakdown
        category_query = """
            SELECT cat.name as category, cat.code as category_code,
                   COUNT(*) as count,
                   COALESCE(SUM(c.final_amount), 0) as total_amount
            FROM claims c
            JOIN claim_categories cat ON c.category_id = cat.id
            JOIN claim_statuses s ON c.status_id = s.id
            WHERE s.code = 'APPROVED'
            GROUP BY cat.id, cat.name, cat.code
            ORDER BY total_amount DESC
        """
        categories = await db.query(category_query)
        
        # Recent claims (last 5)
        recent_query = """
            SELECT c.claim_number, c.created_at, e.name as employee_name,
                   cat.name as category_name, c.final_amount, s.code as status_code
            FROM claims c
            JOIN employees e ON c.employee_id = e.id
            JOIN claim_categories cat ON c.category_id = cat.id
            JOIN claim_statuses s ON c.status_id = s.id
            ORDER BY c.created_at DESC
            LIMIT 5
        """
        recent = await db.query(recent_query)
        
        return {
            "overview": stats[0] if stats else {},
            "categories": categories,
            "recent_claims": recent
        }
        
    except Exception as e:
        print(f"❌ Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/employees")
async def get_employees(
    role: Optional[str] = Query(None),
    location_id: Optional[int] = Query(None),
    include_inactive: bool = Query(False)
):
    """
    Get list of employees with optional filters
    """
    try:
        employees = await employee_model.find_all_with_details(
            role=role, 
            location_id=location_id, 
            include_inactive=include_inactive
        )
        return {"employees": employees, "total": len(employees)}
    except Exception as e:
        print(f"❌ Error fetching employees: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/employees/{employee_id}")
async def get_employee(employee_id: int):
    """
    Get a single employee by ID
    """
    try:
        employee = await employee_model.find_by_id(employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        return employee
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching employee {employee_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CreateEmployeeRequest(BaseModel):
    employee_code: Optional[str] = None  # Auto-generated if not provided
    name: str
    phone_number: str
    email: Optional[str] = None
    grade_id: Optional[int] = None
    unit_id: Optional[int] = None
    location_id: Optional[int] = None
    manager_id: Optional[int] = None
    role: str = "staff"
    is_admin: bool = False
    is_manager: bool = False


@app.post("/api/employees")
async def create_employee(request: CreateEmployeeRequest):
    """
    Create a new employee
    """
    try:
        # Sync role flags based on role string
        if request.role == 'admin':
            request.is_admin = True
            request.is_manager = False
        elif request.role == 'manager':
            request.is_manager = True
            request.is_admin = False
        else:
            request.is_admin = False
            request.is_manager = False

        employee = await employee_model.create(request.model_dump())
        return {
            "success": True,
            "message": "Employee created successfully",
            "employee": employee
        }
    except Exception as e:
        print(f"❌ Error creating employee: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class UpdateEmployeeRequest(BaseModel):
    employee_code: Optional[str] = None
    name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    grade_id: Optional[int] = None
    unit_id: Optional[int] = None
    location_id: Optional[int] = None
    manager_id: Optional[int] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_manager: Optional[bool] = None


@app.put("/api/employees/{employee_id}")
async def update_employee(employee_id: int, request: UpdateEmployeeRequest):
    """
    Update an employee
    """
    try:
        existing = await employee_model.find_by_id(employee_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Sync role flags if role is being updated
        update_data = request.model_dump(exclude_unset=True)
        if 'role' in update_data:
            role = update_data['role']
            if role == 'admin':
                update_data['is_admin'] = True
                update_data['is_manager'] = False
            elif role == 'manager':
                update_data['is_manager'] = True
                update_data['is_admin'] = False
            else:
                update_data['is_admin'] = False
                update_data['is_manager'] = False
        
        employee = await employee_model.update(employee_id, update_data)
        if not employee:
            raise HTTPException(status_code=500, detail="Failed to update employee")
        
        return {
            "success": True,
            "message": "Employee updated successfully",
            "employee": employee
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating employee {employee_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/employees/{employee_id}")
async def delete_employee(employee_id: int, permanent: bool = Query(False)):
    """
    Delete an employee (soft delete by default, permanent if specified)
    """
    try:
        existing = await employee_model.find_by_id(employee_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        if permanent:
            success = await employee_model.hard_delete(employee_id)
        else:
            success = await employee_model.delete(employee_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete employee")
        
        return {
            "success": True,
            "message": "Employee deleted permanently" if permanent else "Employee deactivated",
            "id": employee_id
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting employee {employee_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/employees/cleanup/inactive")
async def delete_inactive_employees():
    """
    Delete all inactive employees from the database permanently
    """
    try:
        from app.db import db
        
        # First get the list of inactive employees
        inactive = await db.query("SELECT id, name FROM employees WHERE is_active = FALSE")
        
        if not inactive:
            return {
                "success": True,
                "message": "No inactive employees found",
                "deleted_count": 0,
                "deleted_employees": []
            }
        
        # Delete all inactive employees
        await db.execute("DELETE FROM employees WHERE is_active = FALSE")
        
        deleted_names = [e['name'] for e in inactive]
        print(f"🗑️ Deleted {len(inactive)} inactive employees: {deleted_names}")
        
        return {
            "success": True,
            "message": f"Deleted {len(inactive)} inactive employees",
            "deleted_count": len(inactive),
            "deleted_employees": deleted_names
        }
    except Exception as e:
        print(f"❌ Error deleting inactive employees: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/claims/{claim_id}")
async def delete_claim(claim_id: int):
    """
    Delete a claim and its related data
    """
    try:
        existing = await claim_model.find_by_id(claim_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        success = await claim_model.delete(claim_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete claim")
        
        return {
            "success": True,
            "message": "Claim deleted successfully",
            "id": claim_id,
            "claim_number": existing.get('claim_number')
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting claim {claim_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper endpoints for form dropdowns
@app.get("/api/grades")
async def get_grades():
    """Get all grades for dropdowns"""
    try:
        from app.db import db
        grades = await db.query("SELECT * FROM grades ORDER BY code")
        return {"grades": grades}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/locations")
async def get_locations():
    """Get all locations for dropdowns"""
    try:
        from app.db import db
        locations = await db.query("SELECT * FROM locations WHERE is_active = TRUE ORDER BY name")
        return {"locations": locations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/units")
async def get_units():
    """Get all units for dropdowns"""
    try:
        from app.db import db
        units = await db.query("SELECT * FROM units ORDER BY name")
        return {"units": units}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', '4101'))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

