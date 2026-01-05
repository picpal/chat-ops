"""
Pytest configuration and fixtures
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def mock_core_api():
    """Mock Core API responses"""
    with patch("app.api.v1.chat.call_core_api") as mock:
        mock.return_value = {
            "requestId": "test-123",
            "status": "success",
            "data": {
                "rows": [
                    {"orderId": 1, "customerId": 101, "status": "PAID", "totalAmount": 1000.00}
                ]
            },
            "metadata": {"executionTimeMs": 10}
        }
        yield mock


@pytest.fixture
def mock_rag_service():
    """Mock RAG service"""
    with patch("app.services.query_planner.get_rag_service") as mock:
        mock_instance = MagicMock()
        mock_instance.search_docs.return_value = []
        mock_instance.format_context.return_value = ""
        mock.return_value = mock_instance
        yield mock_instance
