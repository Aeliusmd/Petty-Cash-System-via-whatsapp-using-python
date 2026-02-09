"""
Mobile Controller (BFF Pattern)
Endpoints optimized for mobile consumption.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from app.models.claim import Claim
from app.models.employee import Employee
from app.dependencies import get_current_user
from app.schemas.mobile import MobileClaimSummary, MobileEmployeeSummary, MobileDashboardStats

router = APIRouter(
    prefix="/api/mobile",
    tags=["Mobile BFF"],
    responses={404: {"description": "Not found"}},
)

@router.get("/claims", response_model=List[MobileClaimSummary])
async def get_mobile_claims(
    skip: int = 0,
    limit: int = 20, # Smaller default limit for mobile
    status: Optional[str] = None,
    current_user: Employee = Depends(get_current_user)
):
    """
    Get slim claims list for mobile.
    """
    # Use Claim model directly
    # find_by_employee parameters: employee_id, status, limit, offset, organization_id
    
    # Logic to handle different roles if needed, currently assumes own claims or filtered by generic logic
    # But wait, find_by_employee is for a specific employee.
    # If mobile app is for the logged in user, this is correct.
    # If manager needs to see team claims, we might need a different method.
    # For now, let's stick to "My Claims" equivalent for mobile.
    
    claims, _ = await Claim.find_by_employee(
        employee_id=current_user.id,
        status=None if status == 'All' else status,
        limit=limit,
        offset=skip,
        organization_id=current_user.organization_id
    )

    # Map to mobile summary
    mobile_claims = []
    for claim in claims:
        # Logic to determine display amount
        amount = claim.final_amount if claim.final_amount is not None else (claim.user_amount or 0.0)
        
        mobile_claims.append(MobileClaimSummary(
            id=claim.id,
            claim_number=claim.claim_number,
            amount=amount,
            status=claim.status_name or str(claim.status_id),
            description=claim.description[:50] + "..." if claim.description and len(claim.description) > 50 else claim.description,
            category=claim.category_name or "Uncategorized",
            date=claim.claim_date
        ))
        
    return mobile_claims

@router.get("/employees", response_model=List[MobileEmployeeSummary])
async def get_mobile_employees(
    skip: int = 0,
    limit: int = 50,
    current_user: Employee = Depends(get_current_user)
):
    """
    Get contact list for mobile (e.g. for selection).
    """
    # Use Employee model directly
    employees = await Employee.find_all_with_details(
        organization_id=current_user.organization_id,
        include_inactive=False
    )
    
    # Apply pagination manually as find_all_with_details doesn't support it directly in signature shown 
    # (actually find_all_with_details signature in service showed filters but not limit/offset, let's double check model if needed)
    # But usually we can just slice list in python if it's small enough, or assume it's small.
    # For now, let's slice.
    employees = employees[skip : skip + limit]
        
    mobile_employees = []
    for emp in employees:
        mobile_employees.append(MobileEmployeeSummary(
            id=emp.id,
            name=emp.name,
            role=emp.role,
            status="active" if emp.is_active else "inactive"
        ))
        
    return mobile_employees

@router.get("/stats", response_model=MobileDashboardStats)
async def get_mobile_stats(
    current_user: Employee = Depends(get_current_user)
):
    """
    Get simplified dashboard stats.
    """
    if current_user.is_super_admin:
        # Super admin sees all or filtered by org? usually all.
        # But get_dashboard_stats accepts org_id.
        stats = await Claim.get_dashboard_stats()
        return MobileDashboardStats(
            pending_count=stats.get("pending_claims", 0),
            approved_count=stats.get("approved_claims", 0),
            total_spent=stats.get("total_approved_amount", 0.0)
        )
    elif current_user.is_manager:
        stats = await Claim.get_dashboard_stats(
            organization_id=current_user.organization_id,
            manager_id=current_user.id
        )
        return MobileDashboardStats(
            pending_count=stats.get("pending_claims", 0),
            approved_count=stats.get("approved_claims", 0),
            total_spent=stats.get("total_approved_amount", 0.0)
        )
    else:
        stats = await Claim.get_stats(current_user.id)
        return MobileDashboardStats(
            pending_count=stats.get("pending_claims", 0),
            approved_count=stats.get("approved_claims", 0),
            total_spent=stats.get("total_approved_amount", 0.0)
        )
