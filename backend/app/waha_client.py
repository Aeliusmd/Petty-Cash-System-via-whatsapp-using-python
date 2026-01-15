"""
WAHA API Client
Handles all communication with WAHA WhatsApp HTTP API
"""

import httpx
import os
from typing import Optional


WAHA_BASE_URL = os.getenv('WAHA_BASE_URL', 'http://waha:3000')
WAHA_SESSION = os.getenv('WAHA_SESSION', 'default')
WAHA_API_KEY = os.getenv('WAHA_API_KEY', '')


def _get_headers() -> dict:
    """Get common headers for WAHA API"""
    headers = {'Content-Type': 'application/json'}
    if WAHA_API_KEY:
        headers['X-Api-Key'] = WAHA_API_KEY
    return headers


async def send_text(chat_id: str, text: str) -> dict:
    """
    Send a text message to a chat
    
    Args:
        chat_id: The chat ID (e.g., "1234567890@c.us")
        text: The message text to send
        
    Returns:
        WAHA API response
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{WAHA_BASE_URL}/api/sendText',
                json={
                    'session': WAHA_SESSION,
                    'chatId': chat_id,
                    'text': text
                },
                headers=_get_headers()
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f'❌ WAHA sendText error: {e}')
        raise


async def start_typing(chat_id: str) -> Optional[dict]:
    """
    Start typing indicator in a chat
    
    Args:
        chat_id: The chat ID
        
    Returns:
        WAHA API response
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f'{WAHA_BASE_URL}/api/startTyping',
                json={
                    'session': WAHA_SESSION,
                    'chatId': chat_id
                },
                headers=_get_headers()
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        # Typing indicator is optional, don't raise
        print(f'⚠️ WAHA startTyping failed: {e}')
        return None


async def stop_typing(chat_id: str) -> Optional[dict]:
    """
    Stop typing indicator in a chat
    
    Args:
        chat_id: The chat ID
        
    Returns:
        WAHA API response
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f'{WAHA_BASE_URL}/api/stopTyping',
                json={
                    'session': WAHA_SESSION,
                    'chatId': chat_id
                },
                headers=_get_headers()
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        # Stop typing is optional, don't raise
        print(f'⚠️ WAHA stopTyping failed: {e}')
        return None


async def get_session_status() -> dict:
    """
    Get session status
    
    Returns:
        Session status
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f'{WAHA_BASE_URL}/api/sessions/{WAHA_SESSION}',
                headers=_get_headers()
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f'❌ WAHA getSessionStatus error: {e}')
        raise


