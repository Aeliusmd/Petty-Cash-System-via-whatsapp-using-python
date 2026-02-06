"""
Claim Service
OOP class for claim business logic
"""

from typing import Optional, List, Dict, Any
from datetime import date
from fastapi import Request
from app.services.base import BaseService
from app.services.audit_service import AuditService
from app.models.claim import Claim
from app.models.employee import Employee


class ClaimService(BaseService):
    """
    Service for claim business logic.
    Handles claim CRUD, approvals, rejections, appeals with audit logging.
    """
    
    def __init__(self, request: Optional[Request] = None, audit_service: AuditService = None):
        """Initialize with optional request and audit service"""
        super().__init__(request)
        self.audit_service = audit_service or AuditService(request)
    
    async def get_claim(self, claim_id: int) -> Optional[Claim]:
        """Get claim by ID with full details"""
        return await Claim.find_by_id(claim_id)
    
    async def get_claim_by_number(self, claim_number: str) -> Optional[Claim]:
        """Get claim by claim number"""
        return await Claim.find_by_number(claim_number)
    
    async def get_claims_by_employee(
        self,
        employee_id: int,
        status: str = None,
        limit: int = 10,
        offset: int = 0,
        organization_id: int = None
    ) -> Dict[str, Any]:
        """Get claims for an employee, filtered by organization. Returns {'claims': [], 'total': int}"""
        claims, total = await Claim.find_by_employee(employee_id, status, limit, offset, organization_id)
        return {'claims': claims, 'total': total}
    
    async def get_pending_claims_for_manager(self, manager_id: int, organization_id: int = None) -> List[Claim]:
        """Get pending claims for a manager, filtered by organization"""
        return await Claim.find_pending_for_manager(manager_id, organization_id)
    
    async def create_claim(
        self,
        data: Dict[str, Any],
        created_by: int = None,
        organization_id: int = None
    ) -> Claim:
        """Create new claim with audit logging"""
        claim = await Claim.create(data)
        
        # Record initial status
        await Claim.record_status_change(
            claim.id, None, 'PENDING', created_by or data.get('employee_id'),
            'Claim submitted'
        )
        
        await self.audit_service.log_claim_action(
            claim_id=claim.id,
            action='CREATE',
            new_values=data,
            performed_by=created_by or data.get('employee_id'),
            organization_id=organization_id
        )
        
        return claim
    
    async def approve_claim(
        self,
        claim_id: int,
        approver_id: int,
        final_amount: float = None,
        organization_id: int = None
    ) -> Optional[Claim]:
        """Approve a claim with audit logging"""
        current = await Claim.find_by_id(claim_id)
        if not current:
            return None
        
        old_values = {
            'status_code': current.status_code,
            'final_amount': current.final_amount
        }
        
        claim = await Claim.approve(claim_id, approver_id, final_amount)
        
        # Record status change
        await Claim.record_status_change(
            claim_id, current.status_code, 'APPROVED', approver_id,
            f'Claim approved. Final amount: {claim.final_amount}'
        )
        
        await self.audit_service.log_claim_action(
            claim_id=claim_id,
            action='APPROVE',
            old_values=old_values,
            new_values={
                'status_code': 'APPROVED',
                'final_amount': claim.final_amount,
                'approved_by': approver_id
            },
            performed_by=approver_id,
            organization_id=organization_id
        )
        
        return claim
    
    async def reject_claim(
        self,
        claim_id: int,
        approver_id: int,
        reason: str,
        organization_id: int = None
    ) -> Optional[Claim]:
        """Reject a claim with audit logging"""
        current = await Claim.find_by_id(claim_id)
        if not current:
            return None
        
        old_values = {
            'status_code': current.status_code,
            'rejection_reason': current.rejection_reason
        }
        
        claim = await Claim.reject(claim_id, approver_id, reason)
        
        # Record status change
        await Claim.record_status_change(
            claim_id, current.status_code, 'REJECTED', approver_id,
            f'Rejected: {reason}'
        )
        
        await self.audit_service.log_claim_action(
            claim_id=claim_id,
            action='REJECT',
            old_values=old_values,
            new_values={
                'status_code': 'REJECTED',
                'rejection_reason': reason,
                'approved_by': approver_id
            },
            performed_by=approver_id,
            organization_id=organization_id
        )
        
        return claim
    
    async def appeal_claim(
        self,
        claim_id: int,
        employee_id: int,
        notes: str = None,
        organization_id: int = None
    ) -> Optional[Claim]:
        """Appeal a rejected claim with audit logging"""
        current = await Claim.find_by_id(claim_id)
        if not current:
            return None
        
        if current.status_code != 'REJECTED':
            raise ValueError("Only rejected claims can be appealed")
        
        old_values = {
            'status_code': current.status_code,
            'appeal_count': current.appeal_count
        }
        
        claim = await Claim.appeal(claim_id, employee_id, notes)
        
        await self.audit_service.log_claim_action(
            claim_id=claim_id,
            action='APPEAL',
            old_values=old_values,
            new_values={
                'status_code': 'APPEALED',
                'appeal_count': claim.appeal_count if claim else old_values['appeal_count'] + 1
            },
            performed_by=employee_id,
            organization_id=organization_id,
            metadata={'notes': notes}
        )
        
        return claim
    
    async def get_claim_stats(self, employee_id: int) -> Dict[str, Any]:
        """Get claim statistics for an employee"""
        return await Claim.get_stats(employee_id)
    
    async def get_claim_history(self, claim_id: int) -> List[Dict[str, Any]]:
        """Get status history for a claim"""
        return await Claim.get_history(claim_id)
    
    async def add_receipt(
        self,
        claim_id: int,
        file_path: str,
        file_name: str,
        file_type: str = None,
        file_size: int = None,
        ocr_amount: float = None,
        ocr_raw_text: str = None,
        message_id: str = None,
        vendor: str = None,
        uploaded_by: int = None,
        organization_id: int = None
    ) -> Dict[str, Any]:
        """Add receipt to claim with audit logging"""
        receipt = await Claim.add_receipt(
            claim_id, file_path, file_name, file_type,
            file_size, ocr_amount, ocr_raw_text, message_id, vendor
        )
        
        if receipt and uploaded_by:
            await self.audit_service.log_receipt_action(
                receipt_id=receipt.get('id'),
                claim_id=claim_id,
                action='UPLOAD',
                metadata={
                    'file_name': file_name,
                    'file_type': file_type,
                    'ocr_amount': ocr_amount,
                    'vendor': vendor
                },
                performed_by=uploaded_by,
                organization_id=organization_id
            )
        
        return receipt
    
    async def get_receipts(self, claim_id: int) -> List[Dict[str, Any]]:
        """Get all receipts for a claim"""
        return await Claim.get_receipts(claim_id)
    
    async def process_and_save_receipts(
        self,
        claim_id: int,
        receipt_files: List[Dict[str, Any]],
        employee_id: int,
        organization_id: int = None
    ) -> Dict[str, Any]:
        """
        Process multiple receipts: extract OCR, save to DB, calculate total.
        Shared method for both WhatsApp and Web uploads.
        
        Args:
            claim_id: ID of the claim to attach receipts to
            receipt_files: List of dicts with keys:
                - 'bytes': file content as bytes
                - 'filename': original filename
                - 'content_type': MIME type
            employee_id: ID of employee uploading
            organization_id: Organization context
            
        Returns:
            {
                'receipts_saved': int,
                'total_extracted': float,
                'receipts': [list of receipt records]
            }
        """
        from app.services import textract_service
        from pathlib import Path
        import uuid
        
        total_extracted = 0.0
        receipts_saved = []
        
        # 1. Get receipts directory (handle both local and Docker environments)
        possible_paths = [
            Path("/app/backend/receipts"),  # Docker container
            Path(__file__).resolve().parent.parent / "receipts",  # Local relative to app folder
            Path("receipts").resolve()  # Current working directory
        ]
        
        receipts_dir = None
        for path in possible_paths:
            if path.exists():
                receipts_dir = path
                break
        
        if not receipts_dir:
            # Fallback: create relative to this file's location
            receipts_dir = Path(__file__).resolve().parent.parent / "receipts"
            receipts_dir.mkdir(parents=True, exist_ok=True)
        
        for receipt_data in receipt_files:
            content = receipt_data['bytes']
            filename = receipt_data.get('filename', 'receipt')
            content_type = receipt_data.get('content_type', 'image/jpeg')
            
            # 2. Save file (flat structure, no subdirectories)
            ext = Path(filename).suffix or '.jpg'
            saved_filename = f"{uuid.uuid4()}{ext}"
            file_path = receipts_dir / saved_filename
            
            # Write file synchronously (in async context)
            import asyncio
            await asyncio.to_thread(file_path.write_bytes, content)
            
            # 3. Extract OCR
            ocr_amount = None
            ocr_vendor = None
            ocr_text = None
            
            try:
                print(f"🔍 Extracting data from receipt: {filename}")
                extraction = await textract_service.extract_expense_from_image(content)
                if extraction.get('success'):
                    expense = extraction.get('expense', {})
                    
                    # Parse amount
                    raw_total = expense.get('total')
                    if raw_total:
                        clean_total = str(raw_total).replace(',', '').replace(' ', '')
                        try:
                            ocr_amount = float(clean_total)
                            total_extracted += ocr_amount
                            print(f"✅ Extracted: Rs. {ocr_amount}")
                        except ValueError:
                            print(f"⚠️ Could not parse amount: {raw_total}")
                    
                    ocr_vendor = expense.get('vendorName')
                    ocr_text = extraction.get('text')
            except Exception as e:
                print(f"⚠️ Extraction failed: {e}")
            
            # 4. Save to database
            receipt_record = await self.add_receipt(
                claim_id=claim_id,
                file_path=saved_filename,  # Store only filename, not full path
                file_name=filename,
                file_type=content_type,
                file_size=len(content),
                ocr_amount=ocr_amount,
                ocr_raw_text=ocr_text,
                vendor=ocr_vendor,
                uploaded_by=employee_id,
                organization_id=organization_id
            )
            
            receipts_saved.append(receipt_record)
        
        print(f"📊 Total extracted from {len(receipts_saved)} receipts: Rs. {total_extracted}")
        
        return {
            'receipts_saved': len(receipts_saved),
            'total_extracted': total_extracted,
            'receipts': receipts_saved
        }
    
    async def delete_claim(
        self,
        claim_id: int,
        deleted_by: int,
        organization_id: int = None
    ) -> bool:
        """Delete a claim with audit logging"""
        current = await Claim.find_by_id(claim_id)
        if not current:
            return False
        
        success = await Claim.delete(claim_id)
        
        if success:
            await self.audit_service.log_claim_action(
                claim_id=claim_id,
                action='DELETE',
                old_values=current.to_dict(),
                performed_by=deleted_by,
                organization_id=organization_id
            )
        
        return success
