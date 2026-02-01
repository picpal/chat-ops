"""
knowledge_answer 기능 테스트
- KNOWLEDGE_ANSWER 의도 분류 (IntentType enum 확인)
- RAG 문서 기반 지식 응답 (문서 있을 때)
- RAG 문서 없을 때 안내 메시지 반환
- Core API 호출 없이 응답
- 참조 문서 메타데이터 포함 확인
- knowledge_answer vs query_needed 경계 분류
- LLM 호출 실패 시 에러 처리
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.services.query_planner import IntentClassification, IntentType


# ============================================
# 테스트 1: IntentType enum에 KNOWLEDGE_ANSWER 존재
# ============================================

class TestKnowledgeAnswerIntentType:
    """KNOWLEDGE_ANSWER가 IntentType enum에 정의되어 있는지 확인"""

    def test_knowledge_answer_in_intent_type(self):
        """IntentType에 KNOWLEDGE_ANSWER가 존재"""
        assert hasattr(IntentType, "KNOWLEDGE_ANSWER")
        assert IntentType.KNOWLEDGE_ANSWER.value == "knowledge_answer"

    def test_intent_classification_accepts_knowledge_answer(self):
        """IntentClassification이 knowledge_answer intent를 수용"""
        result = IntentClassification(
            intent=IntentType.KNOWLEDGE_ANSWER,
            confidence=0.9,
            reasoning="프로세스 설명 요청"
        )
        assert result.intent == IntentType.KNOWLEDGE_ANSWER
        assert result.confidence == 0.9

    def test_all_intent_types_exist(self):
        """모든 IntentType이 정의됨 (6개)"""
        expected = [
            "direct_answer", "query_needed", "filter_local",
            "aggregate_local", "daily_check", "knowledge_answer"
        ]
        actual = [e.value for e in IntentType]
        for intent in expected:
            assert intent in actual, f"Missing intent: {intent}"


# ============================================
# 테스트 2: RAG 문서가 있을 때 지식 응답 반환
# ============================================

class TestKnowledgeAnswerWithDocuments:
    """RAG 문서가 있을 때 knowledge_answer 응답 테스트"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_query_planner_knowledge(self):
        """knowledge_answer 의도를 반환하는 QueryPlanner mock"""
        with patch("app.api.v1.chat.get_query_planner") as mock:
            mock_instance = MagicMock()
            mock_instance.classify_intent = AsyncMock(return_value=IntentClassification(
                intent=IntentType.KNOWLEDGE_ANSWER,
                confidence=0.92,
                reasoning="프로세스/절차 설명 요청"
            ))
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_rag_with_documents(self):
        """RAG 문서를 반환하는 mock"""
        with patch("app.api.v1.chat.get_rag_service") as mock:
            mock_instance = MagicMock()

            # Document 객체 mock 생성
            doc1 = MagicMock()
            doc1.id = 1
            doc1.doc_type = "business_logic"
            doc1.title = "부분취소(부분환불) 처리 프로세스"
            doc1.content = "## 부분취소 프로세스\n\n1단계: 요청 접수\n2단계: 금액 검증\n3단계: PG사 요청"
            doc1.metadata = {"domain": "payment"}
            doc1.similarity = 0.85

            doc2 = MagicMock()
            doc2.id = 2
            doc2.doc_type = "error_code"
            doc2.title = "환불 관련 에러코드"
            doc2.content = "REFUND_AMOUNT_EXCEEDED: 취소 금액이 잔여 결제 금액을 초과"
            doc2.metadata = {"domain": "payment"}
            doc2.similarity = 0.72

            mock_instance.search_docs = AsyncMock(return_value=[doc1, doc2])
            mock_instance.format_context = MagicMock(return_value=(
                "## 참고 문서\n\n"
                "### 1. 부분취소(부분환불) 처리 프로세스 (business_logic)\n"
                "## 부분취소 프로세스\n1단계: 요청 접수\n2단계: 금액 검증\n3단계: PG사 요청\n\n"
                "### 2. 환불 관련 에러코드 (error_code)\n"
                "REFUND_AMOUNT_EXCEEDED: 취소 금액이 잔여 결제 금액을 초과\n"
            ))
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_llm_response(self):
        """LLM 답변 mock"""
        with patch("app.api.v1.chat._generate_knowledge_answer", new_callable=AsyncMock) as mock:
            mock.return_value = (
                "## 부분취소 프로세스\n\n"
                "부분취소는 다음 3단계로 처리됩니다:\n\n"
                "1. **요청 접수**: 가맹점이 API로 부분취소 요청\n"
                "2. **금액 검증**: 누적 취소액 검증\n"
                "3. **PG사 요청**: 원래 PG사에 취소 요청 전달\n\n"
                "### 관련 에러코드\n"
                "- **REFUND_AMOUNT_EXCEEDED**: 취소 금액 초과"
            )
            yield mock

    @pytest.fixture
    def mock_core_api(self):
        """Core API mock - 호출되면 안됨"""
        with patch("app.api.v1.chat.call_core_api") as mock:
            mock.return_value = {
                "requestId": "should-not-be-called",
                "status": "error"
            }
            yield mock

    def test_knowledge_answer_returns_text_type(
        self, client, mock_query_planner_knowledge,
        mock_rag_with_documents, mock_llm_response, mock_core_api
    ):
        """
        시나리오: "부분취소 프로세스 알려줘" 질문
        기대: renderSpec.type이 "text", RAG 문서 기반 마크다운 답변
        """
        response = client.post("/api/v1/chat", json={
            "message": "부분취소 프로세스 알려줘",
            "conversationHistory": []
        })

        assert response.status_code == 200
        data = response.json()

        # 검증 1: renderSpec.type이 "text"
        assert data["renderSpec"]["type"] == "text"

        # 검증 2: 제목이 업무 지식 답변
        assert data["renderSpec"]["title"] == "업무 지식 답변"

        # 검증 3: 마크다운 형식
        assert data["renderSpec"]["text"]["format"] == "markdown"

        # 검증 4: Core API 호출 없음
        mock_core_api.assert_not_called()

    def test_knowledge_answer_contains_references(
        self, client, mock_query_planner_knowledge,
        mock_rag_with_documents, mock_llm_response, mock_core_api
    ):
        """
        시나리오: 지식 응답에 참조 문서 메타데이터 포함
        기대: metadata.references에 문서 제목, 타입, 유사도 포함
        """
        response = client.post("/api/v1/chat", json={
            "message": "부분취소 프로세스 알려줘",
            "conversationHistory": []
        })

        assert response.status_code == 200
        data = response.json()

        metadata = data["renderSpec"]["metadata"]
        assert "references" in metadata
        references = metadata["references"]
        assert len(references) == 2

        # 첫 번째 참조 문서 확인
        assert references[0]["title"] == "부분취소(부분환불) 처리 프로세스"
        assert references[0]["doc_type"] == "business_logic"
        assert references[0]["similarity"] == 0.85

        # 두 번째 참조 문서 확인
        assert references[1]["title"] == "환불 관련 에러코드"
        assert references[1]["doc_type"] == "error_code"

    def test_knowledge_answer_intent_metadata(
        self, client, mock_query_planner_knowledge,
        mock_rag_with_documents, mock_llm_response, mock_core_api
    ):
        """
        시나리오: 응답 메타데이터에 intent 정보 포함
        기대: intent=knowledge_answer, confidence, reasoning 포함
        """
        response = client.post("/api/v1/chat", json={
            "message": "수수료율 기준이 뭐야?",
            "conversationHistory": []
        })

        assert response.status_code == 200
        data = response.json()

        metadata = data["renderSpec"]["metadata"]
        assert metadata["intent"] == "knowledge_answer"
        assert metadata["confidence"] == 0.92
        assert "reasoning" in metadata

    def test_knowledge_answer_query_plan_format(
        self, client, mock_query_planner_knowledge,
        mock_rag_with_documents, mock_llm_response, mock_core_api
    ):
        """
        시나리오: queryPlan에 knowledge_answer intent 포함
        기대: query_intent가 "knowledge_answer"
        """
        response = client.post("/api/v1/chat", json={
            "message": "가상계좌란?",
            "conversationHistory": []
        })

        assert response.status_code == 200
        data = response.json()

        assert data["queryPlan"]["query_intent"] == "knowledge_answer"
        assert "requestId" in data["queryPlan"]

    def test_knowledge_answer_rag_search_called_with_correct_params(
        self, client, mock_query_planner_knowledge,
        mock_rag_with_documents, mock_llm_response, mock_core_api
    ):
        """
        시나리오: RAG 검색이 올바른 파라미터로 호출됨
        기대: k=5, min_similarity=0.4, use_dynamic_params=False
        """
        response = client.post("/api/v1/chat", json={
            "message": "정산 절차 설명해줘",
            "conversationHistory": []
        })

        assert response.status_code == 200

        # RAG search_docs 호출 확인
        mock_rag_with_documents.search_docs.assert_called_once_with(
            query="정산 절차 설명해줘",
            k=5,
            min_similarity=0.4,
            use_dynamic_params=False
        )


