"""
Common Schemas
Shared Pydantic models used across multiple endpoints
"""

from pydantic import BaseModel
from typing import Optional, Any


class MessageResponse(BaseModel):
    """Standard message response"""
    message: str


class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    message: str = "Success"
    data: Optional[Any] = None


class PaginatedResponse(BaseModel):
    """Standard paginated response"""
    total: int
    limit: int
    offset: int
    has_more: bool = False


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    message: str
    code: Optional[int] = None
