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
