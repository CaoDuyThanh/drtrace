"""
API Service module demonstrating drtrace integration in a service layer.
"""

import logging

logger = logging.getLogger("api_service")


class APIService:
    """API service that handles HTTP-like requests."""
    
    def __init__(self):
        self.service_name = "api-service"
        logger.info(f"Initialized {self.service_name}")
    
    def handle_request(self, endpoint: str, params: dict):
        """
        Handle an API request.
        
        Args:
            endpoint: API endpoint path
            params: Request parameters
        """
        logger.info(
            f"Handling request to {endpoint}",
            extra={
                "service_name": self.service_name,
                "module_name": "api_handlers",
                "context": {
                    "endpoint": endpoint,
                    "params": params,
                }
            }
        )
        
        # Simulate endpoint-specific logic
        if endpoint == "/api/users":
            return self._get_user(params.get("user_id"))
        elif endpoint == "/api/data":
            return self._query_data(params.get("query"))
        elif endpoint == "/api/invalid":
            # Intentionally trigger an error
            raise ValueError(f"Invalid endpoint: {endpoint}")
        else:
            raise ValueError(f"Unknown endpoint: {endpoint}")
    
    def _get_user(self, user_id: str):
        """Get user by ID."""
        logger.info(
            f"Fetching user {user_id}",
            extra={
                "service_name": self.service_name,
                "module_name": "api_handlers",
            }
        )
        return {"user_id": user_id, "name": "John Doe"}
    
    def _query_data(self, query: str):
        """Query data using SQL-like query."""
        logger.info(
            f"Executing query: {query}",
            extra={
                "service_name": self.service_name,
                "module_name": "api_handlers",
            }
        )
        return {"results": [1, 2, 3]}

