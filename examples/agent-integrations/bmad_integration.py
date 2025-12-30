```python
"""
BMAD Agent Integration Example for DrTrace Analysis

This example shows how to integrate DrTrace's agent interface into a BMAD-style agent.
The agent interface provides natural language query processing that returns formatted
markdown responses.

Usage:
    # In your BMAD agent file or handler:
    from drtrace_service.agent_interface import process_agent_query
    
    # Process a natural language query
    response = await process_agent_query(
        "explain error from 9:00 to 10:00 for app myapp"
    )
    print(response)
"""

import asyncio
import os
import sys

# Add the project root to the path so we can import drtrace_service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from drtrace_service.agent_interface import process_agent_query


async def example_bmad_agent_handler(user_query: str, context: dict = None) -> str:
    """
    Example BMAD agent handler that processes log analysis queries.
    
    This function can be called from a BMAD agent's menu handler or workflow.
    
    Args:
        user_query: Natural language query from the user
        context: Optional context dict (e.g., default application_id)
    
    Returns:
        Formatted markdown response
    """
    # Process the query using DrTrace's agent interface
    response = await process_agent_query(user_query, context)
    return response


async def main():
    """Example usage of the BMAD integration."""
    print("=" * 70)
    print("BMAD Agent Integration Example")
    print("=" * 70)
    print()
    
    # Example 1: Simple error explanation query
    print("Example 1: Explaining an error")
    print("-" * 70)
    query1 = "explain error from 9:00 to 10:00 for app myapp"
    print(f"Query: {query1}")
    print()
    
    context = {
        "application_id": "myapp",  # Default application if not in query
    }
    
    response1 = await process_agent_query(query1, context)
    print(response1)
    print()
    
    # Example 2: Query with relative time
    print("=" * 70)
    print("Example 2: What happened in the last 10 minutes?")
    print("-" * 70)
    query2 = "what happened in the last 10 minutes for app myapp"
    print(f"Query: {query2}")
    print()
    
    response2 = await process_agent_query(query2, context)
    print(response2)
    print()
    
    # Example 3: Query with filters
    print("=" * 70)
    print("Example 3: Errors from a specific module")
    print("-" * 70)
    query3 = "show errors from module data_processor between 2:30 PM and 2:35 PM for app myapp"
    print(f"Query: {query3}")
    print()
    
    response3 = await process_agent_query(query3, context)
    print(response3)


if __name__ == "__main__":
    # Note: Ensure the DrTrace daemon is running before executing this example
    # Start it with: python -m drtrace_service
    
    print("Note: This example requires the DrTrace daemon to be running.")
    print("Start it with: python -m drtrace_service")
    print()
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure:")
        print("1. The DrTrace daemon is running (python -m drtrace_service)")
        print("2. The daemon is accessible at the default host/port (localhost:8001)")
        print("3. You have logs in the database for the specified time range")
        sys.exit(1)


```
"""
BMAD Agent Integration Example for DrTrace Analysis

This example shows how to integrate DrTrace's agent interface into a BMAD-style agent.
The agent interface provides natural language query processing that returns formatted
markdown responses.

Usage:
    # In your BMAD agent file or handler:
    from drtrace_service.agent_interface import process_agent_query
    
    # Process a natural language query
    response = await process_agent_query(
        "explain error from 9:00 to 10:00 for app myapp"
    )
    print(response)
"""

import asyncio
import os
import sys

# Add the project root to the path so we can import drtrace_service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from drtrace_service.agent_interface import process_agent_query


async def example_bmad_agent_handler(user_query: str, context: dict = None) -> str:
    """
    Example BMAD agent handler that processes log analysis queries.
    
    This function can be called from a BMAD agent's menu handler or workflow.
    
    Args:
        user_query: Natural language query from the user
        context: Optional context dict (e.g., default application_id)
    
    Returns:
        Formatted markdown response
    """
    # Process the query using DrTrace's agent interface
    response = await process_agent_query(user_query, context)
    return response


async def main():
    """Example usage of the BMAD integration."""
    print("=" * 70)
    print("BMAD Agent Integration Example")
    print("=" * 70)
    print()
    
    # Example 1: Simple error explanation query
    print("Example 1: Explaining an error")
    print("-" * 70)
    query1 = "explain error from 9:00 to 10:00 for app myapp"
    print(f"Query: {query1}")
    print()
    
    context = {
        "application_id": "myapp",  # Default application if not in query
    }
    
    response1 = await process_agent_query(query1, context)
    print(response1)
    print()
    
    # Example 2: Query with relative time
    print("=" * 70)
    print("Example 2: What happened in the last 10 minutes?")
    print("-" * 70)
    query2 = "what happened in the last 10 minutes for app myapp"
    print(f"Query: {query2}")
    print()
    
    response2 = await process_agent_query(query2, context)
    print(response2)
    print()
    
    # Example 3: Query with filters
    print("=" * 70)
    print("Example 3: Errors from a specific module")
    print("-" * 70)
    query3 = "show errors from module data_processor between 2:30 PM and 2:35 PM for app myapp"
    print(f"Query: {query3}")
    print()
    
    response3 = await process_agent_query(query3, context)
    print(response3)


if __name__ == "__main__":
    # Note: Ensure the DrTrace daemon is running before executing this example
    # Start it with: python -m drtrace_service
    
    print("Note: This example requires the DrTrace daemon to be running.")
    print("Start it with: python -m drtrace_service")
    print()
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure:")
        print("1. The DrTrace daemon is running (python -m drtrace_service)")
        print("2. The daemon is accessible at the default host/port (localhost:8001)")
        print("3. You have logs in the database for the specified time range")
        sys.exit(1)

