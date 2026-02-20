"""
Event Service
Handles real-time Server-Sent Events (SSE) for frontend updates.
"""
import asyncio
import json
from typing import Dict, Set

class EventService:
    def __init__(self):
        # Map of employee_id to a set of their connection queues
        self.connections: Dict[int, Set[asyncio.Queue]] = {}

    async def subscribe(self, employee_id: int):
        """
        Subscribe to events for a specific employee.
        Returns an AsyncGenerator suitable for StreamingResponse.
        """
        queue = asyncio.Queue()
        
        if employee_id not in self.connections:
            self.connections[employee_id] = set()
        
        self.connections[employee_id].add(queue)
        print(f"📡 New SSE connection for employee {employee_id}. Active: {len(self.connections[employee_id])}")
        
        try:
            while True:
                try:
                    # Wait for an event with a 15-second timeout
                    event_data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    # SSE format requires 'data: ...\n\n'
                    yield f"data: {json.dumps(event_data)}\n\n"
                except asyncio.TimeoutError:
                    # Send a comment as a heartbeat to keep connection alive and flush proxies
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            # Client disconnected
            print(f"📡 SSE client disconnected for employee {employee_id}")
            pass
        finally:
            self._remove_connection(employee_id, queue)

    def _remove_connection(self, employee_id: int, queue: asyncio.Queue):
        if employee_id in self.connections:
            self.connections[employee_id].discard(queue)
            if not self.connections[employee_id]:
                del self.connections[employee_id]

    async def notify_employee(self, employee_id: int, event_type: str, payload: dict = None):
        """
        Notify a specific employee's active browsers to refresh or update.
        """
        if employee_id in self.connections:
            event = {
                "type": event_type,
                "payload": payload or {}
            }
            print(f"📣 Pushing SSE '{event_type}' to employee {employee_id} ({len(self.connections[employee_id])} clients)")
            for queue in self.connections[employee_id]:
                await queue.put(event)

    async def notify_group(self, role_id: int, event_type: str, payload: dict = None):
        """
        Notify all active employees who map to a specific role.
        """
        from app.db.database import db
        # Find all active employees with this role_id
        # We also need to get users who have this role_id OR might have matching role string
        employees = await db.query("SELECT id FROM employees WHERE role_id = $1 OR role = (SELECT code FROM roles WHERE id=$1)", role_id)
        print(f"📣 Pushing SSE '{event_type}' to {len(employees)} employees for role {role_id}")
        for emp in employees:
            await self.notify_employee(emp['id'], event_type, payload)

# Singleton instance
event_service = EventService()
