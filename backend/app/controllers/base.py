"""
Base Controller Class
Provides common functionality for all API controllers
"""

from abc import ABC
from typing import Any, Dict, List
from fastapi import APIRouter


class BaseController(ABC):
    """
    Abstract base class for all API controllers.
    Provides common router setup and response helpers.
    """
    
    prefix: str = ""
    tags: List[str] = []
    
    def __init__(self):
        """Initialize controller with router"""
        self.router = APIRouter(
            prefix=self.prefix,
            tags=self.tags
        )
        self._register_routes()
    
    def _register_routes(self):
        """
        Register all routes for this controller.
        Override in subclass to define routes.
        """
        pass
    
    @staticmethod
    def success_response(
        data: Any = None,
        message: str = "Success"
    ) -> Dict[str, Any]:
        """
        Create standardized success response.
        
        Args:
            data: Response data payload
            message: Success message
            
        Returns:
            Standardized response dict
        """
        response = {"success": True, "message": message}
        if data is not None:
            response["data"] = data
        return response
    
    @staticmethod
    def paginated_response(
        items: List[Any],
        total: int,
        limit: int,
        offset: int,
        item_key: str = "items"
    ) -> Dict[str, Any]:
        """
        Create standardized paginated response.
        
        Args:
            items: List of items for current page
            total: Total count of all items
            limit: Page size limit
            offset: Current offset
            item_key: Key name for items in response
            
        Returns:
            Paginated response dict
        """
        return {
            item_key: items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(items) < total
        }
