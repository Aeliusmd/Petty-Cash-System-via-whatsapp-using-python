"""
Mobile-Optimized Schemas (BFF Pattern)
Reduces payload size for mobile devices by stripping unnecessary fields.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

class MobileClaimSummary(BaseModel):
    """Slim claim model for mobile lists"""
    id: int
    claim_number: str
    amount: float = 0.0  # Combined user or system amount logic handled in controller
    status: str
    description: Optional[str] = None
    category: str
    date: date
    
    # Visual cues (colors/icons) can be derived from status on frontend, 
    # but sending a status_color hint is also a valid BFF pattern.
    # We keep it simple for now.

    class Config:
        from_attributes = True

class MobileEmployeeSummary(BaseModel):
    """Slim employee model for contact lists"""
    id: int
    name: str
    role: str
    status: str = "active" # derived from is_active
    avatar_url: Optional[str] = None # Placeholder if we have avatars later

    class Config:
        from_attributes = True

class MobileDashboardStats(BaseModel):
    """Ultra-slim stats for mobile dashboard cards"""
    pending_count: int
    approved_count: int
    total_spent: float
