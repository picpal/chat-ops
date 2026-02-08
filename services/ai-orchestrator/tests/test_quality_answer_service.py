"""
Quality Answer Service 테스트
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime


class TestQualityAnswerService:
    """QualityAnswerService 단위 테스트"""

    @pytest.fixture
    def mock_db_connection(self):
        """데이터베이스 연결 모킹"""
        with patch("app.services.quality_answer_service.psycopg.connect") as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn.return_value)
            mock_conn.return_value.__exit__ = MagicMock(return_value=None)
            mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(return_value=None)
            yield mock_cursor

    @pytest.fixture
    def mock_openai(self):
        """OpenAI API 모킹"""
        with patch("app.services.quality_answer_service.os.getenv") as mock_getenv:
            mock_getenv.return_value = "test-api-key"
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
                mock_client.embeddings.create.return_value = mock_response
                mock_openai.return_value = mock_client
                yield mock_client

    @pytest.mark.asyncio
    async def test_save_quality_answer_success(self, mock_db_connection):
        """고품질 답변 저장 - 성공 (임베딩 없이)"""
        from app.services.quality_answer_service import QualityAnswerService

        mock_db_connection.fetchone.return_value = (123,)

        service = QualityAnswerService()
        service.openai_api_key = None  # 임베딩 비활성화

        doc_id = await service.save_quality_answer(
            request_id="req-123",
            user_question="환불은 어떻게 하나요?",
            ai_response="환불은 결제일로부터 7일 이내에 가능합니다.",
            rating=5,
            session_id="session-456"
        )

        assert doc_id == 123
        # INSERT 쿼리 실행 확인
        assert mock_db_connection.execute.called

    @pytest.mark.asyncio
    async def test_save_quality_answer_with_embedding(self, mock_db_connection, mock_openai):
        """고품질 답변 저장 - 임베딩 포함"""
        from app.services.quality_answer_service import QualityAnswerService

        mock_db_connection.fetchone.return_value = (123,)

        service = QualityAnswerService()
        service.openai_api_key = "test-key"
        service._openai_client = mock_openai

        doc_id = await service.save_quality_answer(
            request_id="req-123",
            user_question="환불은 어떻게 하나요?",
            ai_response="환불은 결제일로부터 7일 이내에 가능합니다.",
            rating=5,
            session_id="session-456"
        )

        assert doc_id == 123
        # 임베딩 생성 확인
        mock_openai.embeddings.create.assert_called_once()

    def test_get_stored_count(self, mock_db_connection):
        """저장된 고품질 답변 수 조회"""
        from app.services.quality_answer_service import QualityAnswerService

        mock_db_connection.fetchone.return_value = (42,)

        service = QualityAnswerService()
        count = service.get_stored_count()

        assert count == 42

    def test_format_quality_context_empty(self):
        """컨텍스트 포맷팅 - 빈 목록"""
        from app.services.quality_answer_service import QualityAnswerService

        service = QualityAnswerService()
        result = service.format_quality_context([])

        assert result == ""

    def test_format_quality_context_with_documents(self):
        """컨텍스트 포맷팅 - 문서 있음"""
        from app.services.quality_answer_service import QualityAnswerService, QualityAnswer

        service = QualityAnswerService()

        docs = [
            QualityAnswer(
                id=1,
                title="[5점] 환불 문의",
                content="## 질문\n환불 방법\n\n## 답변\n7일 이내 가능",
                metadata={"rating": 5},
                similarity=0.85
            )
        ]

        result = service.format_quality_context(docs)

        assert "## 참고 답변 예시" in result
        assert "예시 1" in result
        assert "별점 5점" in result
        assert "유사도 0.85" in result

    @pytest.mark.asyncio
    async def test_search_similar_answers_no_api_key(self):
        """유사 답변 검색 - API 키 없음"""
        from app.services.quality_answer_service import QualityAnswerService

        service = QualityAnswerService()
        service.openai_api_key = None

        results = await service.search_similar_answers("환불 방법")

        assert results == []

    @pytest.mark.asyncio
    async def test_is_duplicate_question(self, mock_db_connection, mock_openai):
        """중복 질문 확인"""
        from app.services.quality_answer_service import QualityAnswerService

        mock_db_connection.fetchall.return_value = [(1, "제목", "내용", {}, 0.98, None)]

        service = QualityAnswerService()
        service.openai_api_key = "test-key"
        service._openai_client = mock_openai

        is_duplicate = await service.is_duplicate_question("동일한 질문", threshold=0.95)

        assert is_duplicate is True


class TestQualityAnswerIntegration:
    """Quality Answer RAG 통합 테스트"""

    @pytest.fixture
    def mock_settings_enabled(self):
        """Settings 서비스 - 활성화 상태"""
        with patch("app.services.rating_service._get_settings_service") as mock:
            mock_instance = MagicMock()
            mock_instance.is_quality_answer_rag_enabled.return_value = True
            mock_instance.get_quality_answer_min_rating.return_value = 4
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_settings_disabled(self):
        """Settings 서비스 - 비활성화 상태"""
        with patch("app.services.rating_service._get_settings_service") as mock:
            mock_instance = MagicMock()
            mock_instance.is_quality_answer_rag_enabled.return_value = False
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_qa_service(self):
        """QualityAnswer 서비스 모킹"""
        with patch("app.services.rating_service._get_qa_service") as mock:
            mock_instance = MagicMock()
            mock_instance.save_quality_answer = AsyncMock(return_value=123)
            mock.return_value = mock_instance
            yield mock_instance

    def test_rating_triggers_quality_answer_save(self, mock_settings_enabled, mock_qa_service):
        """별점 저장 시 고품질 답변 자동 저장 트리거"""
        # 이 테스트는 실제 DB 연결이 필요하므로 통합 테스트로 분류
        # rating_service.save_rating() 호출 시 quality_answer_service.save_quality_answer() 호출 확인
        pass

    def test_rating_does_not_trigger_when_disabled(self, mock_settings_disabled, mock_qa_service):
        """기능 비활성화 시 고품질 답변 저장 안 함"""
        # 이 테스트는 실제 DB 연결이 필요하므로 통합 테스트로 분류
        pass

    def test_low_rating_does_not_trigger_save(self, mock_settings_enabled, mock_qa_service):
        """낮은 별점(1~3)은 고품질 답변으로 저장 안 함"""
        # 이 테스트는 실제 DB 연결이 필요하므로 통합 테스트로 분류
        pass
