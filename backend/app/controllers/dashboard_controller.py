"""
Dashboard Controller
API routes for dashboard statistics
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from app.utils.auth import require_manager
from app.models.claim import Claim

router = APIRouter(prefix="/api/stats", tags=["Dashboard"])

@router.get("/")
async def get_dashboard_stats(request: Request, auth: dict = Depends(require_manager)):
    """
    Get dashboard statistics
    Requires Manager/Admin role
    """
    if request.method == "OPTIONS":
        return {}

    # For super_admin viewing global scope, ignore organization filter
    # Super admin's own org membership should not filter the dashboard
    role = auth.get("role", "employee")
    organization_id = auth.get("organization_id")
    
    # If super_admin and viewing global (indicated by not having entered a specific org context)
    # For now, we allow super_admins to always see global stats unless we add explicit "entered org" flag
    # A more robust solution would check if they explicitly "entered" an org
    # For simplicity, super_admins always get global view on the main dashboard
    if role == "super_admin":
        # Super Admin sees all organizations unless they've explicitly entered one
        # The "enter organization" action should set a flag or we rely on frontend to call a different endpoint
        # For now, let's check if org name is set - if not, it's global view
        if not auth.get("organization_name"):
            organization_id = None
    
    # Overview stats
    overview = await Claim.get_dashboard_stats(organization_id)
    
    # Ensure default values for nulls
    overview = {
        "total_claims": overview.get("total_claims", 0),
        "pending_claims": overview.get("pending_claims", 0),
        "approved_claims": overview.get("approved_claims", 0),
        "rejected_claims": overview.get("rejected_claims", 0),
        "total_approved_amount": float(overview.get("total_approved_amount") or 0),
        "pending_amount": float(overview.get("pending_amount") or 0)
    }
    
    # Categories
    categories = await Claim.get_category_stats(organization_id)
    
    # Recent Claims
    recent = await Claim.get_recent_claims(limit=5, organization_id=organization_id)
    
    return {
        "overview": overview,
        "categories": [dict(cat) for cat in categories],
        "recent_claims": recent
    }
