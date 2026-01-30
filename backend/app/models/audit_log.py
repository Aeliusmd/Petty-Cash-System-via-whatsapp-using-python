"""
Audit Log Model
OOP class for audit log database operations
"""

import json
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from app.models.base import BaseModel
from app.db.database import db


class AuditLog(BaseModel):
    """
    AuditLog model with database operations.
    Handles comprehensive system audit logging.
    """
    
    table_name = "audit_logs"
    
    # Instance attributes
    id: int = None
    entity_type: str = None
    entity_id: int = None
    action: str = None
    old_values: Dict = None
    new_values: Dict = None
    performed_by: int = None
    ip_address: str = None
    user_agent: str = None
    session_id: str = None
    organization_id: int = None
    metadata: Dict = None
    created_at: datetime = None
    
    # Joined fields
    performed_by_name: str = None
    performed_by_code: str = None
    organization_name: str = None
    
    def __init__(self, data: Dict[str, Any] = None):
        """Initialize audit log from data dict"""
        super().__init__(data)
        # Parse JSON fields if strings
        if isinstance(self.old_values, str):
            try:
                self.old_values = json.loads(self.old_values)
            except:
                self.old_values = {}
        if isinstance(self.new_values, str):
            try:
                self.new_values = json.loads(self.new_values)
            except:
                self.new_values = {}
        if isinstance(self.metadata, str):
            try:
                self.metadata = json.loads(self.metadata)
            except:
                self.metadata = {}
    
    @staticmethod
    def _decimal_default(obj):
        """JSON encoder for Decimal objects"""
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    @classmethod
    async def create(cls, data: Dict[str, Any]) -> 'AuditLog':
        """Create a new audit log entry"""
        old_values_json = json.dumps(data.get('old_values'), default=cls._decimal_default) if data.get('old_values') else None
        new_values_json = json.dumps(data.get('new_values'), default=cls._decimal_default) if data.get('new_values') else None
        metadata_json = json.dumps(data.get('metadata'), default=cls._decimal_default) if data.get('metadata') else '{}'
        
        row = await db.query_one("""
            INSERT INTO audit_logs (
                entity_type, entity_id, action, old_values, new_values,
                performed_by, ip_address, user_agent, session_id,
                organization_id, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING *
        """, 
            data.get('entity_type'), data.get('entity_id'), data.get('action'),
            old_values_json, new_values_json, data.get('performed_by'),
            data.get('ip_address'), data.get('user_agent'), data.get('session_id'),
            data.get('organization_id'), metadata_json
        )
        
        return cls(dict(row)) if row else None
    
    @classmethod
    async def find_all(
        cls,
        entity_type: str = None,
        action: str = None,
        performed_by: int = None,
        organization_id: int = None,
        from_date: str = None,
        to_date: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List['AuditLog']:
        """Get audit logs with optional filtering"""
        conditions = []
        params = []
        param_count = 1
        
        if entity_type:
            conditions.append(f"a.entity_type = ${param_count}")
            params.append(entity_type)
            param_count += 1
        
        if action:
            conditions.append(f"a.action = ${param_count}")
            params.append(action)
            param_count += 1
        
        if performed_by:
            conditions.append(f"a.performed_by = ${param_count}")
            params.append(performed_by)
            param_count += 1
        
        if organization_id:
            conditions.append(f"a.organization_id = ${param_count}")
            params.append(organization_id)
            param_count += 1
        
        if from_date:
            conditions.append(f"a.created_at >= ${param_count}")
            params.append(from_date)
            param_count += 1
        
        if to_date:
            conditions.append(f"a.created_at <= ${param_count}")
            params.append(to_date)
            param_count += 1
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT 
                a.*, e.name as performed_by_name, e.employee_code as performed_by_code,
                u.name as organization_name
            FROM audit_logs a
            LEFT JOIN employees e ON a.performed_by = e.id
            LEFT JOIN units u ON a.organization_id = u.id
            WHERE {where_clause}
            ORDER BY a.created_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        
        params.extend([limit, offset])
        rows = await db.query(query, *params)
        return [cls(dict(row)) for row in rows]
    
    @classmethod
    async def count_all(
        cls,
        entity_type: str = None,
        action: str = None,
        performed_by: int = None,
        organization_id: int = None,
        from_date: str = None,
        to_date: str = None
    ) -> int:
        """Count audit logs with optional filtering"""
        conditions = []
        params = []
        param_count = 1
        
        if entity_type:
            conditions.append(f"entity_type = ${param_count}")
            params.append(entity_type)
            param_count += 1
        
        if action:
            conditions.append(f"action = ${param_count}")
            params.append(action)
            param_count += 1
        
        if performed_by:
            conditions.append(f"performed_by = ${param_count}")
            params.append(performed_by)
            param_count += 1
        
        if organization_id:
            conditions.append(f"organization_id = ${param_count}")
            params.append(organization_id)
            param_count += 1
        
        if from_date:
            conditions.append(f"created_at >= ${param_count}")
            params.append(from_date)
            param_count += 1
        
        if to_date:
            conditions.append(f"created_at <= ${param_count}")
            params.append(to_date)
            param_count += 1
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        row = await db.query_one(f"SELECT COUNT(*) as count FROM audit_logs WHERE {where_clause}", *params)
        return row['count'] if row else 0
    
    @classmethod
    async def find_by_id(cls, audit_log_id: int) -> Optional['AuditLog']:
        """Get a specific audit log entry by ID"""
        row = await db.query_one("""
            SELECT 
                a.*, e.name as performed_by_name, e.employee_code as performed_by_code,
                u.name as organization_name
            FROM audit_logs a
            LEFT JOIN employees e ON a.performed_by = e.id
            LEFT JOIN units u ON a.organization_id = u.id
            WHERE a.id = $1
        """, audit_log_id)
        return cls(dict(row)) if row else None
    
    @classmethod
    async def find_by_entity(cls, entity_type: str, entity_id: int) -> List['AuditLog']:
        """Get all audit logs for a specific entity"""
        rows = await db.query("""
            SELECT 
                a.*, e.name as performed_by_name, e.employee_code as performed_by_code
            FROM audit_logs a
            LEFT JOIN employees e ON a.performed_by = e.id
            WHERE a.entity_type = $1 AND a.entity_id = $2
            ORDER BY a.created_at DESC
        """, entity_type, entity_id)
        return [cls(dict(row)) for row in rows]
    
    @classmethod
    async def find_by_user(cls, employee_id: int, limit: int = 50, offset: int = 0) -> List['AuditLog']:
        """Get all audit logs performed by a specific user"""
        rows = await db.query("""
            SELECT 
                a.*, e.name as performed_by_name, e.employee_code as performed_by_code
            FROM audit_logs a
            LEFT JOIN employees e ON a.performed_by = e.id
            WHERE a.performed_by = $1
            ORDER BY a.created_at DESC
            LIMIT $2 OFFSET $3
        """, employee_id, limit, offset)
        return [cls(dict(row)) for row in rows]
    
    @classmethod
    async def get_statistics(cls) -> Dict[str, Any]:
        """Get audit log statistics"""
        total_row = await db.query_one("SELECT COUNT(*) as count FROM audit_logs")
        total_logs = total_row['count'] if total_row else 0
        
        action_rows = await db.query("SELECT action, COUNT(*) as count FROM audit_logs GROUP BY action ORDER BY count DESC")
        logs_by_action = {row['action']: row['count'] for row in action_rows}
        
        entity_rows = await db.query("SELECT entity_type, COUNT(*) as count FROM audit_logs GROUP BY entity_type ORDER BY count DESC")
        logs_by_entity = {row['entity_type']: row['count'] for row in entity_rows}
        
        recent_row = await db.query_one("SELECT COUNT(*) as count FROM audit_logs WHERE created_at >= NOW() - INTERVAL '24 hours'")
        recent_logs = recent_row['count'] if recent_row else 0
        
        users_rows = await db.query("""
            SELECT e.name, e.employee_code, COUNT(*) as count
            FROM audit_logs a
            JOIN employees e ON a.performed_by = e.id
            GROUP BY e.id, e.name, e.employee_code
            ORDER BY count DESC LIMIT 10
        """)
        top_users = [{'name': row['name'], 'employee_code': row['employee_code'], 'count': row['count']} for row in users_rows]
        
        return {
            'total_logs': total_logs,
            'logs_by_action': logs_by_action,
            'logs_by_entity': logs_by_entity,
            'recent_logs_24h': recent_logs,
            'top_users': top_users
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log to dictionary"""
        return {
            'id': self.id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'action': self.action,
            'old_values': self.old_values,
            'new_values': self.new_values,
            'performed_by': self.performed_by,
            'performed_by_name': self.performed_by_name,
            'performed_by_code': self.performed_by_code,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'session_id': self.session_id,
            'organization_id': self.organization_id,
            'organization_name': self.organization_name,
            'metadata': self.metadata,
            'created_at': self.created_at
        }


# Backward compatibility - expose class methods as module functions
async def create(
    entity_type: str,
    entity_id: int = None,
    action: str = None,
    old_values: Dict = None,
    new_values: Dict = None,
    performed_by: int = None,
    ip_address: str = None,
    user_agent: str = None,
    session_id: str = None,
    organization_id: int = None,
    metadata: Dict = None
):
    log = await AuditLog.create({
        'entity_type': entity_type,
        'entity_id': entity_id,
        'action': action,
        'old_values': old_values,
        'new_values': new_values,
        'performed_by': performed_by,
        'ip_address': ip_address,
        'user_agent': user_agent,
        'session_id': session_id,
        'organization_id': organization_id,
        'metadata': metadata
    })
    return log.to_dict() if log else None

async def find_all(
    entity_type: str = None,
    action: str = None,
    performed_by: int = None,
    organization_id: int = None,
    from_date: str = None,
    to_date: str = None,
    limit: int = 50,
    offset: int = 0
):
    logs = await AuditLog.find_all(entity_type, action, performed_by, organization_id, from_date, to_date, limit, offset)
    return [l.to_dict() for l in logs]

async def count_all(
    entity_type: str = None,
    action: str = None,
    performed_by: int = None,
    organization_id: int = None,
    from_date: str = None,
    to_date: str = None
):
    return await AuditLog.count_all(entity_type, action, performed_by, organization_id, from_date, to_date)

async def find_by_id(audit_log_id: int):
    log = await AuditLog.find_by_id(audit_log_id)
    return log.to_dict() if log else None

async def find_by_entity(entity_type: str, entity_id: int):
    logs = await AuditLog.find_by_entity(entity_type, entity_id)
    return [l.to_dict() for l in logs]

async def find_by_user(employee_id: int, limit: int = 50, offset: int = 0):
    logs = await AuditLog.find_by_user(employee_id, limit, offset)
    return [l.to_dict() for l in logs]

async def get_statistics():
    return await AuditLog.get_statistics()
