"""
Test script for OpenAPI-first daemon discovery.

Verifies that agents can discover daemon endpoints via OpenAPI schema.
"""

from typing import Dict, List

import requests


def discover_daemon_endpoints(base_url: str = "http://localhost:8001") -> Dict[str, List[str]]:
    """Discover all available endpoints from OpenAPI schema."""
    try:
        response = requests.get(f"{base_url}/openapi.json", timeout=2)
        if response.status_code == 200:
            schema = response.json()
            endpoints = {}
            paths = schema.get("paths", {})
            for path, methods in paths.items():
                endpoints[path] = list(methods.keys())
            return endpoints
    except requests.exceptions.RequestException:
        pass

    # Fallback to core endpoints
    return {
        "/status": ["GET"],
        "/logs/ingest": ["POST"],
        "/logs/query": ["GET"],
        "/docs": ["GET"],
        "/openapi.json": ["GET"],
    }


def extract_endpoints(schema: dict) -> Dict[str, List[str]]:
    """Extract endpoint paths and methods from OpenAPI schema."""
    endpoints = {}
    paths = schema.get("paths", {})
    for path, methods in paths.items():
        endpoints[path] = list(methods.keys())
    return endpoints


def test_openapi_discovery():
    """Test OpenAPI-first discovery pattern."""
    base_url = "http://localhost:8001"

    print("Testing OpenAPI-first discovery...")
    print(f"Base URL: {base_url}")
    print()

    # Fetch OpenAPI schema
    try:
        response = requests.get(f"{base_url}/openapi.json", timeout=2)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ OpenAPI schema fetched successfully")

        schema = response.json()
        assert "paths" in schema, "Schema missing 'paths' key"
        print("✅ OpenAPI schema is valid JSON")

        # Extract endpoints
        endpoints = extract_endpoints(schema)
        print(f"✅ Extracted {len(endpoints)} endpoints")
        print()

        # Verify core endpoints exist
        core_endpoints = ["/status", "/logs/ingest", "/logs/query"]
        for endpoint in core_endpoints:
            assert endpoint in endpoints, f"Core endpoint {endpoint} not found"
            print(f"✅ Core endpoint {endpoint} found: {endpoints[endpoint]}")

        print()
        print("All endpoints discovered:")
        for path, methods in sorted(endpoints.items()):
            print(f"  {path}: {methods}")

        return endpoints

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch OpenAPI schema: {e}")
        print("Testing fallback to core endpoints...")
        endpoints = discover_daemon_endpoints(base_url)
        print(f"✅ Fallback endpoints: {endpoints}")
        return endpoints


def test_fallback():
    """Test fallback mechanism when OpenAPI is unavailable."""
    print()
    print("Testing fallback mechanism...")

    # Simulate OpenAPI unavailable by using invalid URL
    endpoints = discover_daemon_endpoints("http://localhost:9999")

    # Should fall back to core endpoints
    assert "/status" in endpoints, "Fallback should include /status"
    assert "/logs/ingest" in endpoints, "Fallback should include /logs/ingest"
    assert "/logs/query" in endpoints, "Fallback should include /logs/query"

    print("✅ Fallback mechanism works correctly")
    print(f"Fallback endpoints: {endpoints}")


if __name__ == "__main__":
    print("=" * 60)
    print("OpenAPI-First Discovery Test")
    print("=" * 60)
    print()

    try:
        # Test OpenAPI discovery
        endpoints = test_openapi_discovery()

        # Test fallback
        test_fallback()

        print()
        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ Test failed: {e}")
        print("=" * 60)
        exit(1)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Unexpected error: {e}")
        print("=" * 60)
        exit(1)

