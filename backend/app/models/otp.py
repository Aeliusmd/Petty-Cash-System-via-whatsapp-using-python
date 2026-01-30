"""
OTP Model
OOP class for OTP generation, storage, and verification
"""

import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.models.base import BaseModel
from app.db.database import db


class OTP(BaseModel):
    """
    OTP model with database operations.
    Handles OTP generation and verification for authentication.
    """
    
    table_name = "otp_codes"
    
    # Instance attributes
    id: int = None
    phone_number: str = None
    code: str = None
    expires_at: datetime = None
    created_at: datetime = None
    
    def __init__(self, data: Dict[str, Any] = None):
        """Initialize OTP from data dict"""
        super().__init__(data)
    
    @classmethod
    async def generate(cls, phone_number: str, expiry_minutes: int = 5) -> 'OTP':
        """
        Generate a new 6-digit OTP code for a phone number.
        Deletes any existing OTP for this number first.
        
        Args:
            phone_number: The phone number to generate OTP for
            expiry_minutes: OTP validity in minutes (default 5)
            
        Returns:
            OTP instance with the generated code
        """
        otp_code = ''.join(random.choices(string.digits, k=6))
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        # Delete existing OTP for this phone
        await db.execute("DELETE FROM otp_codes WHERE phone_number = $1", phone_number)
        
        # Create new OTP
        await db.execute("""
            INSERT INTO otp_codes (phone_number, code, expires_at, created_at)
            VALUES ($1, $2, $3, $4)
        """, phone_number, otp_code, expires_at, datetime.utcnow())
        
        return cls({
            'phone_number': phone_number,
            'code': otp_code,
            'expires_at': expires_at
        })
    
    @classmethod
    async def verify(cls, phone_number: str, otp_code: str) -> bool:
        """
        Verify if the OTP code is valid for the phone number.
        Deletes the OTP after successful verification (one-time use).
        
        Args:
            phone_number: The phone number
            otp_code: The OTP code to verify
            
        Returns:
            True if valid and not expired, False otherwise
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
            # Delete after successful verification
            await db.execute("DELETE FROM otp_codes WHERE phone_number = $1", phone_number)
            return True
        
        return False
    
    @classmethod
    async def check_rate_limit(
        cls,
        phone_number: str,
        max_attempts: int = 3,
        window_minutes: int = 60
    ) -> bool:
        """
        Check if phone number has exceeded rate limit for OTP requests.
        
        Args:
            phone_number: Phone number to check
            max_attempts: Maximum attempts allowed
            window_minutes: Time window in minutes
            
        Returns:
            True if rate limit exceeded, False if OK to proceed
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
        
        result = await db.query("""
            SELECT COUNT(*) as attempt_count FROM otp_codes
            WHERE phone_number = $1 AND created_at > $2
        """, phone_number, cutoff_time)
        
        attempt_count = result[0]['attempt_count'] if result else 0
        return attempt_count >= max_attempts
    
    @classmethod
    async def cleanup_expired(cls) -> int:
        """Delete all expired OTP codes"""
        result = await db.execute("""
            DELETE FROM otp_codes WHERE expires_at < CURRENT_TIMESTAMP
        """)
        if result and 'DELETE' in result:
            try:
                return int(result.split(' ')[1])
            except:
                return 0
        return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert OTP to dictionary"""
        return {
            'id': self.id,
            'phone_number': self.phone_number,
            'code': self.code,
            'expires_at': self.expires_at
        }


# Backward compatibility - expose class methods as module functions
async def generate_otp(phone_number: str):
    otp = await OTP.generate(phone_number)
    return otp.code

async def verify_otp(phone_number: str, otp_code: str):
    return await OTP.verify(phone_number, otp_code)

async def check_rate_limit(phone_number: str, max_attempts: int = 3, window_minutes: int = 60):
    return await OTP.check_rate_limit(phone_number, max_attempts, window_minutes)
