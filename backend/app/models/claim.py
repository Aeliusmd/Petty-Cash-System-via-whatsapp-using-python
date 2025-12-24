"""
Claim Model - Database operations for claims and approvals
"""

from typing import Optional
from datetime import date
from app.db.database import db


async def create(data: dict) -> dict:
    """Create a new claim"""
    claim_number = await db.fetchval("SELECT generate_claim_number()")
    
    status_result = await db.query("SELECT id FROM claim_statuses WHERE code = 'PENDING'")
    status_id = status_result[0]['id'] if status_result else 2
    
    result = await db.query("""
        INSERT INTO claims (claim_number, employee_id, category_id, location_id, status_id,
                           claim_type, claim_date, duration_days, user_amount, system_amount,
                           final_amount, description, manager_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13) RETURNING *
    """, claim_number, data.get('employee_id'), data.get('category_id'),
        data.get('location_id'), status_id, data.get('claim_type', 'outright'),
        data.get('claim_date', date.today()), data.get('duration_days', 1),
        data.get('user_amount'), data.get('system_amount'),
        data.get('final_amount') or data.get('system_amount'),
        data.get('description'), data.get('manager_id'))
    
    return result[0]


async def find_by_id(claim_id: int) -> Optional[dict]:
    """Find claim by ID with full details"""
    result = await db.query("""
        SELECT c.*, e.name as employee_name, e.employee_code, g.code as grade_code,
               cat.code as category_code, cat.name as category_name,
               l.name as location_name, s.code as status_code, s.name as status_name,
               m.name as manager_name, a.name as approver_name
        FROM claims c
        JOIN employees e ON c.employee_id = e.id
        LEFT JOIN grades g ON e.grade_id = g.id
        JOIN claim_categories cat ON c.category_id = cat.id
        LEFT JOIN locations l ON c.location_id = l.id
        JOIN claim_statuses s ON c.status_id = s.id
        LEFT JOIN employees m ON c.manager_id = m.id
        LEFT JOIN employees a ON c.approved_by = a.id
        WHERE c.id = $1
    """, claim_id)
    
    return result[0] if result else None


async def find_by_number(claim_number: str) -> Optional[dict]:
    """Find claim by claim number"""
    result = await db.query("SELECT * FROM claims WHERE claim_number = $1", claim_number)
    if result:
        return await find_by_id(result[0]['id'])
    return None


async def find_by_employee(employee_id: int, status: Optional[str] = None,
                           limit: int = 10, offset: int = 0) -> list[dict]:
    """Get claims for an employee"""
    if status:
        return await db.query("""
            SELECT c.*, cat.code as category_code, cat.name as category_name,
                   l.name as location_name, s.code as status_code, s.name as status_name
            FROM claims c
            JOIN claim_categories cat ON c.category_id = cat.id
            LEFT JOIN locations l ON c.location_id = l.id
            JOIN claim_statuses s ON c.status_id = s.id
            WHERE c.employee_id = $1 AND s.code = $2
            ORDER BY c.created_at DESC LIMIT $3 OFFSET $4
        """, employee_id, status, limit, offset)
    else:
        return await db.query("""
            SELECT c.*, cat.code as category_code, cat.name as category_name,
                   l.name as location_name, s.code as status_code, s.name as status_name
            FROM claims c
            JOIN claim_categories cat ON c.category_id = cat.id
            LEFT JOIN locations l ON c.location_id = l.id
            JOIN claim_statuses s ON c.status_id = s.id
            WHERE c.employee_id = $1
            ORDER BY c.created_at DESC LIMIT $2 OFFSET $3
        """, employee_id, limit, offset)


async def find_pending_for_manager(manager_id: int) -> list[dict]:
    """Get pending claims for a manager"""
    return await db.query("""
        SELECT c.*, e.name as employee_name, e.employee_code,
               cat.code as category_code, cat.name as category_name, l.name as location_name
        FROM claims c
        JOIN employees e ON c.employee_id = e.id
        JOIN claim_categories cat ON c.category_id = cat.id
        LEFT JOIN locations l ON c.location_id = l.id
        JOIN claim_statuses s ON c.status_id = s.id
        WHERE c.manager_id = $1 AND s.code = 'PENDING'
        ORDER BY c.created_at ASC
    """, manager_id)


async def approve(claim_id: int, approver_id: int, final_amount: Optional[float] = None) -> dict:
    """Approve a claim"""
    status_result = await db.query("SELECT id FROM claim_statuses WHERE code = 'APPROVED'")
    status_id = status_result[0]['id']
    
    result = await db.query("""
        UPDATE claims SET status_id = $1, approved_by = $2, approved_at = CURRENT_TIMESTAMP,
                          final_amount = COALESCE($3, system_amount), updated_at = CURRENT_TIMESTAMP
        WHERE id = $4 RETURNING *
    """, status_id, approver_id, final_amount, claim_id)
    
    return result[0]


async def reject(claim_id: int, approver_id: int, reason: str) -> dict:
    """Reject a claim"""
    status_result = await db.query("SELECT id FROM claim_statuses WHERE code = 'REJECTED'")
    status_id = status_result[0]['id']
    
    result = await db.query("""
        UPDATE claims SET status_id = $1, approved_by = $2, approved_at = CURRENT_TIMESTAMP,
                          rejection_reason = $3, final_amount = 0, updated_at = CURRENT_TIMESTAMP
        WHERE id = $4 RETURNING *
    """, status_id, approver_id, reason, claim_id)
    
    return result[0]


async def get_stats(employee_id: int) -> dict:
    """Get claim statistics for an employee"""
    result = await db.query("""
        SELECT COUNT(*) as total_claims,
               COUNT(*) FILTER (WHERE s.code = 'APPROVED') as approved_claims,
               COUNT(*) FILTER (WHERE s.code = 'PENDING') as pending_claims,
               COUNT(*) FILTER (WHERE s.code = 'REJECTED') as rejected_claims,
               COALESCE(SUM(c.final_amount) FILTER (WHERE s.code = 'APPROVED'), 0) as total_approved_amount
        FROM claims c
        JOIN claim_statuses s ON c.status_id = s.id
        WHERE c.employee_id = $1
    """, employee_id)
    
    return result[0] if result else {}
