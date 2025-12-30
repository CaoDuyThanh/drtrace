"""
Python service component for multi-language example.
"""

import logging

logger = logging.getLogger("python_service")


class PythonService:
    """Python service component."""
    
    def __init__(self):
        self.service_name = "multi-language-app"
        logger.info(
            f"Initialized Python service",
            extra={
                "service_name": self.service_name,
                "module_name": "python_service",
            }
        )
    
    def process_data(self, data: list):
        """
        Process a list of data items.
        
        Args:
            data: List of data items
            
        Raises:
            ValueError: If data is empty
        """
        if not data:
            raise ValueError("Cannot process empty data list")
        
        logger.info(
            f"Processing {len(data)} items",
            extra={
                "service_name": self.service_name,
                "module_name": "python_service",
                "context": {
                    "data_size": len(data),
                }
            }
        )
        
        # Simulate processing
        results = [x * 2 for x in data]
        
        logger.info(
            f"Processed {len(results)} items",
            extra={
                "service_name": self.service_name,
                "module_name": "python_service",
            }
        )
        
        return results
    
    def compute_result(self, a: int, b: int):
        """Compute a result from two integers."""
        logger.info(
            f"Computing result from {a} and {b}",
            extra={
                "service_name": self.service_name,
                "module_name": "python_service",
            }
        )
        
        result = a + b
        
        logger.info(
            f"Computed result: {result}",
            extra={
                "service_name": self.service_name,
                "module_name": "python_service",
            }
        )
        
        return result

