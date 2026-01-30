"""
Audit Controller
API routes for audit log viewing
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from app.controllers.base import BaseController
from app.models.audit_log import AuditLog
from app.utils.auth import require_admin


class AuditController(BaseController):
    """Controller for audit log endpoints"""
    
    prefix = "/api/audit-logs"
    tags = ["Audit Logs"]
    
    def __init__(self):
        super().__init__()
    
    def _register_routes(self):
        """Register audit routes"""
        self.router.get("/")(self.get_audit_logs)
        self.router.get("/stats")(self.get_audit_stats)
        self.router.get("/{audit_id}")(self.get_audit_log)
        self.router.get("/entity/{entity_type}/{entity_id}")(self.get_entity_logs)
    
    async def get_audit_logs(
        self,
        entity_type: Optional[str] = None,
        action: Optional[str] = None,
        performed_by: Optional[int] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        auth: dict = Depends(require_admin)
    ):
        """Get audit logs with filtering"""
        logs = await AuditLog.find_all(
            entity_type=entity_type,
            action=action,
            performed_by=performed_by,
            organization_id=auth.get('organization_id'),
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset
        )
        
        total = await AuditLog.count_all(
            entity_type=entity_type,
            action=action,
            performed_by=performed_by,
            organization_id=auth.get('organization_id'),
            from_date=from_date,
            to_date=to_date
        )
        
        return self.paginated_response(
            items=[l.to_dict() for l in logs],
            total=total,
            limit=limit,
            offset=offset,
            item_key="audit_logs"
        )
    
    async def get_audit_stats(
        self,
        auth: dict = Depends(require_admin)
    ):
        """Get audit log statistics"""
        return await AuditLog.get_statistics()
    
    async def get_audit_log(
        self,
        audit_id: int,
        auth: dict = Depends(require_admin)
    ):
        """Get single audit log by ID"""
        log = await AuditLog.find_by_id(audit_id)
        if not log:
            raise HTTPException(status_code=404, detail="Audit log not found")
        return log.to_dict()
    
    async def get_entity_logs(
        self,
        entity_type: str,
        entity_id: int,
        auth: dict = Depends(require_admin)
    ):
        """Get all audit logs for a specific entity"""
        logs = await AuditLog.find_by_entity(entity_type, entity_id)
        return {"logs": [l.to_dict() for l in logs]}


# Create controller instance and export router
audit_controller = AuditController()
router = audit_controller.router
