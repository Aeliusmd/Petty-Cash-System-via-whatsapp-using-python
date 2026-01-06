"""
OTP (One-Time Password) Model
Handles OTP generation, storage, and verification for employee authentication
"""

import random
import string
from datetime import datetime, timedelta
from typing import Optional
from app.db.database import db


async def generate_otp(phone_number: str) -> str:
    """
    Generate a 6-digit OTP code for the given phone number
    
    Args:
        phone_number: The employee's phone number
        
    Returns:
        The generated 6-digit OTP code
    """
    # Generate random 6-digit code
    otp_code = ''.join(random.choices(string.digits, k=6))
    
    # Set expiration to 5 minutes from now
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    
    # Delete any existing OTP for this phone number
    await db.execute("""
        DELETE FROM otp_codes WHERE phone_number = $1
    """, phone_number)
    
    # Store new OTP
    await db.execute("""
        INSERT INTO otp_codes (phone_number, code, expires_at, created_at)
        VALUES ($1, $2, $3, $4)
    """, phone_number, otp_code, expires_at, datetime.utcnow())
    
    return otp_code


async def verify_otp(phone_number: str, otp_code: str) -> bool:
    """
    Verify if the OTP code is valid for the given phone number
    
    Args:
        phone_number: The employee's phone number
        otp_code: The OTP code to verify
        
    Returns:
        True if OTP is valid and not expired, False otherwise
    """
    result = await db.query("""
        SELECT code, expires_at FROM otp_codes
        WHERE phone_number = $1
        ORDER BY created_at DESC
        LIMIT 1
    """, phone_number)
    
    if not result:
        return False
    
    stored_code = result[0]['code']
    expires_at = result[0]['expires_at']
    
    # Check if OTP matches and hasn't expired
    if stored_code == otp_code and datetime.utcnow() < expires_at:
        # Delete the OTP after successful verification (one-time use)
        await db.execute("""
            DELETE FROM otp_codes WHERE phone_number = $1
        """, phone_number)
        return True
    
    return False


async def check_rate_limit(phone_number: str, max_attempts: int = 3, window_minutes: int = 60) -> bool:
    """
    Check if the phone number has exceeded the rate limit for OTP requests
    
    Args:
        phone_number: The employee's phone number
        max_attempts: Maximum attempts allowed within the time window
        window_minutes: Time window in minutes
        
    Returns:
        True if rate limit is exceeded, False otherwise
    """
    cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
    
    result = await db.query("""
        SELECT COUNT(*) as attempt_count FROM otp_codes
        WHERE phone_number = $1 AND created_at > $2
    """, phone_number, cutoff_time)
    
    attempt_count = result[0]['attempt_count'] if result else 0
    
    return attempt_count >= max_attempts