# ============================================
# 테스트 3: RAG 문서가 없을 때 안내 메시지 반환
# ============================================

class TestKnowledgeAnswerNoDocuments:
    """RAG 문서가 없을 때 안내 메시지 테스트"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_query_planner_knowledge(self):
        """knowledge_answer 의도를 반환하는 QueryPlanner mock"""
        with patch("app.api.v1.chat.get_query_planner") as mock:
            mock_instance = MagicMock()
            mock_instance.classify_intent = AsyncMock(return_value=IntentClassification(
                intent=IntentType.KNOWLEDGE_ANSWER,
                confidence=0.85,
                reasoning="도메인 개념 설명 요청"
            ))
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_rag_empty(self):
        """빈 결과를 반환하는 RAG mock"""
        with patch("app.api.v1.chat.get_rag_service") as mock:
            mock_instance = MagicMock()
            mock_instance.search_docs = AsyncMock(return_value=[])
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_core_api(self):
        """Core API mock - 호출되면 안됨"""
        with patch("app.api.v1.chat.call_core_api") as mock:
            yield mock

    def test_no_documents_returns_not_found_message(
        self, client, mock_query_planner_knowledge,
        mock_rag_empty, mock_core_api
    ):
        """
        시나리오: RAG 문서가 없을 때
        기대: "관련 문서를 찾지 못했습니다" 메시지 반환
        """
        response = client.post("/api/v1/chat", json={
            "message": "XYZ 프로세스가 뭐야?",
            "conversationHistory": []
        })

        assert response.status_code == 200
        data = response.json()

        # 검증 1: renderSpec.type이 "text"
        assert data["renderSpec"]["type"] == "text"

        # 검증 2: 문서 없음 안내 메시지 포함
        content = data["renderSpec"]["text"]["content"]
        assert "관련 문서를 찾지 못했습니다" in content

        # 검증 3: Core API 호출 없음
        mock_core_api.assert_not_called()

    def test_no_documents_has_correct_title(
        self, client, mock_query_planner_knowledge,
        mock_rag_empty, mock_core_api
    ):
        """
        시나리오: 문서 없을 때 제목 확인
        기대: "문서 검색 결과 없음" 제목
        """
        response = client.post("/api/v1/chat", json={
            "message": "알 수 없는 프로세스",
            "conversationHistory": []
        })

        assert response.status_code == 200
        data = response.json()

        assert data["renderSpec"]["title"] == "문서 검색 결과 없음"

    def test_no_documents_no_references_in_metadata(
        self, client, mock_query_planner_knowledge,
        mock_rag_empty, mock_core_api
    ):
        """
        시나리오: 문서 없을 때 references가 없음
        기대: metadata에 references 키 없음
        """
        response = client.post("/api/v1/chat", json={
            "message": "없는 문서 주제",
            "conversationHistory": []
        })

        assert response.status_code == 200
        data = response.json()

        metadata = data["renderSpec"]["metadata"]
        assert "references" not in metadata


# ============================================
# 테스트 4: LLM 호출 실패 시 에러 처리
# ============================================

class TestKnowledgeAnswerErrorHandling:
    """knowledge_answer 에러 처리 테스트"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_query_planner_knowledge(self):
        """knowledge_answer 의도를 반환하는 QueryPlanner mock"""
        with patch("app.api.v1.chat.get_query_planner") as mock:
            mock_instance = MagicMock()
            mock_instance.classify_intent = AsyncMock(return_value=IntentClassification(
                intent=IntentType.KNOWLEDGE_ANSWER,
                confidence=0.9,
                reasoning="프로세스 설명 요청"
            ))
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_rag_error(self):
        """에러를 발생시키는 RAG mock"""
        with patch("app.api.v1.chat.get_rag_service") as mock:
            mock_instance = MagicMock()
            mock_instance.search_docs = AsyncMock(side_effect=Exception("DB connection failed"))
            mock.return_value = mock_instance
            yield mock_instance

    def test_rag_error_returns_error_response(
        self, client, mock_query_planner_knowledge, mock_rag_error
    ):
        """
        시나리오: RAG 서비스 에러 시
        기대: 에러 메시지를 포함한 text 응답 (500이 아닌 200)
        """
        response = client.post("/api/v1/chat", json={
            "message": "부분취소 프로세스 알려줘",
            "conversationHistory": []
        })

        assert response.status_code == 200
        data = response.json()

        # 검증: 에러 메시지 포함
        assert data["renderSpec"]["type"] == "text"
        content = data["renderSpec"]["text"]["content"]
        assert "오류가 발생했습니다" in content


