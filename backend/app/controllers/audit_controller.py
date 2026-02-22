"""
Audit Controller
API routes for audit log viewing
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from app.controllers.base import BaseController
from app.models.audit_log import AuditLog
from app.utils.auth import require_permission


class AuditController(BaseController):
    """Controller for audit log endpoints"""
    
    prefix = "/api/audit-logs"
    tags = ["Audit Logs"]
    
    def __init__(self):
        super().__init__()
    
    def _register_routes(self):
        """Register audit routes"""
        self.router.get("/")(self.get_audit_logs)
        self.router.get("/export")(self.export_audit_logs)
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
        auth: dict = Depends(require_permission("audit.view"))
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
    
    async def export_audit_logs(
        self,
        entity_type: Optional[str] = None,
        action: Optional[str] = None,
        performed_by: Optional[int] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        auth: dict = Depends(require_permission("audit.view"))
    ):
        """Export audit logs to CSV"""
        import io
        import csv
        from datetime import date
        from fastapi.responses import StreamingResponse
        
        logs = await AuditLog.find_all(
            entity_type=entity_type,
            action=action,
            performed_by=performed_by,
            organization_id=auth.get('organization_id'),
            from_date=from_date,
            to_date=to_date,
            limit=10000,
            offset=0
        )
        
        output = io.BytesIO()
        text_buffer = io.StringIO()
        writer = csv.writer(text_buffer)
        
        headers = [
            'Date & Time',
            'Action',
            'Entity Type',
            'Description',
            'Performed By',
            'Organization',
            'IP Address'
        ]
        writer.writerow(headers)
        
        for log in logs:
            log_dict = log.to_dict()
            writer.writerow([
                log_dict.get('created_at', ''),
                log_dict.get('action', ''),
                log_dict.get('entity_type', ''),
                log_dict.get('description', ''),
                log_dict.get('performed_by_name', '') or 'System',
                log_dict.get('organization_name', '') or 'N/A',
                log_dict.get('ip_address', '')
            ])
            
        output.write(text_buffer.getvalue().encode('utf-8'))
        output.seek(0)
        
        filename = f"audit_logs_export_{date.today()}.csv"
        
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    async def get_audit_stats(
        self,
        auth: dict = Depends(require_permission("audit.view"))
    ):
        """Get audit log statistics"""
        return await AuditLog.get_statistics()
    
    async def get_audit_log(
        self,
        audit_id: int,
        auth: dict = Depends(require_permission("audit.view"))
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
        auth: dict = Depends(require_permission("audit.view"))
    ):
        """Get all audit logs for a specific entity"""
        logs = await AuditLog.find_by_entity(entity_type, entity_id)
        return {"logs": [l.to_dict() for l in logs]}


# Create controller instance and export router
audit_controller = AuditController()
router = audit_controller.router
