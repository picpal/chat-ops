"""
Main application tests
"""

import pytest


class TestHealthEndpoints:
    """Health check endpoint tests"""

    def test_root_endpoint(self, client):
        """Test root endpoint returns service info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ai-orchestrator"
        assert data["status"] == "UP"
        assert "step" in data  # step 존재 확인 (버전에 무관)

    def test_health_endpoint(self, client):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UP"
        assert "rag_enabled" in data


class TestConfigEndpoint:
    """Config endpoint tests"""

    def test_get_config(self, client):
        """Test config endpoint"""
        response = client.get("/api/v1/chat/config")
        assert response.status_code == 200
        data = response.json()
        assert "core_api_url" in data
        assert "step" in data
