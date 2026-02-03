"""
Authentication Schemas
Pydantic models for auth-related endpoints
"""

from pydantic import BaseModel
from typing import Optional


class RequestOTPRequest(BaseModel):
    """Request for sending OTP"""
    phone_number: str


class VerifyOTPRequest(BaseModel):
    """Request for verifying OTP"""
    phone_number: str
    otp_code: str


class LoginResponse(BaseModel):
    """Response after successful login"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    employee: dict


class RefreshTokenRequest(BaseModel):
    """Request for refreshing access token"""
    refresh_token: str


class TokenPayload(BaseModel):
    """JWT token payload"""
    employee_id: int
    name: str
    role: str
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    exp: Optional[int] = None
