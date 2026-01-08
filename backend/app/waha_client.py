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