async def configure_session_store() -> Optional[dict]:
    """
    Configure or update the WAHA session with NOWEB store enabled.
    This must be called to enable LID resolution with NOWEB engine.
    
    IMPORTANT: This will DELETE and RECREATE the session, requiring QR code re-scan.
    
    Returns:
        Session configuration or None if failed
    """
    try:
        session_config = {
            "name": WAHA_SESSION,
            "config": {
                "noweb": {
                    "store": {
                        "enabled": True,
                        "fullSync": True  # Get more message history
                    }
                }
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Check if session exists
            try:
                response = await client.get(
                    f'{WAHA_BASE_URL}/api/sessions/{WAHA_SESSION}',
                    headers=_get_headers()
                )
                session_exists = response.status_code == 200
                
                if session_exists:
                    session_data = response.json()
                    # Check if store is already enabled
                    store_config = session_data.get('config', {}).get('noweb', {}).get('store', {})
                    if store_config.get('enabled') == True:
                        print(f'✅ Session "{WAHA_SESSION}" already has NOWEB store enabled')
                        return session_data
                    
                    # Store not enabled - need to delete and recreate
                    print(f'⚠️ Session "{WAHA_SESSION}" exists without store - deleting to recreate...')
                    delete_response = await client.delete(
                        f'{WAHA_BASE_URL}/api/sessions/{WAHA_SESSION}',
                        headers=_get_headers()
                    )
                    delete_response.raise_for_status()
                    print(f'✅ Deleted session "{WAHA_SESSION}"')
            except httpx.HTTPStatusError:
                # Session doesn't exist, that's fine
                pass
            
            # Create new session with store enabled
            response = await client.post(
                f'{WAHA_BASE_URL}/api/sessions/',
                json=session_config,
                headers=_get_headers()
            )
            response.raise_for_status()
            print(f'✅ Created session "{WAHA_SESSION}" with NOWEB store enabled')
            print(f'📱 Please scan the QR code to authenticate WhatsApp')
            return response.json()
            
    except Exception as e:
        print(f'⚠️ WAHA configure_session_store failed: {e}')
        return None


async def get_lid_info(lid: str) -> Optional[dict]:
    """
    Get LID info to resolve to phone number
    
    Args:
        lid: The Linked ID (e.g. 12345@lid)
        
    Returns:
        Dict with 'lid' and 'pn' (phone number) or None if failed
    """
    try:
        # URL encode the LID (replace @ with %40)
        encoded_lid = lid.replace('@', '%40')
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f'{WAHA_BASE_URL}/api/{WAHA_SESSION}/lids/{encoded_lid}',
                headers=_get_headers()
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f'⚠️ WAHA get_lid_info failed for {lid}: {e}')
        return None


async def sync_contacts() -> Optional[list]:
    """
    Sync contacts to populate LID-to-phone mapping in WAHA's SQLite store.
    Call this once after WAHA starts to ensure LID resolution works.
    
    Returns:
        List of contacts or None if failed
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f'{WAHA_BASE_URL}/api/contacts?session={WAHA_SESSION}',
                headers=_get_headers()
            )
            response.raise_for_status()
            contacts = response.json()
            print(f'✅ Synced {len(contacts)} contacts for LID resolution')
            return contacts
    except Exception as e:
        print(f'⚠️ WAHA sync_contacts failed: {e}')
        return None


async def send_image(chat_id: str, image_url: str = None, image_base64: str = None, 
                     caption: str = None, mimetype: str = 'image/jpeg') -> Optional[dict]:
    """
    Send an image to a chat
    
    Args:
        chat_id: The chat ID
        image_url: URL of the image (use this OR image_base64)
        image_base64: Base64 encoded image data
        caption: Optional caption for the image
        mimetype: MIME type of the image
        
    Returns:
        WAHA API response or None if failed
    """
    try:
        payload = {
            'session': WAHA_SESSION,
            'chatId': chat_id
        }
        
        if image_url:
            payload['file'] = {'url': image_url}
        elif image_base64:
            payload['file'] = {'data': image_base64, 'mimetype': mimetype}
        else:
            print('❌ send_image: No image URL or base64 provided')
            return None
        
        if caption:
            payload['caption'] = caption
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f'{WAHA_BASE_URL}/api/sendImage',
                json=payload,
                headers=_get_headers()
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f'❌ WAHA sendImage error: {e}')
        return None


async def send_file(chat_id: str, file_url: str = None, file_base64: str = None,
                    filename: str = 'document.pdf', caption: str = None,
                    mimetype: str = 'application/pdf') -> Optional[dict]:
    """
    Send a file/document to a chat
    
    Args:
        chat_id: The chat ID
        file_url: URL of the file (use this OR file_base64)
        file_base64: Base64 encoded file data
        filename: Name of the file
        caption: Optional caption
        mimetype: MIME type of the file
        
    Returns:
        WAHA API response or None if failed
    """
    try:
        payload = {
            'session': WAHA_SESSION,
            'chatId': chat_id
        }
        
        if file_url:
            payload['file'] = {'url': file_url, 'filename': filename}
        elif file_base64:
            payload['file'] = {'data': file_base64, 'filename': filename, 'mimetype': mimetype}
        else:
            print('❌ send_file: No file URL or base64 provided')
            return None
        
        if caption:
            payload['caption'] = caption
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f'{WAHA_BASE_URL}/api/sendFile',
                json=payload,
                headers=_get_headers()
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f'❌ WAHA sendFile error: {e}')
        return None


async def send_media(chat_id: str, media_info: dict, caption: str = None) -> Optional[dict]:
    """
    Send media (image or file) based on media_info dict
    
    Args:
        chat_id: The chat ID
        media_info: Dict with 'url', 'data', 'mimetype', 'filename'
        caption: Optional caption
        
    Returns:
        WAHA API response or None if failed
    """
    if not media_info:
        return None
    
    mimetype = media_info.get('mimetype', '')
    is_image = 'image' in mimetype
    
    if is_image:
        return await send_image(
            chat_id,
            image_url=media_info.get('url'),
            image_base64=media_info.get('data'),
            caption=caption,
            mimetype=mimetype
        )
    else:
        return await send_file(
            chat_id,
            file_url=media_info.get('url'),
            file_base64=media_info.get('data'),
            filename=media_info.get('filename', 'document'),
            caption=caption,
            mimetype=mimetype
        )


async def forward_message(chat_id: str, message_id: str) -> Optional[dict]:
    """
    Forward a WhatsApp message to another chat
    
    Args:
        chat_id: The destination chat ID
        message_id: The message ID to forward
        
    Returns:
        WAHA API response or None if failed
    """
    try:
        payload = {
            'session': WAHA_SESSION,
            'chatId': chat_id,
            'messageId': message_id
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f'{WAHA_BASE_URL}/api/forwardMessage',
                json=payload,
                headers=_get_headers()
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f'❌ WAHA forwardMessage error: {e}')
        return None


<<<<<<< HEAD
async def configure_session_store() -> Optional[dict]:
    """
    Configure or update the WAHA session with NOWEB store enabled.
    This must be called to enable LID resolution with NOWEB engine.
    
    IMPORTANT: This will DELETE and RECREATE the session, requiring QR code re-scan.
    
    Returns:
        Session configuration or None if failed
    """
    try:
        session_config = {
            "name": WAHA_SESSION,
            "config": {
                "noweb": {
                    "store": {
                        "enabled": True,
                        "fullSync": True  # Get more message history
                    }
                }
=======
async def send_poll(chat_id: str, question: str, options: list, 
                    multiple_answers: bool = False) -> Optional[dict]:
    """
    Send a poll to a WhatsApp chat
    
    Polls are more reliable than clickable buttons and work 100% of the time.
    Use multipleAnswers=False to force single selection (radio button behavior).
    
    Args:
        chat_id: The chat ID (e.g., "1234567890@c.us")
        question: The poll question/title
        options: List of option strings (max 12 options)
        multiple_answers: If False, user can only pick one option
        
    Returns:
        WAHA API response or None if failed
    """
    try:
        # Limit options to 12 (WhatsApp limit)
        if len(options) > 12:
            print(f'⚠️ Poll has {len(options)} options, truncating to 12')
            options = options[:12]
        
        payload = {
            'session': WAHA_SESSION,
            'chatId': chat_id,
            'poll': {
                'name': question,
                'options': options,
                'multipleAnswers': multiple_answers
>>>>>>> aacf1863e4ef6646015f74e4c5ec2a4032cc330f
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
<<<<<<< HEAD
            # Check if session exists
            try:
                response = await client.get(
                    f'{WAHA_BASE_URL}/api/sessions/{WAHA_SESSION}',
                    headers=_get_headers()
                )
                session_exists = response.status_code == 200
                
                if session_exists:
                    session_data = response.json()
                    # Check if store is already enabled
                    store_config = session_data.get('config', {}).get('noweb', {}).get('store', {})
                    if store_config.get('enabled') == True:
                        print(f'✅ Session "{WAHA_SESSION}" already has NOWEB store enabled')
                        return session_data
                    
                    # Store not enabled - need to delete and recreate
                    print(f'⚠️ Session "{WAHA_SESSION}" exists without store - deleting to recreate...')
                    delete_response = await client.delete(
                        f'{WAHA_BASE_URL}/api/sessions/{WAHA_SESSION}',
                        headers=_get_headers()
                    )
                    delete_response.raise_for_status()
                    print(f'✅ Deleted session "{WAHA_SESSION}"')
            except httpx.HTTPStatusError:
                # Session doesn't exist, that's fine
                pass
            
            # Create new session with store enabled
            response = await client.post(
                f'{WAHA_BASE_URL}/api/sessions/',
                json=session_config,
                headers=_get_headers()
            )
            response.raise_for_status()
            print(f'✅ Created session "{WAHA_SESSION}" with NOWEB store enabled')
            print(f'📱 Please scan the QR code to authenticate WhatsApp')
            return response.json()
            
    except Exception as e:
        print(f'⚠️ WAHA configure_session_store failed: {e}')
        return None


async def sync_contacts() -> Optional[list]:
    """
    Sync contacts to populate LID-to-phone mapping in WAHA's SQLite store.
    Call this once after WAHA starts to ensure LID resolution works.
    
    Returns:
        List of contacts or None if failed
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f'{WAHA_BASE_URL}/api/contacts?session={WAHA_SESSION}',
                headers=_get_headers()
            )
            response.raise_for_status()
            contacts = response.json()
            print(f'✅ Synced {len(contacts)} contacts for LID resolution')
            return contacts
    except Exception as e:
        print(f'⚠️ WAHA sync_contacts failed: {e}')
=======
            response = await client.post(
                f'{WAHA_BASE_URL}/api/sendPoll',
                json=payload,
                headers=_get_headers()
            )
            response.raise_for_status()
            print(f'✅ Poll sent to {chat_id}: "{question}" with {len(options)} options')
            return response.json()
    except Exception as e:
        print(f'❌ WAHA sendPoll error: {e}')
>>>>>>> aacf1863e4ef6646015f74e4c5ec2a4032cc330f
        return None
