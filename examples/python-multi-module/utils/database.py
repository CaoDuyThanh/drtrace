"""
Database utility module demonstrating drtrace integration in a utility layer.
"""

import logging

logger = logging.getLogger("database")


class Database:
    """Database utility for executing queries."""
    
    def __init__(self):
        self.service_name = "data-service"  # Same service as data_service
        logger.info(f"Initialized database utility for {self.service_name}")
    
    def query(self, sql: str):
        """
        Execute a SQL query.
        
        Args:
            sql: SQL query string
            
        Raises:
            ValueError: If SQL is invalid
        """
        logger.info(
            f"Executing query: {sql}",
            extra={
                "service_name": self.service_name,
                "module_name": "database",
                "context": {
                    "sql": sql,
                }
            }
        )
        
        # Simulate SQL validation
        if not sql or not sql.strip().upper().startswith("SELECT"):
            raise ValueError(f"Invalid SQL query: {sql}")
        
        # Simulate query execution
        logger.info(
            "Query executed successfully",
            extra={
                "service_name": self.service_name,
                "module_name": "database",
            }
        )
        
        return {"rows": []}

