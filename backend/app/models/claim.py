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


async def record_status_change(claim_id: int, from_status_code: str, to_status_code: str, 
                                changed_by: int = None, reason: str = None) -> dict:
    """Record a status change in claim_status_history"""
    # Get status IDs
    from_status = await db.query("SELECT id FROM claim_statuses WHERE code = $1", from_status_code) if from_status_code else None
    to_status = await db.query("SELECT id FROM claim_statuses WHERE code = $1", to_status_code)
    
    from_status_id = from_status[0]['id'] if from_status else None
    to_status_id = to_status[0]['id'] if to_status else None
    
    result = await db.query("""
        INSERT INTO claim_status_history (claim_id, from_status_id, to_status_id, changed_by, reason)
        VALUES ($1, $2, $3, $4, $5) RETURNING *
    """, claim_id, from_status_id, to_status_id, changed_by, reason)
    
    return result[0] if result else {}


async def appeal(claim_id: int, employee_id: int, notes: str = None) -> dict:
    """Appeal a rejected claim - changes status to APPEALED with optional notes"""
    # Get the claim to verify it's rejected
    claim = await find_by_id(claim_id)
    if not claim:
        raise ValueError("Claim not found")
    
    if claim.get('status_code') != 'REJECTED':
        raise ValueError("Only rejected claims can be appealed")
    
    # Get APPEALED status ID
    status_result = await db.query("SELECT id FROM claim_statuses WHERE code = 'APPEALED'")
    if not status_result:
        # If APPEALED status doesn't exist, create it
        status_result = await db.query("""
            INSERT INTO claim_statuses (code, name, description, display_order)
            VALUES ('APPEALED', 'Under Appeal', 'Staff has appealed the rejection', 5)
            RETURNING id
        """)
    status_id = status_result[0]['id']
    
    # Record the status change with notes
    reason = f"Staff appealed: {notes}" if notes else "Staff appealed the rejection"
    await record_status_change(claim_id, 'REJECTED', 'APPEALED', employee_id, reason)
    
    # Update the claim
    result = await db.query("""
        UPDATE claims SET status_id = $1, appeal_count = COALESCE(appeal_count, 0) + 1,
                          rejection_reason = NULL, updated_at = CURRENT_TIMESTAMP
        WHERE id = $2 RETURNING *
    """, status_id, claim_id)
    
    return result[0] if result else {}


async def get_history(claim_id: int) -> list[dict]:
    """Get status history for a claim"""
    result = await db.query("""
        SELECT h.*, 
               fs.code as from_status_code, fs.name as from_status_name,
               ts.code as to_status_code, ts.name as to_status_name,
               e.name as changed_by_name
        FROM claim_status_history h
        LEFT JOIN claim_statuses fs ON h.from_status_id = fs.id
        JOIN claim_statuses ts ON h.to_status_id = ts.id
        LEFT JOIN employees e ON h.changed_by = e.id
        WHERE h.claim_id = $1
        ORDER BY h.created_at ASC
    """, claim_id)
    
    return result


async def find_latest_rejected_for_employee(employee_id: int) -> Optional[dict]:
    """Find the most recent rejected claim for an employee"""
    result = await db.query("""
        SELECT c.*, cat.code as category_code, cat.name as category_name,
               s.code as status_code, s.name as status_name
        FROM claims c
        JOIN claim_categories cat ON c.category_id = cat.id
        JOIN claim_statuses s ON c.status_id = s.id
        WHERE c.employee_id = $1 AND s.code = 'REJECTED'
        ORDER BY c.updated_at DESC
        LIMIT 1
    """, employee_id)
    
    return result[0] if result else None
