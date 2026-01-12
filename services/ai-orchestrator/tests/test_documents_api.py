"""
RAG 문서 관리 API 테스트
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from app.services.rag_service import Document


class TestDocumentsAPI:
    """문서 관리 API 엔드포인트 테스트"""

    @pytest.fixture
    def mock_rag_service(self):
        """RAG 서비스 모킹"""
        with patch("app.api.v1.documents.get_rag_service") as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def sample_document(self):
        """샘플 문서"""
        return Document(
            id=1,
            doc_type="entity",
            title="Test Document",
            content="This is test content for the document.",
            metadata={"key": "value"},
            status="active",
            has_embedding=True,
            submitted_by="user1",
            submitted_at=datetime(2024, 1, 1, 11, 0, 0),
            reviewed_by="admin",
            reviewed_at=datetime(2024, 1, 1, 12, 0, 0),
            rejection_reason=None,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0)
        )

    @pytest.fixture
    def pending_document(self):
        """승인 대기 문서"""
        return Document(
            id=2,
            doc_type="faq",
            title="Pending Document",
            content="This document is waiting for approval.",
            metadata={},
            status="pending",
            has_embedding=False,
            submitted_by="user2",
            submitted_at=datetime(2024, 1, 2, 10, 0, 0),
            reviewed_by=None,
            reviewed_at=None,
            rejection_reason=None,
            created_at=datetime(2024, 1, 2, 10, 0, 0),
            updated_at=datetime(2024, 1, 2, 10, 0, 0)
        )

    def test_list_documents(self, client, mock_rag_service, sample_document):
        """문서 목록 조회 테스트"""
        mock_rag_service.list_documents = AsyncMock(return_value=([sample_document], 1))

        response = client.get("/api/v1/documents")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Test Document"

    def test_list_documents_with_filters(self, client, mock_rag_service, sample_document):
        """필터링된 문서 목록 조회 테스트"""
        mock_rag_service.list_documents = AsyncMock(return_value=([sample_document], 1))

        response = client.get("/api/v1/documents?doc_type=entity&has_embedding=true&page=1&page_size=10")

        assert response.status_code == 200
        mock_rag_service.list_documents.assert_called_once()
        call_args = mock_rag_service.list_documents.call_args
        assert call_args.kwargs["doc_type"] == "entity"
        assert call_args.kwargs["has_embedding"] == True

    def test_list_documents_with_search(self, client, mock_rag_service, sample_document):
        """검색어로 문서 목록 조회 테스트"""
        mock_rag_service.list_documents = AsyncMock(return_value=([sample_document], 1))

        response = client.get("/api/v1/documents?search=test")

        assert response.status_code == 200
        call_args = mock_rag_service.list_documents.call_args
        assert call_args.kwargs["search_query"] == "test"

    def test_get_document(self, client, mock_rag_service, sample_document):
        """단일 문서 조회 테스트"""
        mock_rag_service.get_document = AsyncMock(return_value=sample_document)

        response = client.get("/api/v1/documents/1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "Test Document"
        assert data["doc_type"] == "entity"

    def test_get_document_not_found(self, client, mock_rag_service):
        """존재하지 않는 문서 조회 테스트"""
        mock_rag_service.get_document = AsyncMock(return_value=None)

        response = client.get("/api/v1/documents/999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_document(self, client, mock_rag_service, sample_document):
        """문서 생성 테스트"""
        mock_rag_service.add_document = AsyncMock(return_value=1)
        mock_rag_service.get_document = AsyncMock(return_value=sample_document)

        response = client.post(
            "/api/v1/documents",
            json={
                "doc_type": "entity",
                "title": "Test Document",
                "content": "This is test content for the document.",
                "metadata": {"key": "value"}
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Document"

    def test_create_document_with_embedding(self, client, mock_rag_service, sample_document):
        """임베딩 포함 문서 생성 테스트 (기본 동작)"""
        mock_rag_service.add_document = AsyncMock(return_value=1)
        mock_rag_service.get_document = AsyncMock(return_value=sample_document)

        response = client.post(
            "/api/v1/documents",
            json={
                "doc_type": "entity",
                "title": "Test Document",
                "content": "This is test content.",
                "skip_embedding": False
            }
        )

        assert response.status_code == 201
        # add_document가 호출되었는지 확인
        mock_rag_service.add_document.assert_called_once()

    def test_update_document(self, client, mock_rag_service, sample_document):
        """문서 수정 테스트"""
        mock_rag_service.document_exists = AsyncMock(return_value=True)
        updated_doc = Document(
            id=1,
            doc_type="entity",
            title="Updated Document",
            content="Updated content",
            metadata={},
            has_embedding=True,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 2, 12, 0, 0)
        )
        mock_rag_service.update_document = AsyncMock(return_value=updated_doc)

        response = client.put(
            "/api/v1/documents/1",
            json={
                "title": "Updated Document",
                "content": "Updated content"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Document"

    def test_update_document_not_found(self, client, mock_rag_service):
        """존재하지 않는 문서 수정 테스트"""
        mock_rag_service.document_exists = AsyncMock(return_value=False)

        response = client.put(
            "/api/v1/documents/999",
            json={"title": "Updated"}
        )

        assert response.status_code == 404

    def test_delete_document(self, client, mock_rag_service):
        """문서 삭제 테스트"""
        mock_rag_service.delete_document = AsyncMock(return_value=True)

        response = client.delete("/api/v1/documents/1")

        assert response.status_code == 204

    def test_delete_document_not_found(self, client, mock_rag_service):
        """존재하지 않는 문서 삭제 테스트"""
        mock_rag_service.delete_document = AsyncMock(return_value=False)

        response = client.delete("/api/v1/documents/999")

        assert response.status_code == 404

    def test_get_stats(self, client, mock_rag_service):
        """문서 통계 조회 테스트"""
        mock_rag_service.get_document_stats = AsyncMock(return_value={
            "total_count": 10,
            "by_type": {"entity": 5, "faq": 5},
            "by_status": {"pending": 2, "active": 7, "rejected": 1},
            "embedding_status": {"with_embedding": 8, "without_embedding": 2},
            "last_updated": datetime(2024, 1, 1, 12, 0, 0)
        })

        response = client.get("/api/v1/documents/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 10
        assert data["by_type"]["entity"] == 5
        assert data["by_status"]["pending"] == 2
        assert data["by_status"]["active"] == 7

    def test_bulk_create_documents(self, client, mock_rag_service):
        """대량 문서 생성 테스트"""
        mock_rag_service.bulk_add_documents = AsyncMock(return_value=(3, []))

        response = client.post(
            "/api/v1/documents/bulk",
            json={
                "documents": [
                    {"doc_type": "entity", "title": "Doc 1", "content": "Content 1"},
                    {"doc_type": "faq", "title": "Doc 2", "content": "Content 2"},
                    {"doc_type": "entity", "title": "Doc 3", "content": "Content 3"}
                ],
                "skip_embedding": True
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success_count"] == 3
        assert data["failed_count"] == 0

    def test_bulk_delete_documents(self, client, mock_rag_service):
        """대량 문서 삭제 테스트"""
        mock_rag_service.bulk_delete_documents = AsyncMock(return_value=(2, [3]))

        response = client.post(
            "/api/v1/documents/bulk/delete",
            json={"ids": [1, 2, 3]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 2
        assert data["failed_count"] == 1
        assert 3 in data["failed_ids"]

    def test_refresh_embeddings(self, client, mock_rag_service):
        """임베딩 갱신 테스트"""
        mock_rag_service.refresh_embeddings = AsyncMock(return_value={
            "processed": 5,
            "updated": 4,
            "failed": 1,
            "remaining": 0
        })

        response = client.post(
            "/api/v1/documents/embeddings/refresh",
            json={
                "force_all": False,
                "batch_size": 50
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["processed"] == 5
        assert data["updated"] == 4

    def test_refresh_embeddings_with_doc_types(self, client, mock_rag_service):
        """특정 타입만 임베딩 갱신 테스트"""
        mock_rag_service.refresh_embeddings = AsyncMock(return_value={
            "processed": 3,
            "updated": 3,
            "failed": 0,
            "remaining": 0
        })

        response = client.post(
            "/api/v1/documents/embeddings/refresh",
            json={
                "force_all": True,
                "doc_types": ["entity", "faq"],
                "batch_size": 100
            }
        )

        assert response.status_code == 200
        call_args = mock_rag_service.refresh_embeddings.call_args
        assert call_args.kwargs["doc_types"] == ["entity", "faq"]

    # === 승인 워크플로우 테스트 ===

    def test_list_pending_documents(self, client, mock_rag_service, pending_document):
        """승인 대기 문서 목록 조회 테스트"""
        mock_rag_service.list_documents = AsyncMock(return_value=([pending_document], 1))

        response = client.get("/api/v1/documents/pending")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "pending"
        # status=pending 필터로 호출되었는지 확인
        call_args = mock_rag_service.list_documents.call_args
        assert call_args.kwargs["status"] == "pending"

    def test_list_documents_with_status_filter(self, client, mock_rag_service, sample_document):
        """상태 필터로 문서 목록 조회 테스트"""
        mock_rag_service.list_documents = AsyncMock(return_value=([sample_document], 1))

        response = client.get("/api/v1/documents?status=active")

        assert response.status_code == 200
        call_args = mock_rag_service.list_documents.call_args
        assert call_args.kwargs["status"] == "active"

    def test_create_document_pending_status(self, client, mock_rag_service, pending_document):
        """문서 생성 시 기본 pending 상태 테스트"""
        mock_rag_service.add_document = AsyncMock(return_value=2)
        mock_rag_service.get_document = AsyncMock(return_value=pending_document)

        response = client.post(
            "/api/v1/documents",
            json={
                "doc_type": "faq",
                "title": "Pending Document",
                "content": "This document is waiting for approval.",
                "submitted_by": "user2"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["submitted_by"] == "user2"

    def test_create_document_with_active_status(self, client, mock_rag_service, sample_document):
        """관리자가 active 상태로 직접 문서 생성 테스트"""
        mock_rag_service.add_document = AsyncMock(return_value=1)
        mock_rag_service.get_document = AsyncMock(return_value=sample_document)

        response = client.post(
            "/api/v1/documents",
            json={
                "doc_type": "entity",
                "title": "Test Document",
                "content": "This is test content for the document.",
                "status": "active",
                "submitted_by": "admin"
            }
        )

        assert response.status_code == 201
        # add_document가 status="active"로 호출되었는지 확인
        call_args = mock_rag_service.add_document.call_args
        assert call_args.kwargs["status"] == "active"

    def test_review_document_approve(self, client, mock_rag_service, pending_document):
        """문서 승인 테스트"""
        mock_rag_service.document_exists = AsyncMock(return_value=True)
        approved_doc = Document(
            id=2,
            doc_type="faq",
            title="Pending Document",
            content="This document is waiting for approval.",
            metadata={},
            status="active",
            has_embedding=True,
            submitted_by="user2",
            submitted_at=datetime(2024, 1, 2, 10, 0, 0),
            reviewed_by="admin",
            reviewed_at=datetime(2024, 1, 2, 11, 0, 0),
            rejection_reason=None,
            created_at=datetime(2024, 1, 2, 10, 0, 0),
            updated_at=datetime(2024, 1, 2, 11, 0, 0)
        )
        mock_rag_service.approve_document = AsyncMock(return_value=approved_doc)

        response = client.post(
            "/api/v1/documents/2/review",
            json={
                "action": "approve",
                "reviewed_by": "admin"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["reviewed_by"] == "admin"
        mock_rag_service.approve_document.assert_called_once_with(2, "admin")

    def test_review_document_reject(self, client, mock_rag_service, pending_document):
        """문서 반려 테스트"""
        mock_rag_service.document_exists = AsyncMock(return_value=True)
        rejected_doc = Document(
            id=2,
            doc_type="faq",
            title="Pending Document",
            content="This document is waiting for approval.",
            metadata={},
            status="rejected",
            has_embedding=False,
            submitted_by="user2",
            submitted_at=datetime(2024, 1, 2, 10, 0, 0),
            reviewed_by="admin",
            reviewed_at=datetime(2024, 1, 2, 11, 0, 0),
            rejection_reason="내용 보완 필요",
            created_at=datetime(2024, 1, 2, 10, 0, 0),
            updated_at=datetime(2024, 1, 2, 11, 0, 0)
        )
        mock_rag_service.reject_document = AsyncMock(return_value=rejected_doc)

        response = client.post(
            "/api/v1/documents/2/review",
            json={
                "action": "reject",
                "reviewed_by": "admin",
                "rejection_reason": "내용 보완 필요"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["rejection_reason"] == "내용 보완 필요"
        mock_rag_service.reject_document.assert_called_once_with(2, "admin", "내용 보완 필요")

    def test_review_document_reject_without_reason(self, client, mock_rag_service):
        """반려 사유 없이 반려 시도 테스트"""
        mock_rag_service.document_exists = AsyncMock(return_value=True)

        response = client.post(
            "/api/v1/documents/2/review",
            json={
                "action": "reject",
                "reviewed_by": "admin"
            }
        )

        assert response.status_code == 400
        assert "rejection_reason" in response.json()["detail"].lower()

    def test_review_document_not_found(self, client, mock_rag_service):
        """존재하지 않는 문서 승인/반려 테스트"""
        mock_rag_service.document_exists = AsyncMock(return_value=False)

        response = client.post(
            "/api/v1/documents/999/review",
            json={
                "action": "approve",
                "reviewed_by": "admin"
            }
        )

        assert response.status_code == 404

    def test_bulk_review_approve(self, client, mock_rag_service):
        """대량 문서 승인 테스트"""
        mock_rag_service.bulk_review_documents = AsyncMock(return_value=(3, []))

        response = client.post(
            "/api/v1/documents/bulk/review",
            json={
                "ids": [1, 2, 3],
                "action": "approve",
                "reviewed_by": "admin"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 3
        assert data["failed_count"] == 0

    def test_bulk_review_reject(self, client, mock_rag_service):
        """대량 문서 반려 테스트"""
        mock_rag_service.bulk_review_documents = AsyncMock(return_value=(2, [3]))

        response = client.post(
            "/api/v1/documents/bulk/review",
            json={
                "ids": [1, 2, 3],
                "action": "reject",
                "reviewed_by": "admin",
                "rejection_reason": "품질 기준 미달"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 2
        assert data["failed_count"] == 1
        assert 3 in data["failed_ids"]

    def test_bulk_review_reject_without_reason(self, client, mock_rag_service):
        """반려 사유 없이 대량 반려 시도 테스트"""
        response = client.post(
            "/api/v1/documents/bulk/review",
            json={
                "ids": [1, 2, 3],
                "action": "reject",
                "reviewed_by": "admin"
            }
        )

        assert response.status_code == 400
        assert "rejection_reason" in response.json()["detail"].lower()


class TestDocumentsValidation:
    """요청 유효성 검사 테스트"""

    def test_create_document_missing_required_fields(self, client):
        """필수 필드 누락 테스트"""
        response = client.post(
            "/api/v1/documents",
            json={"title": "Only title"}
        )

        assert response.status_code == 422

    def test_create_document_invalid_doc_type(self, client):
        """잘못된 문서 타입 테스트"""
        response = client.post(
            "/api/v1/documents",
            json={
                "doc_type": "invalid_type",
                "title": "Test",
                "content": "Content"
            }
        )

        assert response.status_code == 422

    def test_list_documents_invalid_page(self, client):
        """잘못된 페이지 번호 테스트"""
        response = client.get("/api/v1/documents?page=0")

        assert response.status_code == 422

    def test_list_documents_invalid_page_size(self, client):
        """잘못된 페이지 크기 테스트"""
        response = client.get("/api/v1/documents?page_size=101")

        assert response.status_code == 422

    def test_bulk_create_too_many_documents(self, client):
        """대량 생성 제한 초과 테스트"""
        docs = [
            {"doc_type": "entity", "title": f"Doc {i}", "content": f"Content {i}"}
            for i in range(101)
        ]

        response = client.post(
            "/api/v1/documents/bulk",
            json={"documents": docs}
        )

        assert response.status_code == 422

    def test_bulk_delete_too_many_ids(self, client):
        """대량 삭제 제한 초과 테스트"""
        response = client.post(
            "/api/v1/documents/bulk/delete",
            json={"ids": list(range(101))}
        )

        assert response.status_code == 422
