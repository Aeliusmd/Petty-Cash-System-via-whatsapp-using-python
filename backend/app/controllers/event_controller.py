"""
Event Controller
Exposes Server-Sent Events (SSE) endpoint for real-time frontend updates.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from app.services.event_service import event_service
from app.utils.jwt_utils import verify_access_token

router = APIRouter(prefix="/api/events", tags=["Events"])

async def get_user_from_query_token(token: str = Query(None)):
    """
    Dependency to authenticate via query parameter since native EventSource 
    in browsers cannot send Authorization headers.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
        
    return payload

@router.get("/stream")
async def stream_events(auth: dict = Depends(get_user_from_query_token)):
    """
    Subscribe to real-time events for the authenticated employee.
    """
    employee_id = auth.get('employee_id')
    if not employee_id:
        raise HTTPException(status_code=400, detail="Invalid token payload")

    # Return the generator directly as a StreamingResponse
    return StreamingResponse(
        event_service.subscribe(employee_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no" # Disable buffering in proxy servers like Nginx
        }
    )