# ============================================
# 테스트 5: 기존 기능 회귀 테스트 (knowledge_answer가 다른 intent에 영향 없음)
# ============================================

class TestKnowledgeAnswerNoRegression:
    """knowledge_answer 추가가 기존 기능에 영향 없음을 확인"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_core_api(self):
        """Core API mock"""
        with patch("app.api.v1.chat.call_core_api") as mock:
            mock.return_value = {
                "requestId": "test-req-001",
                "status": "success",
                "data": {
                    "rows": [
                        {"paymentKey": "pay_001", "amount": 50000, "status": "DONE"}
                    ]
                },
                "metadata": {"executionTimeMs": 50, "rowsReturned": 1}
            }
            yield mock

    def test_query_needed_still_calls_core_api(self, client, mock_core_api):
        """
        시나리오: query_needed 질문은 기존대로 Core API 호출
        기대: "오늘 결제 건수" → Core API 호출됨
        """
        with patch("app.api.v1.chat.get_query_planner") as mock_planner:
            mock_instance = MagicMock()
            mock_instance.classify_intent = AsyncMock(return_value=IntentClassification(
                intent=IntentType.QUERY_NEEDED,
                confidence=0.95,
                reasoning="데이터 조회 필요"
            ))
            mock_instance.generate_query_plan = AsyncMock(return_value={
                "entity": "Payment",
                "operation": "aggregate",
                "query_intent": "new_query",
                "aggregations": [{"function": "count", "field": "*", "alias": "count"}]
            })
            mock_planner.return_value = mock_instance

            response = client.post("/api/v1/chat", json={
                "message": "오늘 결제 건수",
                "conversationHistory": []
            })

            assert response.status_code == 200

            # Core API가 호출되었는지 확인
            mock_core_api.assert_called_once()

    def test_direct_answer_still_works(self, client, mock_core_api):
        """
        시나리오: direct_answer 질문은 기존대로 LLM 직접 답변
        기대: direct_answer_text 반환, Core API 호출 없음
        """
        with patch("app.api.v1.chat.get_query_planner") as mock_planner:
            mock_instance = MagicMock()
            mock_instance.classify_intent = AsyncMock(return_value=IntentClassification(
                intent=IntentType.DIRECT_ANSWER,
                confidence=0.95,
                reasoning="산술 연산 요청",
                direct_answer_text="$5,000,000의 0.6% 수수료는 **$30,000**입니다."
            ))
            mock_planner.return_value = mock_instance

            response = client.post("/api/v1/chat", json={
                "message": "수수료 0.6% 적용해줘",
                "conversationHistory": []
            })

            assert response.status_code == 200
            data = response.json()

            # direct_answer 응답 확인
            assert data["renderSpec"]["type"] == "text"
            assert "$30,000" in data["renderSpec"]["text"]["content"]

            # Core API 호출 없음
            mock_core_api.assert_not_called()

    def test_daily_check_still_works(self, client, mock_core_api):
        """
        시나리오: daily_check 질문은 기존대로 템플릿 응답
        기대: daily_check_template 모드
        """
        with patch("app.api.v1.chat.get_query_planner") as mock_planner:
            mock_instance = MagicMock()
            mock_instance.classify_intent = AsyncMock(return_value=IntentClassification(
                intent=IntentType.DAILY_CHECK,
                confidence=0.98,
                reasoning="일일점검 키워드 감지",
                check_date="2026-01-28"
            ))
            mock_planner.return_value = mock_instance

            response = client.post("/api/v1/chat", json={
                "message": "일일점검",
                "conversationHistory": []
            })

            assert response.status_code == 200
            data = response.json()

            # daily_check 응답 확인
            assert data["queryPlan"]["mode"] == "daily_check_template"


# ============================================
# 테스트 6: 대화 이력이 있는 상태에서 knowledge_answer
# ============================================

class TestKnowledgeAnswerWithConversationHistory:
    """대화 이력이 있는 상태에서 지식 질문 테스트"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_query_planner_knowledge(self):
        """knowledge_answer 의도를 반환하는 QueryPlanner mock"""
        with patch("app.api.v1.chat.get_query_planner") as mock:
            mock_instance = MagicMock()
            mock_instance.classify_intent = AsyncMock(return_value=IntentClassification(
                intent=IntentType.KNOWLEDGE_ANSWER,
                confidence=0.88,
                reasoning="에러코드 설명 요청"
            ))
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_rag_with_error_doc(self):
        """에러코드 문서를 반환하는 RAG mock"""
        with patch("app.api.v1.chat.get_rag_service") as mock:
            mock_instance = MagicMock()

            doc = MagicMock()
            doc.id = 3
            doc.doc_type = "error_code"
            doc.title = "결제 에러코드 목록"
            doc.content = "INVALID_CARD_NUMBER: 유효하지 않은 카드번호"
            doc.metadata = {"domain": "payment"}
            doc.similarity = 0.78

            mock_instance.search_docs = AsyncMock(return_value=[doc])
            mock_instance.format_context = MagicMock(return_value=(
                "## 참고 문서\n\n"
                "### 1. 결제 에러코드 목록 (error_code)\n"
                "INVALID_CARD_NUMBER: 유효하지 않은 카드번호\n"
            ))
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_llm_response(self):
        """LLM 답변 mock"""
        with patch("app.api.v1.chat._generate_knowledge_answer", new_callable=AsyncMock) as mock:
            mock.return_value = (
                "## INVALID_CARD_NUMBER 에러코드\n\n"
                "**INVALID_CARD_NUMBER**는 유효하지 않은 카드번호가 "
                "입력되었을 때 발생하는 에러입니다."
            )
            yield mock

    @pytest.fixture
    def mock_core_api(self):
        """Core API mock"""
        with patch("app.api.v1.chat.call_core_api") as mock:
            yield mock

    def test_knowledge_answer_after_data_query(
        self, client, mock_query_planner_knowledge,
        mock_rag_with_error_doc, mock_llm_response, mock_core_api
    ):
        """
        시나리오: 결제 조회 후 에러코드 질문
        기대: 이전 조회 결과와 무관하게 RAG 기반 답변 반환
        """
        conversation_history = [
            {
                "id": "msg-001",
                "role": "user",
                "content": "최근 결제 30건 조회",
                "timestamp": "2024-01-15T10:00:00Z"
            },
            {
                "id": "msg-002",
                "role": "assistant",
                "content": "결제 목록입니다",
                "timestamp": "2024-01-15T10:00:05Z",
                "queryResult": {
                    "requestId": "req-001",
                    "status": "success",
                    "data": {
                        "rows": [
                            {"paymentKey": "pay_001", "status": "DONE", "amount": 50000}
                        ]
                    },
                    "metadata": {"rowsReturned": 30}
                },
                "queryPlan": {
                    "entity": "Payment",
                    "operation": "list",
                    "limit": 30
                }
            }
        ]

        response = client.post("/api/v1/chat", json={
            "message": "INVALID_CARD_NUMBER 에러가 뭐야?",
            "conversationHistory": conversation_history
        })

        assert response.status_code == 200
        data = response.json()

        # 검증 1: knowledge_answer 응답
        assert data["renderSpec"]["type"] == "text"
        assert data["queryPlan"]["query_intent"] == "knowledge_answer"

        # 검증 2: Core API 호출 없음 (DB 조회 불필요)
        mock_core_api.assert_not_called()

        # 검증 3: 참조 문서에 에러코드 문서 포함
        references = data["renderSpec"]["metadata"]["references"]
        assert any(ref["doc_type"] == "error_code" for ref in references)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
