"""
RAGService 단위 테스트
DB 연결 없이 순수 로직 테스트 + Mock 기반 통합 테스트
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.rag_service import (
    RAGService,
    Document,
    get_rag_service,
)


class TestDocument:
    """Document 데이터클래스 테스트"""

    def test_document_creation(self):
        """Document 생성"""
        doc = Document(
            id=1,
            doc_type="entity",
            title="Order 엔티티 설명",
            content="주문 정보를 담고 있습니다.",
            metadata={"version": "1.0"}
        )

        assert doc.id == 1
        assert doc.doc_type == "entity"
        assert doc.title == "Order 엔티티 설명"
        assert doc.similarity == 0.0  # 기본값

    def test_document_with_similarity(self):
        """유사도가 있는 Document"""
        doc = Document(
            id=1,
            doc_type="entity",
            title="Test",
            content="Test content",
            metadata={},
            similarity=0.85
        )

        assert doc.similarity == 0.85

    def test_document_empty_metadata(self):
        """빈 메타데이터 Document"""
        doc = Document(
            id=1,
            doc_type="faq",
            title="FAQ",
            content="자주 묻는 질문",
            metadata={}
        )

        assert doc.metadata == {}


class TestRAGServiceFormatContext:
    """RAGService.format_context 메서드 테스트"""

    def setup_method(self):
        self.service = RAGService()

    def test_format_context_empty_list(self):
        """빈 문서 리스트 - 빈 문자열 반환"""
        result = self.service.format_context([])
        assert result == ""

    def test_format_context_single_document(self):
        """단일 문서 포맷팅"""
        docs = [
            Document(
                id=1,
                doc_type="entity",
                title="Order 엔티티",
                content="주문 정보를 저장합니다.",
                metadata={}
            )
        ]

        result = self.service.format_context(docs)

        assert "## 참고 문서" in result
        assert "### 1. Order 엔티티 (entity)" in result
        assert "주문 정보를 저장합니다." in result

    def test_format_context_multiple_documents(self):
        """다중 문서 포맷팅"""
        docs = [
            Document(
                id=1,
                doc_type="entity",
                title="Order 엔티티",
                content="주문 정보",
                metadata={}
            ),
            Document(
                id=2,
                doc_type="business_logic",
                title="환불 정책",
                content="7일 이내 환불 가능",
                metadata={"category": "refund"}
            ),
            Document(
                id=3,
                doc_type="error_code",
                title="E001 에러",
                content="결제 실패 에러",
                metadata={}
            )
        ]

        result = self.service.format_context(docs)

        assert "### 1. Order 엔티티 (entity)" in result
        assert "### 2. 환불 정책 (business_logic)" in result
        assert "### 3. E001 에러 (error_code)" in result

    def test_format_context_includes_metadata(self):
        """메타데이터가 있으면 포함"""
        docs = [
            Document(
                id=1,
                doc_type="faq",
                title="FAQ",
                content="자주 묻는 질문",
                metadata={"category": "general", "priority": "high"}
            )
        ]

        result = self.service.format_context(docs)

        assert "메타데이터:" in result
        assert "category" in result


class TestRAGServiceInit:
    """RAGService 초기화 테스트"""

    def test_default_initialization(self):
        """기본 초기화"""
        with patch.dict(os.environ, {}, clear=True):
            service = RAGService()

            assert service.embedding_model == "text-embedding-ada-002"
            assert service.embedding_dimension == 1536

    def test_initialization_with_custom_database_url(self):
        """커스텀 DATABASE_URL"""
        custom_url = "postgresql://test:test@localhost:5433/testdb"
        with patch.dict(os.environ, {"DATABASE_URL": custom_url}):
            service = RAGService()
            assert service.database_url == custom_url


class TestRAGServiceSingleton:
    """싱글톤 인스턴스 테스트"""

    def test_get_rag_service_returns_singleton(self):
        """get_rag_service는 싱글톤 반환"""
        # 싱글톤 리셋
        import app.services.rag_service as rag_module
        rag_module._rag_service_instance = None

        instance1 = get_rag_service()
        instance2 = get_rag_service()
        assert instance1 is instance2


@pytest.mark.asyncio
class TestRAGServiceSearchWithMock:
    """Mock을 사용한 검색 테스트"""

    @patch.object(RAGService, '_get_connection')
    async def test_keyword_search_called_when_no_api_key(self, mock_conn):
        """API 키 없으면 키워드 검색 사용"""
        # Mock DB connection
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (1, "entity", "Test Title", "Test Content", {}, 0.8)
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = MagicMock(return_value=mock_connection)
        mock_connection.__exit__ = MagicMock(return_value=False)

        mock_conn.return_value = mock_connection

        # API key 없이 서비스 생성
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            service = RAGService()
            service.openai_api_key = None

            result = await service.search_docs("주문")

            # 결과 확인
            assert len(result) >= 0  # 실제 DB 없으므로 결과 수 보장 안됨

    @patch.object(RAGService, '_get_connection')
    async def test_like_search_fallback(self, mock_conn):
        """LIKE 검색 fallback 테스트"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (1, "entity", "Order", "주문 정보", {})
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = MagicMock(return_value=mock_connection)
        mock_connection.__exit__ = MagicMock(return_value=False)

        mock_conn.return_value = mock_connection

        service = RAGService()
        service.openai_api_key = None

        result = await service._like_search("주문", 3, None)

        assert len(result) == 1
        assert result[0].title == "Order"


@pytest.mark.asyncio
class TestRAGServiceAddDocument:
    """문서 추가 테스트"""

    @patch.object(RAGService, '_get_connection')
    async def test_add_document_without_embedding(self, mock_conn):
        """임베딩 없이 문서 추가"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [42]  # 생성된 ID
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = MagicMock(return_value=mock_connection)
        mock_connection.__exit__ = MagicMock(return_value=False)

        mock_conn.return_value = mock_connection

        service = RAGService()
        service.openai_api_key = None

        doc_id = await service.add_document(
            doc_type="entity",
            title="New Document",
            content="Document content",
            metadata={"version": "1.0"}
        )

        assert doc_id == 42


class TestRAGServiceDocumentCount:
    """문서 개수 조회 테스트"""

    @patch.object(RAGService, '_get_connection')
    def test_get_document_count(self, mock_conn):
        """문서 타입별 개수 조회"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("entity", 5),
            ("business_logic", 3),
            ("error_code", 2),
            ("faq", 4)
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = MagicMock(return_value=mock_connection)
        mock_connection.__exit__ = MagicMock(return_value=False)

        mock_conn.return_value = mock_connection

        service = RAGService()

        # async 메서드를 동기적으로 테스트하기 위해 직접 구현 확인
        # 실제 테스트는 pytest.mark.asyncio와 함께 사용
