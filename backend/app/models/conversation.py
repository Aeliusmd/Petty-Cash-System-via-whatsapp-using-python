"""
Conversation State Model - Persistent WhatsApp conversation state
"""

import json
from typing import Optional
from app.db.database import db


async def get_or_create(chat_id: str) -> dict:
    """Get or create conversation state for a chat"""
    result = await db.query("SELECT * FROM conversation_states WHERE chat_id = $1", chat_id)
    
    if result:
        return result[0]
    
    result = await db.query("""
        INSERT INTO conversation_states (chat_id, current_step, context)
        VALUES ($1, 'initial', '{}') RETURNING *
    """, chat_id)
    
    return result[0]


async def update(chat_id: str, updates: dict) -> dict:
    """Update conversation state"""
    current_step = updates.get('current_step')
    category = updates.get('category')
    context = updates.get('context')
    employee_id = updates.get('employee_id')
    
    context_json = json.dumps(context) if context is not None else None
    
    result = await db.query("""
        UPDATE conversation_states SET
            current_step = COALESCE($2, current_step),
            category = COALESCE($3, category),
            context = COALESCE($4::jsonb, context),
            employee_id = COALESCE($5, employee_id),
            updated_at = CURRENT_TIMESTAMP
        WHERE chat_id = $1 RETURNING *
    """, chat_id, current_step, category, context_json, employee_id)
    
    if not result:
        result = await db.query("""
            INSERT INTO conversation_states (chat_id, current_step, category, context, employee_id)
            VALUES ($1, $2, $3, $4::jsonb, $5) RETURNING *
        """, chat_id, current_step or 'initial', category, json.dumps(context or {}), employee_id)
    
    return result[0] if result else None


async def reset(chat_id: str) -> Optional[dict]:
    """Reset conversation state"""
    result = await db.query("""
        UPDATE conversation_states SET
            current_step = 'initial', category = NULL, context = '{}',
            updated_at = CURRENT_TIMESTAMP
        WHERE chat_id = $1 RETURNING *
    """, chat_id)
    
    return result[0] if result else None


async def link_employee(chat_id: str, employee_id: int) -> dict:
    """Link employee to conversation"""
    return await update(chat_id, {'employee_id': employee_id})


async def get_with_employee(chat_id: str) -> Optional[dict]:
    """Get conversation with employee details"""
    result = await db.query("""
        SELECT cs.*, e.name as employee_name, e.employee_code, e.grade_id,
               g.code as grade_code, e.location_id, l.code as location_code,
               l.name as location_name, e.manager_id, m.name as manager_name
        FROM conversation_states cs
        LEFT JOIN employees e ON cs.employee_id = e.id
        LEFT JOIN grades g ON e.grade_id = g.id
        LEFT JOIN locations l ON e.location_id = l.id
        LEFT JOIN employees m ON e.manager_id = m.id
        WHERE cs.chat_id = $1
    """, chat_id)
    
    return result[0] if result else None


async def add_receipt(chat_id: str, receipt_data: dict) -> Optional[dict]:
    """
    Atomically add a receipt to the conversation context
    Uses PostgreSQL JSONB operations to prevent race conditions
    """
    # Ensure the conversation exists first
    await get_or_create(chat_id)
    
    # Atomically append receipt to the receipts array in context
    result = await db.query("""
        UPDATE conversation_states SET
            context = jsonb_set(
                context,
                '{receipts}',
                COALESCE(context->'receipts', '[]'::jsonb) || $2::jsonb,
                true
            ),
            updated_at = CURRENT_TIMESTAMP
        WHERE chat_id = $1
        RETURNING *
    """, chat_id, json.dumps([receipt_data]))
    
    return result[0] if result else None


async def cleanup(days: int = 7) -> int:
    """Delete old inactive conversations"""
    result = await db.execute(f"""
        DELETE FROM conversation_states
        WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '{days} days'
          AND employee_id IS NULL
    """)
    
    if result and 'DELETE' in result:
        try:
            return int(result.split(' ')[1])
        except:
            return 0
    return 0
