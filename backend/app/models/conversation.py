"""
Conversation State Model
OOP class for persistent WhatsApp conversation state
"""

import json
from typing import Optional, Dict, Any, List
from app.models.base import BaseModel
from app.db.database import db


class Conversation(BaseModel):
    """
    Conversation state model with database operations.
    Manages WhatsApp conversation flow state.
    """
    
    table_name = "conversation_states"
    primary_key = "id"
    
    # Instance attributes
    id: int = None
    chat_id: str = None
    employee_id: int = None
    current_step: str = "initial"
    category: str = None
    context: Dict = None
    
    # Joined fields from employee
    employee_name: str = None
    employee_code: str = None
    grade_id: int = None
    grade_code: str = None
    location_id: int = None
    location_code: str = None
    location_name: str = None
    manager_id: int = None
    manager_name: str = None
    
    def __init__(self, data: Dict[str, Any] = None):
        """Initialize conversation from data dict"""
        super().__init__(data)
        # Parse context if it's a string
        if isinstance(self.context, str):
            try:
                self.context = json.loads(self.context)
            except:
                self.context = {}
    
    @classmethod
    async def get_or_create(cls, chat_id: str) -> 'Conversation':
        """Get or create conversation state for a chat"""
        result = await db.query("SELECT * FROM conversation_states WHERE chat_id = $1", chat_id)
        
        if result:
            return cls(result[0])
        
        result = await db.query("""
            INSERT INTO conversation_states (chat_id, current_step, context)
            VALUES ($1, 'initial', '{}') RETURNING *
        """, chat_id)
        
        return cls(result[0])
    
    @classmethod
    async def update(cls, chat_id: str, updates: Dict[str, Any]) -> Optional['Conversation']:
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
        
        return cls(result[0]) if result else None
    
    @classmethod
    async def reset(cls, chat_id: str) -> Optional['Conversation']:
        """Reset conversation state to initial"""
        result = await db.query("""
            UPDATE conversation_states SET
                current_step = 'initial', category = NULL, context = '{}',
                updated_at = CURRENT_TIMESTAMP
            WHERE chat_id = $1 RETURNING *
        """, chat_id)
        
        return cls(result[0]) if result else None
    
    @classmethod
    async def link_employee(cls, chat_id: str, employee_id: int) -> 'Conversation':
        """Link employee to conversation"""
        return await cls.update(chat_id, {'employee_id': employee_id})
    
    @classmethod
    async def get_with_employee(cls, chat_id: str) -> Optional['Conversation']:
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
        
        return cls(result[0]) if result else None
    
    @classmethod
    async def add_receipt(cls, chat_id: str, receipt_data: Dict[str, Any]) -> Optional['Conversation']:
        """Atomically add a receipt to the conversation context"""
        await cls.get_or_create(chat_id)
        
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
        
        return cls(result[0]) if result else None
    
    @classmethod
    async def cleanup(cls, days: int = 7) -> int:
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation to dictionary"""
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'employee_code': self.employee_code,
            'current_step': self.current_step,
            'category': self.category,
            'context': self.context,
            'grade_id': self.grade_id,
            'grade_code': self.grade_code,
            'location_id': self.location_id,
            'location_code': self.location_code,
            'location_name': self.location_name,
            'manager_id': self.manager_id,
            'manager_name': self.manager_name
        }


# Backward compatibility - expose class methods as module functions
async def get_or_create(chat_id: str):
    conv = await Conversation.get_or_create(chat_id)
    return conv.to_dict()

async def update(chat_id: str, updates: dict):
    conv = await Conversation.update(chat_id, updates)
    return conv.to_dict() if conv else None

async def reset(chat_id: str):
    conv = await Conversation.reset(chat_id)
    return conv.to_dict() if conv else None

async def link_employee(chat_id: str, employee_id: int):
    conv = await Conversation.link_employee(chat_id, employee_id)
    return conv.to_dict() if conv else None

async def get_with_employee(chat_id: str):
    conv = await Conversation.get_with_employee(chat_id)
    return conv.to_dict() if conv else None

async def add_receipt(chat_id: str, receipt_data: dict):
    conv = await Conversation.add_receipt(chat_id, receipt_data)
    return conv.to_dict() if conv else None

async def cleanup(days: int = 7):
    return await Conversation.cleanup(days)
