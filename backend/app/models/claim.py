"""
Claim Model
OOP class for claim database operations
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from app.models.base import BaseModel
from app.db.database import db


class Claim(BaseModel):
    """
    Claim model with database operations.
    Handles claims, approvals, rejections, and appeals.
    """
    
    table_name = "claims"
    
    # Instance attributes
    id: int = None
    claim_number: str = None
    employee_id: int = None
    category_id: int = None
    location_id: int = None
    status_id: int = None
    manager_id: int = None
    approved_by: int = None
    claim_type: str = "outright"
    claim_date: date = None
    duration_days: int = 1
    user_amount: float = None
    system_amount: float = None
    final_amount: float = None
    description: str = None
    rejection_reason: str = None
    appeal_count: int = 0
    
    # Joined fields
    employee_name: str = None
    employee_code: str = None
    grade_code: str = None
    category_code: str = None
    category_name: str = None
    location_name: str = None
    status_code: str = None
    status_name: str = None
    manager_name: str = None
    approver_name: str = None
    
    def __init__(self, data: Dict[str, Any] = None):
        """Initialize claim from data dict"""
        super().__init__(data)
    
    @classmethod
    async def create(cls, data: Dict[str, Any]) -> 'Claim':
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
        
        return cls(result[0])
    
    @classmethod
    async def find_by_id(cls, claim_id: int) -> Optional['Claim']:
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
        
        return cls(result[0]) if result else None
    
    @classmethod
    async def find_by_number(cls, claim_number: str) -> Optional['Claim']:
        """Find claim by claim number"""
        result = await db.query("SELECT id FROM claims WHERE claim_number = $1", claim_number)
        if result:
            return await cls.find_by_id(result[0]['id'])
        return None
    
    @classmethod
    async def find_by_employee(cls, employee_id: int = None, status: str = None, limit: int = 10, offset: int = 0, organization_id: int = None) -> tuple[List['Claim'], int]:
        """Find claims by employee, optionally filtered by status and organization. Returns (claims, total_count)"""
        # Base query conditions
        where_conditions = ["1=1"]
        args = []
        arg_idx = 1
        
        if employee_id is not None:
            where_conditions.append(f"c.employee_id = ${arg_idx}")
            args.append(employee_id)
            arg_idx += 1
        
        if status:
            where_conditions.append(f"s.code = ${arg_idx}")
            args.append(status)
            arg_idx += 1
            
        if organization_id:
            where_conditions.append(f"e.organization_id = ${arg_idx}")
            args.append(organization_id)
            arg_idx += 1
            
        where_clause = " AND ".join(where_conditions)
        
        # 1. Get Total Count
        count_query = f"""
            SELECT COUNT(*) 
            FROM claims c
            JOIN employees e ON c.employee_id = e.id
            JOIN claim_statuses s ON c.status_id = s.id
            WHERE {where_clause}
        """
        count_result = await db.query(count_query, *args)
        total_count = count_result[0]['count'] if count_result else 0

        # 2. Get Data
        query = f"""
            SELECT c.*, cat.code as category_code, cat.name as category_name,
                   l.name as location_name, s.code as status_code, s.name as status_name
            FROM claims c
            JOIN employees e ON c.employee_id = e.id
            JOIN claim_categories cat ON c.category_id = cat.id
            LEFT JOIN locations l ON c.location_id = l.id
            JOIN claim_statuses s ON c.status_id = s.id
            WHERE {where_clause}
            ORDER BY c.created_at DESC LIMIT ${arg_idx} OFFSET ${arg_idx+1}
        """
        # Add limit and offset to args
        data_args = args + [limit, offset]
        
        result = await db.query(query, *data_args)
        return [cls(row) for row in result], total_count
    
    @classmethod
    async def find_pending_for_manager(cls, manager_id: int, organization_id: int = None) -> List['Claim']:
        """Find pending claims for manager approval, filtered by organization"""
        query = """
            SELECT c.*, e.name as employee_name, e.employee_code, g.code as grade_code,
                   cat.code as category_code, cat.name as category_name, l.name as location_name
            FROM claims c
            JOIN employees e ON c.employee_id = e.id
            JOIN claim_categories cat ON c.category_id = cat.id
            LEFT JOIN locations l ON c.location_id = l.id
            JOIN claim_statuses s ON c.status_id = s.id
            WHERE c.manager_id = $1 AND s.code = 'PENDING'
        """
        args = [manager_id]
        arg_idx = 2
        
        if organization_id:
            query += f" AND e.organization_id = ${arg_idx}"
            args.append(organization_id)
            arg_idx += 1
            
        query += " ORDER BY c.created_at ASC"
        
        result = await db.query(query, *args)
        return [cls(row) for row in result]
    
    @classmethod
    async def approve(cls, claim_id: int, approver_id: int, final_amount: Optional[float] = None) -> 'Claim':
        """Approve a claim"""
        status_result = await db.query("SELECT id FROM claim_statuses WHERE code = 'APPROVED'")
        status_id = status_result[0]['id']
        
        result = await db.query("""
            UPDATE claims SET status_id = $1, approved_by = $2, approved_at = CURRENT_TIMESTAMP,
                              final_amount = COALESCE($3, system_amount), updated_at = CURRENT_TIMESTAMP
            WHERE id = $4 RETURNING *
        """, status_id, approver_id, final_amount, claim_id)
        
        return cls(result[0])
    
    @classmethod
    async def reject(cls, claim_id: int, approver_id: int, reason: str) -> 'Claim':
        """Reject a claim"""
        status_result = await db.query("SELECT id FROM claim_statuses WHERE code = 'REJECTED'")
        status_id = status_result[0]['id']
        
        result = await db.query("""
            UPDATE claims SET status_id = $1, approved_by = $2, approved_at = CURRENT_TIMESTAMP,
                              rejection_reason = $3, final_amount = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = $4 RETURNING *
        """, status_id, approver_id, reason, claim_id)
        
        return cls(result[0])
    
    @classmethod
    async def appeal(cls, claim_id: int, employee_id: int, notes: str = None) -> 'Claim':
        """Appeal a rejected claim"""
        claim = await cls.find_by_id(claim_id)
        if not claim:
            raise ValueError("Claim not found")
        
        if claim.status_code != 'REJECTED':
            raise ValueError("Only rejected claims can be appealed")
        
        # Get or create APPEALED status
        status_result = await db.query("SELECT id FROM claim_statuses WHERE code = 'APPEALED'")
        if not status_result:
            status_result = await db.query("""
                INSERT INTO claim_statuses (code, name, description, display_order)
                VALUES ('APPEALED', 'Under Appeal', 'Staff has appealed the rejection', 5)
                RETURNING id
            """)
        status_id = status_result[0]['id']
        
        # Record status change
        reason = f"Staff appealed: {notes}" if notes else "Staff appealed the rejection"
        await cls.record_status_change(claim_id, 'REJECTED', 'APPEALED', employee_id, reason)
        
        # Update claim
        result = await db.query("""
            UPDATE claims SET status_id = $1, appeal_count = COALESCE(appeal_count, 0) + 1,
                              rejection_reason = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE id = $2 RETURNING *
        """, status_id, claim_id)
        
        return cls(result[0]) if result else None
    
    @classmethod
    async def record_status_change(
        cls,
        claim_id: int,
        from_status_code: str,
        to_status_code: str,
        changed_by: int = None,
        reason: str = None
    ) -> Dict[str, Any]:
        """Record a status change in claim_status_history"""
        from_status = await db.query("SELECT id FROM claim_statuses WHERE code = $1", from_status_code) if from_status_code else None
        to_status = await db.query("SELECT id FROM claim_statuses WHERE code = $1", to_status_code)
        
        from_status_id = from_status[0]['id'] if from_status else None
        to_status_id = to_status[0]['id'] if to_status else None
        
        result = await db.query("""
            INSERT INTO claim_status_history (claim_id, from_status_id, to_status_id, changed_by, reason)
            VALUES ($1, $2, $3, $4, $5) RETURNING *
        """, claim_id, from_status_id, to_status_id, changed_by, reason)
        
        return result[0] if result else {}
    
    @classmethod
    async def get_dashboard_stats(cls, organization_id: int = None) -> Dict[str, Any]:
        """Get global dashboard statistics, optionally filtered by organization"""
        where_clause = "WHERE 1=1"
        args = []
        if organization_id:
            where_clause += " AND e.organization_id = $1"
            args.append(organization_id)
        
        result = await db.query(f"""
            SELECT COUNT(*) as total_claims,
                   COUNT(*) FILTER (WHERE s.code = 'APPROVED') as approved_claims,
                   COUNT(*) FILTER (WHERE s.code = 'PENDING') as pending_claims,
                   COUNT(*) FILTER (WHERE s.code = 'REJECTED') as rejected_claims,
                   COALESCE(SUM(c.final_amount) FILTER (WHERE s.code = 'APPROVED'), 0) as total_approved_amount,
                   COALESCE(SUM(c.user_amount) FILTER (WHERE s.code = 'PENDING'), 0) as pending_amount
            FROM claims c
            JOIN claim_statuses s ON c.status_id = s.id
            JOIN employees e ON c.employee_id = e.id
            {where_clause}
        """, *args)
        
        return result[0] if result else {}

    @classmethod
    async def get_category_stats(cls, organization_id: int = None) -> List[Dict[str, Any]]:
        """Get spending by category"""
        where_clause = "WHERE s.code = 'APPROVED'"
        args = []
        if organization_id:
            where_clause += " AND e.organization_id = $1"
            args.append(organization_id)
            
        result = await db.query(f"""
            SELECT cat.id as category, cat.name, COUNT(*) as count, SUM(c.final_amount) as total_amount
            FROM claims c
            JOIN claim_categories cat ON c.category_id = cat.id
            JOIN claim_statuses s ON c.status_id = s.id
            JOIN employees e ON c.employee_id = e.id
            {where_clause}
            GROUP BY cat.id, cat.name
            ORDER BY total_amount DESC
        """, *args)
        
        return result

    @classmethod
    async def get_recent_claims(cls, limit: int = 5, organization_id: int = None) -> List[Dict[str, Any]]:
        """Get recent claims for dashboard"""
        where_clause = "WHERE 1=1"
        args = [limit]
        if organization_id:
            where_clause += " AND e.organization_id = $2"
            args.append(organization_id)
            
        result = await db.query(f"""
            SELECT c.claim_number, c.created_at, e.name as employee_name,
                   cat.name as category_name, c.final_amount, s.code as status_code
            FROM claims c
            JOIN employees e ON c.employee_id = e.id
            JOIN claim_categories cat ON c.category_id = cat.id
            JOIN claim_statuses s ON c.status_id = s.id
            {where_clause}
            ORDER BY c.created_at DESC
            LIMIT $1
        """, *args)
        
        return [dict(row) for row in result]

    @classmethod
    async def get_stats(cls, employee_id: int) -> Dict[str, Any]:
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
    
    @classmethod
    async def get_history(cls, claim_id: int) -> List[Dict[str, Any]]:
        """Get status history for a claim"""
        return await db.query("""
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
    
    @classmethod
    async def find_latest_rejected_for_employee(cls, employee_id: int) -> Optional['Claim']:
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
        
        return cls(result[0]) if result else None
    
    @classmethod
    async def delete(cls, claim_id: int, soft: bool = False) -> bool:
        """Delete a claim (always hard delete for claims)"""
        await db.query("DELETE FROM claim_status_history WHERE claim_id = $1", claim_id)
        await db.query("DELETE FROM claim_comments WHERE claim_id = $1", claim_id)
        await db.query("DELETE FROM claim_receipts WHERE claim_id = $1", claim_id)
        result = await db.query("DELETE FROM claims WHERE id = $1 RETURNING id", claim_id)
        return len(result) > 0
    
    @classmethod
    async def add_receipt(
        cls,
        claim_id: int,
        file_path: str,
        file_name: str,
        file_type: str = None,
        file_size: int = None,
        ocr_amount: float = None,
        ocr_raw_text: str = None,
        message_id: str = None,
        vendor: str = None
    ) -> Dict[str, Any]:
        """Add a receipt/attachment to a claim"""
        result = await db.query("""
            INSERT INTO claim_receipts (claim_id, file_path, file_name, file_type, 
                                       file_size, ocr_amount, ocr_raw_text, message_id, vendor)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING *
        """, claim_id, file_path, file_name, file_type, file_size, ocr_amount, ocr_raw_text, message_id, vendor)
        
        return result[0] if result else {}
    
    @classmethod
    async def get_receipts(cls, claim_id: int) -> List[Dict[str, Any]]:
        """Get all receipts for a claim"""
        return await db.query("""
            SELECT id, claim_id, file_path, file_name, file_type, file_size,
                   ocr_amount, uploaded_at, message_id, vendor
            FROM claim_receipts
            WHERE claim_id = $1
            ORDER BY uploaded_at DESC
        """, claim_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert claim to dictionary"""
        return {
            'id': self.id,
            'claim_number': self.claim_number,
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'employee_code': self.employee_code,
            'grade_code': self.grade_code,
            'category_id': self.category_id,
            'category_code': self.category_code,
            'category_name': self.category_name,
            'location_id': self.location_id,
            'location_name': self.location_name,
            'status_id': self.status_id,
            'status_code': self.status_code,
            'status_name': self.status_name,
            'manager_id': self.manager_id,
            'manager_name': self.manager_name,
            'approved_by': self.approved_by,
            'approver_name': self.approver_name,
            'claim_type': self.claim_type,
            'claim_date': self.claim_date.isoformat() if self.claim_date else None,
            'duration_days': self.duration_days,
            'user_amount': float(self.user_amount) if self.user_amount is not None else 0.0,
            'system_amount': float(self.system_amount) if self.system_amount is not None else 0.0,
            'final_amount': float(self.final_amount) if self.final_amount is not None else 0.0,
            'description': self.description,
            'rejection_reason': self.rejection_reason,
            'appeal_count': self.appeal_count,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, (date, datetime)) else str(self.created_at) if self.created_at else None
        }


# Backward compatibility - expose class methods as module functions
async def create(data: dict):
    claim = await Claim.create(data)
    return claim.to_dict()

async def find_by_id(claim_id: int):
    claim = await Claim.find_by_id(claim_id)
    return claim.to_dict() if claim else None

async def find_by_number(claim_number: str):
    claim = await Claim.find_by_number(claim_number)
    return claim.to_dict() if claim else None

async def find_by_employee(employee_id: int, status: str = None, limit: int = 10, offset: int = 0, organization_id: int = None):
    claims = await Claim.find_by_employee(employee_id, status, limit, offset, organization_id)
    return [c.to_dict() for c in claims]

async def find_pending_for_manager(manager_id: int, organization_id: int = None):
    claims = await Claim.find_pending_for_manager(manager_id, organization_id)
    return [c.to_dict() for c in claims]

async def approve(claim_id: int, approver_id: int, final_amount: float = None):
    claim = await Claim.approve(claim_id, approver_id, final_amount)
    return claim.to_dict()

async def reject(claim_id: int, approver_id: int, reason: str):
    claim = await Claim.reject(claim_id, approver_id, reason)
    return claim.to_dict()

async def appeal(claim_id: int, employee_id: int, notes: str = None):
    claim = await Claim.appeal(claim_id, employee_id, notes)
    return claim.to_dict() if claim else {}

async def get_stats(employee_id: int):
    return await Claim.get_stats(employee_id)

async def record_status_change(claim_id: int, from_status_code: str, to_status_code: str, 
                               changed_by: int = None, reason: str = None):
    return await Claim.record_status_change(claim_id, from_status_code, to_status_code, changed_by, reason)

async def get_history(claim_id: int):
    return await Claim.get_history(claim_id)

async def find_latest_rejected_for_employee(employee_id: int):
    claim = await Claim.find_latest_rejected_for_employee(employee_id)
    return claim.to_dict() if claim else None

async def delete(claim_id: int):
    return await Claim.delete(claim_id)

async def add_receipt(claim_id: int, file_path: str, file_name: str, 
                      file_type: str = None, file_size: int = None,
                      ocr_amount: float = None, ocr_raw_text: str = None,
                      message_id: str = None, vendor: str = None):
    return await Claim.add_receipt(claim_id, file_path, file_name, file_type, 
                                   file_size, ocr_amount, ocr_raw_text, message_id, vendor)

async def get_receipts(claim_id: int):
    return await Claim.get_receipts(claim_id)
