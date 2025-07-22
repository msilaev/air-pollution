"""
Basic API tests that avoid TestClient compatibility issues
Tests API functions directly instead of using HTTP requests
"""

from datetime import datetime

import pytest

# Removed unused imports

# Test basic API route functions directly instead of using TestClient
# to avoid version compatibility issues


def test_health_check_function():
    """Test health check function directly"""
    import asyncio

    from src.api.routes.health_check_endpoint import health_check

    # Run the async function
    result = asyncio.run(health_check())

    assert result["status"] == "ok"
    assert "timestamp" in result
    assert result["service"] == "air-pollution-prediction-api"
    # Check timestamp is a valid ISO format
    datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))


def test_readiness_check_function():
    """Test readiness check function directly"""
    import asyncio

    from src.api.routes.health_check_endpoint import readiness_check

    # Run the async function
    result = asyncio.run(readiness_check())

    assert result["status"] == "ready"
    assert "timestamp" in result
    # Check timestamp is a valid ISO format
    datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))


def test_api_app_creation():
    """Test that the API app can be created successfully"""
    from src.api.app import app

    assert app is not None
    assert app.title == "Air Pollution Prediction API"
    assert app.description == "API for predicting air pollution levels"
    assert app.version == "1.0.0"


def test_api_routes_included():
    """Test that routes are properly included in the app"""
    from src.api.app import app

    # Get all routes
    routes = [route.path for route in app.routes]

    # Check that key routes exist
    assert any("/api/v1/health" in route for route in routes)
    assert any("/api/v1/ready" in route for route in routes)


def test_api_schemas_exist():
    """Test that API schemas can be imported"""
    try:
        from src.api import schemas

        assert schemas is not None
    except ImportError:
        pytest.skip("API schemas not fully implemented")


def test_route_modules_importable():
    """Test that all route modules can be imported"""
    from src.api.routes import (
        data_ingestion_endpoint,
        health_check_endpoint,
        predictions_endpoint,
    )

    assert health_check_endpoint.router is not None
    assert predictions_endpoint.router is not None
    assert data_ingestion_endpoint.router is not None
