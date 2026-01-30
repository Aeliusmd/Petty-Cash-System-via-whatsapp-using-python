"""
Auth Controller
API routes for authentication
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from app.controllers.base import BaseController
from app.services.auth_service import AuthService
from app.models.employee import Employee
from app.schemas.auth import RequestOTPRequest, VerifyOTPRequest, LoginResponse
from app.utils.auth import require_authenticated
from app import waha_client


class AuthController(BaseController):
    """Controller for authentication endpoints"""
    
    prefix = "/api/auth"
    tags = ["Authentication"]
    
    def __init__(self):
        super().__init__()
    
    def _register_routes(self):
        """Register authentication routes"""
        self.router.post("/request-otp")(self.request_otp)
        self.router.post("/verify-otp", response_model=LoginResponse)(self.verify_otp)
        self.router.post("/logout")(self.logout)
        self.router.get("/me")(self.get_current_user)
    
    async def request_otp(self, data: RequestOTPRequest, request: Request):
        """Request OTP for phone number"""
        service = AuthService(request)
        
        otp_code = await service.request_otp(data.phone_number)
        if not otp_code:
            raise HTTPException(status_code=429, detail="Too many OTP requests. Please wait before trying again.")
        
        # Find employee to get WhatsApp chat ID
        employee = await Employee.find_by_phone(data.phone_number)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        if not employee.whatsapp_chat_id:
            raise HTTPException(
                status_code=400, 
                detail="WhatsApp not linked. Please send a message to the bot first."
            )
        
        # Send OTP via WhatsApp
        message = f"🔐 Your login OTP is: *{otp_code}*\n\nThis code will expire in 5 minutes. Do not share this with anyone."
        try:
            await waha_client.send_text(employee.whatsapp_chat_id, message)
        except Exception as e:
            print(f"⚠️ Failed to send OTP: {e}")
        
        return self.success_response(message="OTP sent successfully")
    
    async def verify_otp(self, data: VerifyOTPRequest, request: Request):
        """Verify OTP and return JWT token"""
        service = AuthService(request)
        
        result = await service.verify_otp(data.phone_number, data.otp_code)
        if not result:
            raise HTTPException(status_code=401, detail="Invalid or expired OTP")
        
        return result
    
    async def logout(self, request: Request, auth: dict = Depends(require_authenticated)):
        """Logout current user"""
        service = AuthService(request)
        await service.logout(auth['employee_id'])
        return self.success_response(message="Logged out successfully")
    
    async def get_current_user(self, auth: dict = Depends(require_authenticated)):
        """Get current authenticated user"""
        employee = await Employee.find_by_id(auth['employee_id'])
        if not employee:
            raise HTTPException(status_code=404, detail="User not found")
        return employee.to_dict()


# Create controller instance and export router
auth_controller = AuthController()
router = auth_controller.router
