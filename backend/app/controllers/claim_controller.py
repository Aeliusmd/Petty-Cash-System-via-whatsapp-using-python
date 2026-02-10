"""
Claim Controller
API routes for claim management
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from app.controllers.base import BaseController
from app.services.claim_service import ClaimService
from app.services.notification_service import notify_manager_of_new_claim, notify_staff_of_approval, notify_staff_of_rejection
from app.schemas.claim import (
    ClaimCreate, ClaimUpdate, ClaimApproveRequest, ClaimRejectRequest, 
    ClaimAppealRequest, ClaimResponse, ClaimListResponse
)
from app.utils.auth import require_authenticated, require_permission
from pathlib import Path
import asyncio
import uuid


class ClaimController(BaseController):
    """Controller for claim management endpoints"""
    
    prefix = "/api/claims"
    tags = ["Claims"]
    
    def __init__(self):
        super().__init__()
    
    def _register_routes(self):
        """Register claim routes"""
        self.router.get("/")(self.get_claims)
        self.router.get("/pending")(self.get_pending_claims)
        self.router.get("/stats")(self.get_claim_stats)
        self.router.get("/{claim_id}")(self.get_claim)
        self.router.get("/{claim_id}/receipts")(self.get_claim_receipts)
        self.router.get("/{claim_id}/history")(self.get_claim_history)
        self.router.post("/")(self.create_claim)
        self.router.post("/advance")(self.create_advance_claim)  # New endpoint for advance claims
        self.router.post("/{claim_id}/approve")(self.approve_claim)
        self.router.post("/{claim_id}/reject")(self.reject_claim)
        self.router.post("/{claim_id}/appeal")(self.appeal_claim)
        self.router.delete("/{claim_id}")(self.delete_claim)
    
    async def get_claims(
        self,
        request: Request,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        employee_id: Optional[int] = None,
        auth: dict = Depends(require_authenticated)
    ):
        """Get claims - filtered by permissions"""
        service = ClaimService(request)
        permissions = auth.get('permissions', [])
        
        # Get organization context
        organization_id = auth.get('organization_id')
        
        target_employee_id = employee_id
        
        if target_employee_id:
            # If requesting someone else's claims, check permission
            if target_employee_id != auth['employee_id']:
                if 'claims.read.all' not in permissions and 'claims.read.team' not in permissions:
                     raise HTTPException(status_code=403, detail="Cannot view other employees' claims")
        else:
            # No specific employee requested
            if 'claims.read.all' in permissions:
                target_employee_id = None # Show all
            else:
                target_employee_id = auth['employee_id'] # Fallback to own
        
        # Super admin sees all claims unless they've explicitly entered an org
        if auth.get('role') == 'super_admin' and not auth.get('organization_name'):
            organization_id = None
        
        result = await service.get_claims_by_employee(
            employee_id=target_employee_id,
            status=status,
            limit=limit,
            offset=offset,
            organization_id=organization_id
        )
        
        return {
            "claims": [c.to_dict() for c in result['claims']],
            "total": result['total']
        }
    
    async def get_pending_claims(
        self,
        request: Request,
        auth: dict = Depends(require_authenticated)
    ):
        """Get pending claims for manager/approver"""
        permissions = auth.get('permissions', [])
        
        if 'claims.approve' not in permissions and 'claims.read.team' not in permissions:
            raise HTTPException(status_code=403, detail="Approver permissions required")
        
        service = ClaimService(request)
        
        # Get organization context
        organization_id = auth.get('organization_id')
        
        # Super admin sees all pending claims unless they've explicitly entered an org
        if auth.get('role') == 'super_admin' and not auth.get('organization_name'):
            organization_id = None
        
        claims = await service.get_pending_claims_for_manager(
            manager_id=auth['employee_id'],
            organization_id=organization_id
        )
        
        return {"claims": [c.to_dict() for c in claims]}
    
    async def get_claim_stats(
        self,
        request: Request,
        auth: dict = Depends(require_authenticated)
    ):
        """Get claim statistics for current user"""
        service = ClaimService(request)
        stats = await service.get_claim_stats(auth['employee_id'])
        return stats
    
    async def get_claim(
        self,
        claim_id: int,
        request: Request,
        auth: dict = Depends(require_authenticated)
    ):
        """Get single claim by ID"""
        service = ClaimService(request)
        claim = await service.get_claim(claim_id)
        
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        # Check access
        permissions = auth.get('permissions', [])
        is_own = claim.employee_id == auth['employee_id']
        is_manager = claim.manager_id == auth['employee_id']
        
        if is_own:
            pass # OK
        elif is_manager and ('claims.read.team' in permissions or 'claims.approve' in permissions):
            pass # OK
        elif 'claims.read.all' in permissions:
            pass # OK
        else:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return claim.to_dict()
    
    async def get_claim_receipts(
        self,
        claim_id: int,
        request: Request,
        auth: dict = Depends(require_authenticated)
    ):
        """Get receipts for a claim"""
        service = ClaimService(request)
        receipts = await service.get_receipts(claim_id)
        return {"receipts": receipts}
    
    async def get_claim_history(
        self,
        claim_id: int,
        request: Request,
        auth: dict = Depends(require_authenticated)
    ):
        """Get status history for a claim"""
        service = ClaimService(request)
        history = await service.get_claim_history(claim_id)
        return {"history": history}
    
    @staticmethod
    def _write_file_sync(file_path: Path, content: bytes):
        """Sync file write helper for thread executor"""
        with open(file_path, 'wb') as f:
            f.write(content)
    
    async def create_claim(
        self,
        request: Request,
        category_id: int = Form(...),
        user_amount: float = Form(None),
        description: str = Form(None),
        location_id: int = Form(None),
        receipts: List[UploadFile] = File(None),
        auth: dict = Depends(require_permission("claims.create"))
    ):
        """Create new claim with optional receipt upload"""
        service = ClaimService(request)
        
        # Get employee to determine manager
        from app.models.employee import Employee
        employee = await Employee.find_by_id(auth['employee_id'])
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        claim_data = {
            'employee_id': auth['employee_id'],
            'category_id': category_id,
            'location_id': location_id or employee.location_id,
            'user_amount': user_amount,
            'description': description,
            'manager_id': employee.manager_id,
            'claim_type': 'outright'
        }
        
        claim = await service.create_claim(
            data=claim_data,
            created_by=auth['employee_id'],
            organization_id=auth.get('organization_id')
        )
        
        # Handle receipt uploads using shared service method
        if receipts:
            # Prepare receipt data in format expected by shared method
            receipt_files = []
            for receipt in receipts:
                content = await receipt.read()
                receipt_files.append({
                    'bytes': content,
                    'filename': receipt.filename,
                    'content_type': receipt.content_type
                })
            
            # Use shared receipt processing method
            result = await service.process_and_save_receipts(
                claim_id=claim.id,
                receipt_files=receipt_files,
                employee_id=auth['employee_id'],
                organization_id=auth.get('organization_id')
            )
            
            # Update claim with extracted total if user didn't provide amount
            if result['total_extracted'] > 0 and not user_amount:
                print(f"🔄 Updating claim {claim.id} with total OCR amount: {result['total_extracted']}")
                from app.models.claim import Claim as ClaimModel
                await ClaimModel.update(claim.id, {'system_amount': result['total_extracted']})
                
                # Refresh claim object for notification
                refreshed_claim = await ClaimModel.find_by_id(claim.id)
                if refreshed_claim:
                    claim = refreshed_claim
        
        # Notify manager
        try:
            claim_dict = claim.to_dict()
            claim_dict['employee_name'] = employee.name
            claim_dict['employee_code'] = employee.employee_code
            await notify_manager_of_new_claim(claim_dict)
        except Exception as e:
            print(f"⚠️ Failed to notify manager: {e}")
        
        return self.success_response(data=claim.to_dict(), message="Claim created successfully")
    
    async def create_advance_claim(
        self,
        request: Request,
        category_id: int = Form(...),
        amount: float = Form(...),
        description: str = Form(...),
        location_id: int = Form(None),
        quotations: List[UploadFile] = File(None),
        auth: dict = Depends(require_permission("claims.create"))
    ):
        """Create new advance claim with optional quotation upload"""
        service = ClaimService(request)
        
        # Get employee to determine manager
        from app.models.employee import Employee
        employee = await Employee.find_by_id(auth['employee_id'])
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Determine final amount: prioritize user-entered amount, then extract from quotations
        final_amount = amount  # Start with user-entered amount
        total_from_quotations = 0
        
        # Handle quotation uploads first to extract amounts
        quotation_data = []
        if quotations:
            for quotation in quotations:
                content = await quotation.read()
                quotation_data.append({
                    'bytes': content,
                    'filename': quotation.filename,
                    'content_type': quotation.content_type
                })
        
        # Only extract amounts from quotations if user didn't provide amount
        if quotation_data and not amount:
            # Use shared receipt processing to extract data from quotations
            from app.services.textract_service import extract_expense_data
            
            for quot_file in quotation_data:
                try:
                    extraction = await extract_expense_data(quot_file['bytes'])
                    if extraction and extraction.get('success'):
                        extracted_amount = extraction.get('expense', {}).get('total')
                        if extracted_amount:
                            # Clean and convert amount
                            amount_str = str(extracted_amount).replace(',', '').replace('Rs.', '').strip()
                            try:
                                total_from_quotations += float(amount_str)
                            except ValueError:
                                pass
                except Exception as e:
                    print(f"⚠️ Failed to extract from quotation: {e}")
            
            # Use total from quotations if extraction was successful
            if total_from_quotations > 0:
                final_amount = total_from_quotations
                print(f"💰 Using total from quotations: Rs. {final_amount:,.0f}")
        else:
            print(f"💰 Using user-entered amount: Rs. {final_amount:,.0f}")

        
        claim_data = {
            'employee_id': auth['employee_id'],
            'category_id': category_id,
            'location_id': location_id or employee.location_id,
            'user_amount': final_amount,
            'description': description,
            'manager_id': employee.manager_id,
            'claim_type': 'advance'  # Mark as advance claim
        }
        
        claim = await service.create_claim(
            data=claim_data,
            created_by=auth['employee_id'],
            organization_id=auth.get('organization_id')
        )
        
        # Save quotations as receipts
        if quotation_data:
            result = await service.process_and_save_receipts(
                claim_id=claim.id,
                receipt_files=quotation_data,
                employee_id=auth['employee_id'],
                organization_id=auth.get('organization_id')
            )
            print(f"✅ Saved {len(quotation_data)} quotations for advance claim {claim.id}")
        
        # Notify manager
        try:
            claim_dict = claim.to_dict()
            claim_dict['employee_name'] = employee.name
            claim_dict['employee_code'] = employee.employee_code
            await notify_manager_of_new_claim(claim_dict)
        except Exception as e:
            print(f"⚠️ Failed to notify manager: {e}")
        
        return self.success_response(data=claim.to_dict(), message="Advance claim created successfully")

    
    async def approve_claim(
        self,
        claim_id: int,
        data: ClaimApproveRequest,
        request: Request,
        auth: dict = Depends(require_permission("claims.approve"))
    ):
        """Approve a claim"""
        service = ClaimService(request)
        
        claim = await service.approve_claim(
            claim_id=claim_id,
            approver_id=auth['employee_id'],
            final_amount=data.final_amount,
            organization_id=auth.get('organization_id')
        )
        
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        # Notify staff
        try:
            await notify_staff_of_approval(claim.to_dict())
        except Exception as e:
            print(f"⚠️ Failed to notify staff: {e}")
        
        return self.success_response(data=claim.to_dict(), message="Claim approved")
    
    async def reject_claim(
        self,
        claim_id: int,
        data: ClaimRejectRequest,
        request: Request,
        auth: dict = Depends(require_permission("claims.reject"))
    ):
        """Reject a claim"""
        service = ClaimService(request)
        
        claim = await service.reject_claim(
            claim_id=claim_id,
            approver_id=auth['employee_id'],
            reason=data.reason,
            organization_id=auth.get('organization_id')
        )
        
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        # Notify staff
        try:
            await notify_staff_of_rejection(claim.to_dict(), data.reason)
        except Exception as e:
            print(f"⚠️ Failed to notify staff: {e}")
        
        return self.success_response(data=claim.to_dict(), message="Claim rejected")
    
    async def appeal_claim(
        self,
        claim_id: int,
        request: Request,
        notes: str = Form(...),
        receipts: List[UploadFile] = File(None),
        auth: dict = Depends(require_permission("claims.appeal"))
    ):
        """Appeal a rejected claim with optional additional receipts"""
        service = ClaimService(request)
        
        # Verify ownership
        claim = await service.get_claim(claim_id)
        if not claim or claim.employee_id != auth['employee_id']:
            raise HTTPException(status_code=403, detail="Can only appeal your own claims")
        
        try:
            claim = await service.appeal_claim(
                claim_id=claim_id,
                employee_id=auth['employee_id'],
                notes=notes,
                organization_id=auth.get('organization_id')
            )
            
            # Handle additional receipt uploads during appeal
            if receipts and len(receipts) > 0:
                # Prepare receipt data
                receipt_files = []
                for receipt in receipts:
                    content = await receipt.read()
                    receipt_files.append({
                        'bytes': content,
                        'filename': receipt.filename,
                        'content_type': receipt.content_type
                    })
                
                # Use shared receipt processing method
                await service.process_and_save_receipts(
                    claim_id=claim.id,
                    receipt_files=receipt_files,
                    employee_id=auth['employee_id'],
                    organization_id=auth.get('organization_id')
                )
                
                print(f"✅ Processed {len(receipts)} additional receipts for appeal on claim {claim_id}")
            
            # Notify manager of the appeal
            try:
                from app.services.notification_service import notify_manager_of_appeal
                claim_dict = claim.to_dict()
                await notify_manager_of_appeal(claim_dict, notes)
            except Exception as e:
                print(f"⚠️ Failed to notify manager of appeal: {e}")
                
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        return self.success_response(data=claim.to_dict(), message="Appeal submitted")
    
    async def delete_claim(
        self,
        claim_id: int,
        request: Request,
        auth: dict = Depends(require_permission("claims.delete.all"))
    ):
        """Delete a claim (admin only)"""
        service = ClaimService(request)
        
        success = await service.delete_claim(
            claim_id=claim_id,
            deleted_by=auth['employee_id'],
            organization_id=auth.get('organization_id')
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        return self.success_response(message="Claim deleted successfully")


# Create controller instance and export router
claim_controller = ClaimController()
router = claim_controller.router
