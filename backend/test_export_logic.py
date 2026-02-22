import asyncio
import io
from fastapi.responses import StreamingResponse
from app.db.database import db
from app.controllers.audit_controller import audit_controller

async def main():
    await db.connect()
    try:
        # Simulate auth payload
        auth_payload = {"role": "super_admin"}
        
        response = await audit_controller.export_audit_logs(
            entity_type=None,
            action=None,
            performed_by=None,
            from_date=None,
            to_date=None,
            auth=auth_payload
        )
        print("Response object:", response)
        
        # Try to read the body
        if isinstance(response, StreamingResponse):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            print("Response body preview:", body[:100])
        else:
            print("Unexpected response type!")
            
    except Exception as e:
        print("ERROR occurred:", e)
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
