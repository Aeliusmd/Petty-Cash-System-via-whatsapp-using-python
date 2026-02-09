"""
Quick test script to verify audit log descriptions are working
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.models.audit_log import AuditLog
from app.db.database import db

async def test_audit_descriptions():
    """Test that audit logs include human-friendly descriptions"""
    print("Testing Audit Log Descriptions...\n")
    
    try:
        # Initialize database connection
        await db.connect()
        
        # Fetch a few recent audit logs
        logs = await AuditLog.find_all(limit=5)
        
        if not logs:
            print("WARNING: No audit logs found in database")
            return
        
        print(f"SUCCESS: Found {len(logs)} audit log(s)\n")
        
        # Display each log with its description
        for i, log in enumerate(logs, 1):
            log_dict = log.to_dict()
            print(f"--- Audit Log #{i} ---")
            print(f"ID: {log_dict.get('id')}")
            print(f"Entity Type: {log_dict.get('entity_type')}")
            print(f"Action: {log_dict.get('action')}")
            print(f"Performed By: {log_dict.get('performed_by_name', 'Unknown')}")
            print(f"Created At: {log_dict.get('created_at')}")
            print(f"\nDESCRIPTION: {log_dict.get('description', 'NO DESCRIPTION')}\n")
        
        # Check if descriptions are present
        has_descriptions = all('description' in log.to_dict() for log in logs)
        
        if has_descriptions:
            print("SUCCESS: All audit logs have human-friendly descriptions!")
        else:
            print("FAILURE: Some audit logs are missing descriptions")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(test_audit_descriptions())
