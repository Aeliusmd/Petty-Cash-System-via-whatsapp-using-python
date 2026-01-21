"""
Audit Log Model
Handles all audit log database operations
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from app.db import db


async def create(
    entity_type: str,
    entity_id: Optional[int],
    action: str,
    old_values: Optional[Dict] = None,
    new_values: Optional[Dict] = None,
    performed_by: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None,
    organization_id: Optional[int] = None,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Create a new audit log entry
    
    Args:
        entity_type: Type of entity (e.g., 'claim', 'employee', 'organization')
        entity_id: ID of the entity being audited
        action: Action performed (e.g., 'CREATE', 'UPDATE', 'DELETE', 'APPROVE', 'REJECT')
        old_values: Previous values (for updates)
        new_values: New values
        performed_by: Employee ID who performed the action
        ip_address: IP address of the request
        user_agent: User agent string
        session_id: Session identifier
        organization_id: Organization context
        metadata: Additional metadata as JSON
    
    Returns:
        Created audit log entry
    """
    import json
    from decimal import Decimal
    
    def decimal_default(obj):
        """JSON encoder function to handle Decimal objects"""
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    query = """
        INSERT INTO audit_logs (
            entity_type, entity_id, action, old_values, new_values,
            performed_by, ip_address, user_agent, session_id,
            organization_id, metadata
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING id, entity_type, entity_id, action, old_values, new_values,
                  performed_by, ip_address, user_agent, session_id,
                  organization_id, metadata, created_at
    """
    
    # Convert dicts to JSON strings for JSONB columns, handling Decimal types
    old_values_json = json.dumps(old_values, default=decimal_default) if old_values else None
    new_values_json = json.dumps(new_values, default=decimal_default) if new_values else None
    metadata_json = json.dumps(metadata, default=decimal_default) if metadata else '{}'
    
    row = await db.query_one(
        query,
        entity_type, entity_id, action, old_values_json, new_values_json,
        performed_by, ip_address, user_agent, session_id,
        organization_id, metadata_json
    )
    
    if row:
        return dict(row)
    return None


