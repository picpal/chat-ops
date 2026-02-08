"""
Settings Service 테스트
"""

import pytest
from unittest.mock import patch, MagicMock
import json


class TestSettingsService:
    """SettingsService 단위 테스트"""

    @pytest.fixture
    def mock_db_connection(self):
        """데이터베이스 연결 모킹"""
        with patch("app.services.settings_service.psycopg.connect") as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn.return_value)
            mock_conn.return_value.__exit__ = MagicMock(return_value=None)
            mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(return_value=None)
            yield mock_cursor

    def test_get_setting_found(self, mock_db_connection):
        """설정 조회 - 성공"""
        from app.services.settings_service import SettingsService

        # Mock DB 결과
        mock_db_connection.fetchone.return_value = (
            "quality_answer_rag",
            {"enabled": True, "minRating": 4},
            "Quality Answer RAG 기능",
            MagicMock(isoformat=lambda: "2026-01-01T00:00:00")
        )

        service = SettingsService()
        result = service.get_setting("quality_answer_rag")

        assert result is not None
        assert result["key"] == "quality_answer_rag"
        assert result["value"]["enabled"] is True
        assert result["value"]["minRating"] == 4

    def test_get_setting_not_found(self, mock_db_connection):
        """설정 조회 - 없음"""
        from app.services.settings_service import SettingsService

        mock_db_connection.fetchone.return_value = None

        service = SettingsService()
        result = service.get_setting("nonexistent_key")

        assert result is None

    def test_is_quality_answer_rag_enabled_default(self, mock_db_connection):
        """Quality Answer RAG 활성화 여부 - 기본값"""
        from app.services.settings_service import SettingsService

        mock_db_connection.fetchone.return_value = None

        service = SettingsService()
        result = service.is_quality_answer_rag_enabled()

        assert result is True  # 기본값은 활성화

    def test_is_quality_answer_rag_enabled_true(self, mock_db_connection):
        """Quality Answer RAG 활성화 여부 - 활성화"""
        from app.services.settings_service import SettingsService

        mock_db_connection.fetchone.return_value = (
            "quality_answer_rag",
            {"enabled": True, "minRating": 4},
            "설명",
            MagicMock(isoformat=lambda: "2026-01-01T00:00:00")
        )

        service = SettingsService()
        result = service.is_quality_answer_rag_enabled()

        assert result is True

    def test_is_quality_answer_rag_enabled_false(self, mock_db_connection):
        """Quality Answer RAG 활성화 여부 - 비활성화"""
        from app.services.settings_service import SettingsService

        mock_db_connection.fetchone.return_value = (
            "quality_answer_rag",
            {"enabled": False, "minRating": 4},
            "설명",
            MagicMock(isoformat=lambda: "2026-01-01T00:00:00")
        )

        service = SettingsService()
        result = service.is_quality_answer_rag_enabled()

        assert result is False

    def test_get_quality_answer_min_rating_default(self, mock_db_connection):
        """최소 별점 기준 - 기본값"""
        from app.services.settings_service import SettingsService

        mock_db_connection.fetchone.return_value = None

        service = SettingsService()
        result = service.get_quality_answer_min_rating()

        assert result == 4  # 기본값

    def test_get_quality_answer_min_rating_custom(self, mock_db_connection):
        """최소 별점 기준 - 사용자 설정"""
        from app.services.settings_service import SettingsService

        mock_db_connection.fetchone.return_value = (
            "quality_answer_rag",
            {"enabled": True, "minRating": 5},
            "설명",
            MagicMock(isoformat=lambda: "2026-01-01T00:00:00")
        )

        service = SettingsService()
        result = service.get_quality_answer_min_rating()

        assert result == 5


class TestSettingsAPI:
    """Settings API 통합 테스트"""

    @pytest.fixture
    def client(self):
        """FastAPI test client"""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    @pytest.fixture
    def mock_settings_service(self):
        """SettingsService 모킹"""
        with patch("app.api.v1.settings.get_settings_service") as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_qa_service(self):
        """QualityAnswerService 모킹"""
        with patch("app.api.v1.settings.get_quality_answer_service") as mock:
            mock_instance = MagicMock()
            mock_instance.get_stored_count.return_value = 42
            mock.return_value = mock_instance
            yield mock_instance

    def test_get_quality_answer_rag_status(self, client, mock_settings_service, mock_qa_service):
        """Quality Answer RAG 상태 조회 API"""
        mock_settings_service.get_quality_answer_rag_status.return_value = {
            "enabled": True,
            "minRating": 4,
            "storedCount": 42,
            "lastUpdated": "2026-01-01T00:00:00"
        }

        response = client.get("/api/v1/settings/quality-answer-rag/status")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["minRating"] == 4
        assert data["storedCount"] == 42

    def test_update_quality_answer_rag(self, client, mock_settings_service):
        """Quality Answer RAG 설정 업데이트 API"""
        mock_settings_service.update_setting.return_value = {
            "key": "quality_answer_rag",
            "value": {"enabled": False, "minRating": 4},
            "description": "설명",
            "updatedAt": "2026-01-01T00:00:00"
        }

        response = client.put(
            "/api/v1/settings/quality-answer-rag",
            json={"enabled": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "quality_answer_rag"
        assert data["value"]["enabled"] is False

    def test_update_quality_answer_rag_no_values(self, client):
        """Quality Answer RAG 설정 업데이트 - 값 없음"""
        response = client.put(
            "/api/v1/settings/quality-answer-rag",
            json={}
        )

        assert response.status_code == 400
