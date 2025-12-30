"""
Data Service module demonstrating drtrace integration in a data processing layer.
"""

import logging

logger = logging.getLogger("data_service")


class DataService:
    """Data processing service."""
    
    def __init__(self):
        self.service_name = "data-service"
        logger.info(f"Initialized {self.service_name}")
    
    def process_batch(self, batch: list):
        """
        Process a batch of data items.
        
        Args:
            batch: List of data items to process
            
        Raises:
            ValueError: If batch is empty
        """
        if not batch:
            raise ValueError("Cannot process empty batch")
        
        logger.info(
            f"Processing batch of {len(batch)} items",
            extra={
                "service_name": self.service_name,
                "module_name": "data_processor",
                "context": {
                    "batch_size": len(batch),
                }
            }
        )
        
        # Simulate processing
        results = []
        for item in batch:
            processed = self._process_item(item)
            results.append(processed)
        
        logger.info(
            f"Processed {len(results)} items",
            extra={
                "service_name": self.service_name,
                "module_name": "data_processor",
            }
        )
        
        return results
    
    def _process_item(self, item):
        """Process a single item."""
        # Simulate some processing
        return item * 2