async def find_all(
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    performed_by: Optional[int] = None,
    organization_id: Optional[int] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get audit logs with optional filtering and pagination
    
    Args:
        entity_type: Filter by entity type
        action: Filter by action
        performed_by: Filter by employee who performed action
        organization_id: Filter by organization
        from_date: Filter by start date (ISO format)
        to_date: Filter by end date (ISO format)
        limit: Maximum number of results
        offset: Pagination offset
    
    Returns:
        List of audit log entries with employee details
    """
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
            a.id, a.entity_type, a.entity_id, a.action,
            a.old_values, a.new_values, a.performed_by,
            a.ip_address, a.user_agent, a.session_id,
            a.organization_id, a.metadata, a.created_at,
            e.name as performed_by_name,
            e.employee_code as performed_by_code,
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
    
    # Parse JSONB fields from JSON strings to dicts
    import json
    result = []
    for row in rows:
        row_dict = dict(row)
        # Parse JSON fields if they are strings
        if isinstance(row_dict.get('old_values'), str):
            try:
                row_dict['old_values'] = json.loads(row_dict['old_values']) if row_dict['old_values'] else {}
            except:
                row_dict['old_values'] = {}
        if isinstance(row_dict.get('new_values'), str):
            try:
                row_dict['new_values'] = json.loads(row_dict['new_values']) if row_dict['new_values'] else {}
            except:
                row_dict['new_values'] = {}
        if isinstance(row_dict.get('metadata'), str):
            try:
                row_dict['metadata'] = json.loads(row_dict['metadata']) if row_dict['metadata'] else {}
            except:
                row_dict['metadata'] = {}
        result.append(row_dict)
    
    return result


async def count_all(
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    performed_by: Optional[int] = None,
    organization_id: Optional[int] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> int:
    """
    Count audit logs with optional filtering
    
    Returns:
        Total count of matching audit logs
    """
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
    
    query = f"SELECT COUNT(*) as count FROM audit_logs WHERE {where_clause}"
    
    row = await db.query_one(query, *params)
    return row['count'] if row else 0


async def find_by_id(audit_log_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a specific audit log entry by ID
    
    Args:
        audit_log_id: Audit log ID
    
    Returns:
        Audit log entry with employee details
    """
    query = """
        SELECT 
            a.id, a.entity_type, a.entity_id, a.action,
            a.old_values, a.new_values, a.performed_by,
            a.ip_address, a.user_agent, a.session_id,
            a.organization_id, a.metadata, a.created_at,
            e.name as performed_by_name,
            e.employee_code as performed_by_code,
            u.name as organization_name
        FROM audit_logs a
        LEFT JOIN employees e ON a.performed_by = e.id
        LEFT JOIN units u ON a.organization_id = u.id
        WHERE a.id = $1
    """
    
    row = await db.query_one(query, audit_log_id)
    return dict(row) if row else None


async def find_by_entity(entity_type: str, entity_id: int) -> List[Dict[str, Any]]:
    """
    Get all audit logs for a specific entity
    
    Args:
        entity_type: Type of entity
        entity_id: Entity ID
    
    Returns:
        List of audit log entries
    """
    query = """
        SELECT 
            a.id, a.entity_type, a.entity_id, a.action,
            a.old_values, a.new_values, a.performed_by,
            a.ip_address, a.user_agent, a.session_id,
            a.organization_id, a.metadata, a.created_at,
            e.name as performed_by_name,
            e.employee_code as performed_by_code
        FROM audit_logs a
        LEFT JOIN employees e ON a.performed_by = e.id
        WHERE a.entity_type = $1 AND a.entity_id = $2
        ORDER BY a.created_at DESC
    """
    
    rows = await db.query(query, entity_type, entity_id)
    return [dict(row) for row in rows]


async def find_by_user(employee_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Get all audit logs performed by a specific user
    
    Args:
        employee_id: Employee ID
        limit: Maximum number of results
        offset: Pagination offset
    
    Returns:
        List of audit log entries
    """
    query = """
        SELECT 
            a.id, a.entity_type, a.entity_id, a.action,
            a.old_values, a.new_values, a.performed_by,
            a.ip_address, a.user_agent, a.session_id,
            a.organization_id, a.metadata, a.created_at,
            e.name as performed_by_name,
            e.employee_code as performed_by_code
        FROM audit_logs a
        LEFT JOIN employees e ON a.performed_by = e.id
        WHERE a.performed_by = $1
        ORDER BY a.created_at DESC
        LIMIT $2 OFFSET $3
    """
    
    rows = await db.query(query, employee_id, limit, offset)
    return [dict(row) for row in rows]


async def get_statistics() -> Dict[str, Any]:
    """
    Get audit log statistics
    
    Returns:
        Dictionary with statistics (total logs, logs by action, logs by entity type, etc.)
    """
    # Total logs
    total_query = "SELECT COUNT(*) as count FROM audit_logs"
    total_row = await db.query_one(total_query)
    total_logs = total_row['count'] if total_row else 0
    
    # Logs by action
    action_query = """
        SELECT action, COUNT(*) as count
        FROM audit_logs
        GROUP BY action
        ORDER BY count DESC
    """
    action_rows = await db.query(action_query)
    logs_by_action = {row['action']: row['count'] for row in action_rows}
    
    # Logs by entity type
    entity_query = """
        SELECT entity_type, COUNT(*) as count
        FROM audit_logs
        GROUP BY entity_type
        ORDER BY count DESC
    """
    entity_rows = await db.query(entity_query)
    logs_by_entity = {row['entity_type']: row['count'] for row in entity_rows}
    
    # Recent activity (last 24 hours)
    recent_query = """
        SELECT COUNT(*) as count
        FROM audit_logs
        WHERE created_at >= NOW() - INTERVAL '24 hours'
    """
    recent_row = await db.query_one(recent_query)
    recent_logs = recent_row['count'] if recent_row else 0
    
    # Top users
    users_query = """
        SELECT 
            e.name, e.employee_code, COUNT(*) as count
        FROM audit_logs a
        JOIN employees e ON a.performed_by = e.id
        GROUP BY e.id, e.name, e.employee_code
        ORDER BY count DESC
        LIMIT 10
    """
    users_rows = await db.query(users_query)
    top_users = [
        {
            'name': row['name'],
            'employee_code': row['employee_code'],
            'count': row['count']
        }
        for row in users_rows
    ]
    
    return {
        'total_logs': total_logs,
        'logs_by_action': logs_by_action,
        'logs_by_entity': logs_by_entity,
        'recent_logs_24h': recent_logs,
        'top_users': top_users
    }
