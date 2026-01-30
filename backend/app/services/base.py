"""
Base Service Class
Provides common functionality for all service layer classes
"""

from abc import ABC
from typing import Optional, Dict, Any
from fastapi import Request


class BaseService(ABC):
    """
    Abstract base class for all service layer classes.
    Provides common utility methods and request context.
    """
    
    def __init__(self, request: Optional[Request] = None):
        """
        Initialize service with optional request context.
        
        Args:
            request: FastAPI Request object for extracting client info
        """
        self._request = request
    
    @property
    def request(self) -> Optional[Request]:
        """Get the current request"""
        return self._request
    
    def get_client_ip(self) -> str:
        """
        Get client IP address from request.
        
        Returns:
            IP address string or 'unknown'
        """
        if self._request and self._request.client:
            return self._request.client.host
        return "unknown"
    
    def get_user_agent(self) -> str:
        """
        Get user agent from request headers.
        
        Returns:
            User agent string or 'unknown'
        """
        if self._request:
            return self._request.headers.get("user-agent", "unknown")
        return "unknown"
    
    def get_request_info(self) -> Dict[str, str]:
        """
        Get combined request info for audit logging.
        
        Returns:
            Dict with ip_address and user_agent
        """
        return {
            'ip_address': self.get_client_ip(),
            'user_agent': self.get_user_agent()
        }
    
    @staticmethod
    def success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
        """
        Create standard success response.
        
        Args:
            data: Response data
            message: Success message
            
        Returns:
            Standardized success response dict
        """
        return {
            "success": True,
            "message": message,
            "data": data
        }
    
    @staticmethod
    def error_response(message: str, code: int = 400) -> Dict[str, Any]:
        """
        Create standard error response.
        
        Args:
            message: Error message
            code: Error code
            
        Returns:
            Standardized error response dict
        """
        return {
            "success": False,
            "message": message,
            "code": code
        }
