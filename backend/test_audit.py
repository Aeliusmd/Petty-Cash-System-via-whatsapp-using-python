import asyncio
from app.db.database import db

async def main():
    await db.connect()
    
    # Query raw audit_logs data
    rows = await db.query("SELECT id, action, performed_by, entity_type FROM audit_logs ORDER BY created_at DESC LIMIT 20")
    
    print("Raw audit_logs data:")
    for r in rows:
        print(dict(r))
        
    # Query joined data
    from app.models.audit_log import AuditLog
    logs = await AuditLog.find_all(limit=20)
    print("\nJoined AuditLog data:")
    for l in logs:
        print(f"ID: {l.id}, action: {l.action}, performed_by: {l.performed_by}, name: {l.performed_by_name}")
        
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
