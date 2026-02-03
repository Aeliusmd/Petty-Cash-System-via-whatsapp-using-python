"""
Dashboard Controller
API routes for dashboard statistics
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from app.utils.auth import require_authenticated
from app.models.claim import Claim

router = APIRouter(prefix="/api/stats", tags=["Dashboard"])

@router.get("/")
async def get_dashboard_stats(request: Request, auth: dict = Depends(require_authenticated)):
    """
    Get dashboard statistics
    Requires dashboard.view.org or dashboard.view.team permission
    """
    if request.method == "OPTIONS":
        return {}

    permissions = auth.get("permissions", [])
    organization_id = auth.get("organization_id")
    manager_id = None
    
    # Determine Scope based on permissions
    # Prioritize Org View if user has both
    if "dashboard.view.org" in permissions:
        # Full Organization View (or Global if Super Admin with no org context)
        # Verify if organization_id is None and user is NOT super_admin?
        # Typically require_authenticated ensures valid context unless system role.
        pass
    elif "dashboard.view.team" in permissions:
        # Team View - Limit to manager's team
        manager_id = auth.get("employee_id")
    else:
        raise HTTPException(status_code=403, detail="Access denied to dashboard")
        
    # Super Admin Global View Handling (Legacy/System Role)
    role = auth.get("role", "employee")
    if role == "super_admin" and not auth.get("organization_name"):
        organization_id = None
    
    # Overview stats
    overview = await Claim.get_dashboard_stats(organization_id=organization_id, manager_id=manager_id)
    
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
    categories = await Claim.get_category_stats(organization_id=organization_id, manager_id=manager_id)
    
    # Recent Claims
    recent = await Claim.get_recent_claims(limit=5, organization_id=organization_id, manager_id=manager_id)
    
    return {
        "overview": overview,
        "categories": [dict(cat) for cat in categories],
        "recent_claims": recent
    }
