"""
Claim Schemas
Pydantic models for claim-related endpoints
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class ClaimBase(BaseModel):
    """Base claim fields"""
    category_id: int
    location_id: Optional[int] = None
    claim_type: str = "outright"
    claim_date: Optional[date] = None
    duration_days: int = 1
    user_amount: Optional[float] = None
    system_amount: Optional[float] = None
    description: Optional[str] = None


class ClaimCreate(ClaimBase):
    """Request for creating a claim"""
    employee_id: Optional[int] = None  # Can be set from auth context
    manager_id: Optional[int] = None


class ClaimUpdate(BaseModel):
    """Request for updating a claim"""
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    claim_type: Optional[str] = None
    duration_days: Optional[int] = None
    user_amount: Optional[float] = None
    description: Optional[str] = None


class ClaimApproveRequest(BaseModel):
    """Request for approving a claim"""
    final_amount: Optional[float] = None


class ClaimRejectRequest(BaseModel):
    """Request for rejecting a claim"""
    reason: str


class ClaimAppealRequest(BaseModel):
    """Request for appealing a rejected claim"""
    notes: Optional[str] = None


class ReceiptInfo(BaseModel):
    """Receipt/attachment information"""
    id: int
    file_path: str
    file_name: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    ocr_amount: Optional[float] = None
    ocr_raw_text: Optional[str] = None
    vendor: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    message_id: Optional[str] = None


class ClaimResponse(BaseModel):
    """Claim response with all details"""
    id: int
    claim_number: str
    employee_id: int
    category_id: int
    location_id: Optional[int] = None
    status_id: int
    claim_type: str
    claim_date: date
    duration_days: int
    user_amount: Optional[float] = None
    system_amount: Optional[float] = None
    final_amount: Optional[float] = None
    description: Optional[str] = None
    rejection_reason: Optional[str] = None
    appeal_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    
    # Joined fields
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    grade_code: Optional[str] = None
    category_code: Optional[str] = None
    category_name: Optional[str] = None
    location_name: Optional[str] = None
    status_code: Optional[str] = None
    status_name: Optional[str] = None
    manager_id: Optional[int] = None
    manager_name: Optional[str] = None
    approved_by: Optional[int] = None
    approver_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class ClaimWithReceipts(ClaimResponse):
    """Claim with receipts included"""
    receipts: List[ReceiptInfo] = []


class ClaimListResponse(BaseModel):
    """Response for listing claims"""
    claims: List[ClaimResponse]
    total: Optional[int] = None


class ClaimStatsResponse(BaseModel):
    """Claim statistics for an employee"""
    total_claims: int
    approved_claims: int
    pending_claims: int
    rejected_claims: int
    total_approved_amount: float
