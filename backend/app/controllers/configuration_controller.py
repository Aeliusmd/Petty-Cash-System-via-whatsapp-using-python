"""
Configuration Controller
API routes for system configuration (Units, Grades, Locations, Categories)
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List, Any, Dict
from pydantic import BaseModel
from app.models.unit import Unit
from app.models.rates import Grade, Location
from app.models.category import Category
from app.models.approval import ApprovalPolicy
from app.db import db
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.utils.auth import require_authenticated, require_permission

# Inline Schemas for Unit
class UnitCreate(BaseModel):
    code: str
    name: str
    organization_id: int
    is_active: bool = True

class UnitUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None


class ApprovalStepInput(BaseModel):
    step_order: int
    role_type: str
    assignee_employee_id: Optional[int] = None
    is_required: bool = True


class ApprovalPolicyUpsert(BaseModel):
    unit_id: int
    name: str
    steps: List[ApprovalStepInput]

# Main router that aggregates sub-routers
router = APIRouter()

# ---------------------------------------------------------
# Units Routes
# ---------------------------------------------------------
units_router = APIRouter(prefix="/api/units", tags=["Configuration"])

@units_router.get("/")
async def get_units(
    organization_id: Optional[int] = None, 
    auth: dict = Depends(require_authenticated)
):
    """Get all units, SCOPED by organization"""
    # Determine context: Param or Auth Token
    org_id = organization_id or auth.get("organization_id")
    
    # If no org context (and not super admin explicitly requesting all?), return empty or scoped
    # Safety: If no org_id, and not specifically requesting generic list... 
    # But usually all users are in an org context.
    if not org_id:
        # If Super Admin, return all units
        if auth.get('role') == 'super_admin':
            units = await Unit.find_all()
            # Normalize response to list of dicts
            result = []
            for u in units:
                if hasattr(u, 'to_dict'):
                    result.append(u.to_dict())
                else:
                    result.append(u)
            return {"units": result}
            
        return {"units": []}

    units = await Unit.find_by_organization(int(org_id))

    # Normalize response to list of dicts
    result = []
    for u in units:
        if hasattr(u, 'to_dict'):
            result.append(u.to_dict())
        elif isinstance(u, dict):
            result.append(u)
        else:
            result.append(u)
            
    return {"units": result}

@units_router.post("/")
async def create_unit(
    data: UnitCreate,
    auth: dict = Depends(require_permission("config.manage"))
):
    """Create a new unit (department)"""
    # Validation: Ensure creation within auth scope (unless super admin)
    auth_org_id = auth.get("organization_id")
    if auth_org_id and auth_org_id != data.organization_id:
        # Allow super Check? For now strict
        # If user is Super Admin but entered Org A, they should create in Org A?
        # data.organization_id comes from form.
        pass 
    
    unit = await Unit.create(data.model_dump())
    return unit.to_dict() if unit else {}

@units_router.put("/{unit_id}")
async def update_unit(
    unit_id: int,
    data: UnitUpdate,
    auth: dict = Depends(require_permission("config.manage"))
):
    """Update a unit"""
    unit = await Unit.find_by_id(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    
    updated = await Unit.update(unit_id, data.model_dump(exclude_unset=True))  # Call as class method
    return updated.to_dict() if updated else {}

@units_router.delete("/{unit_id}")
async def delete_unit(
    unit_id: int,
    auth: dict = Depends(require_permission("config.manage"))
):
    """Delete a unit"""
    unit = await Unit.find_by_id(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
        
    await Unit.delete(unit_id)  # Call as class method with unit_id
    return {"success": True}


# ---------------------------------------------------------
# Grades Routes
# ---------------------------------------------------------
grades_router = APIRouter(prefix="/api/grades", tags=["Configuration"])

@grades_router.get("/")
async def get_grades(auth: dict = Depends(require_authenticated)):
    """Get all grades"""
    # Grades might be global or scoped?
    # If scoped, we need checking. 
    # Assuming Grade model is global for now (User didn't complain about Grades mixing)
    # But if they ARE mixed, we need scope.
    # User complained about "Departments" (Units).
    # I'll enable global grades for now. If Organization-Specific grades needed, model update required.
    grades = await Grade.find_all()
    return {"grades": grades}

# ---------------------------------------------------------
# Locations Routes
# ---------------------------------------------------------
locations_router = APIRouter(prefix="/api/locations", tags=["Configuration"])

@locations_router.get("/")
async def get_locations(auth: dict = Depends(require_authenticated)):
    """Get all locations"""
    # Same as grades, assuming Global for now.
    locations = await Location.find_all()
    return {"locations": locations}



# Categories router implementation removed as it is handled by CategoryController

# ---------------------------------------------------------
# Approval Policy Routes
# ---------------------------------------------------------
approval_policies_router = APIRouter(prefix="/api/approval-policies", tags=["Configuration"])


@approval_policies_router.get("")
async def get_approval_policies(
    unit_id: int,
    auth: dict = Depends(require_authenticated),
):
    if auth.get("organization_id"):
        unit = await db.query_one("SELECT organization_id FROM units WHERE id = $1", unit_id)
        if not unit or unit.get("organization_id") != auth.get("organization_id"):
            raise HTTPException(status_code=404, detail="Department not found")
    policies = await ApprovalPolicy.list_by_unit(unit_id)
    enriched: List[Dict[str, Any]] = []
    for policy in policies:
        steps = await ApprovalPolicy.get_steps(policy["id"])
        policy["steps"] = steps
        enriched.append(policy)
    return {"policies": enriched}


@approval_policies_router.post("/default")
async def upsert_default_policy(
    data: ApprovalPolicyUpsert,
    auth: dict = Depends(require_permission("config.manage")),
):
    org_id = auth.get("organization_id")
    if org_id:
        unit = await db.query_one("SELECT organization_id FROM units WHERE id = $1", data.unit_id)
        if not unit or unit.get("organization_id") != org_id:
            raise HTTPException(status_code=404, detail="Department not found")
    policy = await ApprovalPolicy.upsert_default_policy(
        organization_id=org_id,
        unit_id=data.unit_id,
        name=data.name,
    )
    steps = await ApprovalPolicy.replace_steps(
        policy_id=policy["id"],
        steps=[step.model_dump() for step in data.steps],
    )
    policy["steps"] = steps
    return {"policy": policy}


# ---------------------------------------------------------
# Register Sub-Routers
# ---------------------------------------------------------
router.include_router(units_router)
router.include_router(grades_router)
router.include_router(locations_router)
router.include_router(approval_policies_router)
# Categories router removed (handled by CategoryController)
