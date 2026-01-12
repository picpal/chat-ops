"""
filter_local 기능 테스트
- filter_local 의도 감지
- 다중 결과 시 clarification 응답
- Core API 호출 없이 필터링
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app


class TestFilterLocalIntentDetection:
    """테스트 1: filter_local 의도 감지"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_query_planner_filter_local(self):
        """filter_local 의도를 반환하는 QueryPlanner mock"""
        with patch("app.api.v1.chat.get_query_planner") as mock:
            mock_instance = MagicMock()
            mock_instance.generate_query_plan = AsyncMock(return_value={
                "entity": "Payment",
                "operation": "list",
                "query_intent": "filter_local",
                "filters": [
                    {"field": "orderName", "operator": "like", "value": "도서"}
                ],
                "limit": 30
            })
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_query_planner_new_query(self):
        """new_query 의도를 반환하는 QueryPlanner mock"""
        with patch("app.api.v1.chat.get_query_planner") as mock:
            mock_instance = MagicMock()
            mock_instance.generate_query_plan = AsyncMock(return_value={
                "entity": "Payment",
                "operation": "list",
                "query_intent": "new_query",
                "limit": 30,
                "orderBy": [{"field": "createdAt", "direction": "desc"}]
            })
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_core_api(self):
        """Core API mock"""
        with patch("app.api.v1.chat.call_core_api") as mock:
            mock.return_value = {
                "requestId": "test-req-001",
                "status": "success",
                "data": {
                    "rows": [
                        {"paymentKey": "pay_001", "orderName": "도서 구매", "amount": 15000, "status": "DONE"},
                        {"paymentKey": "pay_002", "orderName": "전자기기", "amount": 250000, "status": "DONE"},
                        {"paymentKey": "pay_003", "orderName": "도서-프로그래밍", "amount": 35000, "status": "DONE"},
                    ]
                },
                "metadata": {"executionTimeMs": 50, "rowsReturned": 3}
            }
            yield mock

    def test_new_query_calls_core_api(self, client, mock_query_planner_new_query, mock_core_api):
        """
        시나리오: 첫 번째 요청 (새로운 쿼리)
        기대: Core API가 호출됨
        """
        response = client.post("/api/v1/chat", json={
            "message": "최근 거래 30건 조회",
            "conversationHistory": []
        })

        assert response.status_code == 200
        data = response.json()

        # Core API가 호출되었는지 확인
        mock_core_api.assert_called_once()

        # renderSpec 타입 확인 (table이어야 함)
        assert data["renderSpec"]["type"] == "table"
        print(f"\n[Test 1-1] new_query - renderSpec type: {data['renderSpec']['type']}")
        print(f"[Test 1-1] Core API called: {mock_core_api.called}")

    def test_filter_local_returns_filter_spec(self, client, mock_query_planner_filter_local, mock_core_api):
        """
        시나리오: 두 번째 요청 (이전 결과에서 필터링)
        기대:
        - query_intent가 "filter_local"로 감지
        - renderSpec.type이 "filter_local"
        - Core API 호출 없음
        """
        # 이전 대화 기록 (첫 번째 요청 결과가 있는 상태)
        conversation_history = [
            {
                "id": "msg-001",
                "role": "user",
                "content": "최근 거래 30건 조회",
                "timestamp": "2024-01-15T10:00:00Z"
            },
            {
                "id": "msg-002",
                "role": "assistant",
                "content": "결과입니다",
                "timestamp": "2024-01-15T10:00:01Z",
                "queryResult": {
                    "requestId": "req-001",
                    "status": "success",
                    "data": {
                        "rows": [
                            {"paymentKey": "pay_001", "orderName": "도서 구매", "amount": 15000, "status": "DONE"},
                            {"paymentKey": "pay_002", "orderName": "전자기기", "amount": 250000, "status": "DONE"},
                        ]
                    },
                    "metadata": {"rowsReturned": 2}
                },
                "queryPlan": {
                    "entity": "Payment",
                    "operation": "list",
                    "limit": 30
                }
            }
        ]

        response = client.post("/api/v1/chat", json={
            "message": "이전 결과에서 도서 관련만 보여줘",
            "conversationHistory": conversation_history
        })

        assert response.status_code == 200
        data = response.json()

        # 검증 1: renderSpec.type이 "filter_local"인지 확인
        assert data["renderSpec"]["type"] == "filter_local", \
            f"Expected 'filter_local', got '{data['renderSpec']['type']}'"

        # 검증 2: Core API가 호출되지 않았는지 확인
        mock_core_api.assert_not_called()

        # 검증 3: filter 조건이 포함되어 있는지 확인
        assert "filter" in data["renderSpec"]

        print(f"\n[Test 1-2] filter_local - renderSpec type: {data['renderSpec']['type']}")
        print(f"[Test 1-2] Core API called: {mock_core_api.called}")
        print(f"[Test 1-2] filter: {data['renderSpec'].get('filter')}")


class TestMultipleResultsClarification:
    """테스트 2: 다중 결과 시 clarification"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_query_planner_filter_local(self):
        """filter_local 의도를 반환하는 QueryPlanner mock"""
        with patch("app.api.v1.chat.get_query_planner") as mock:
            mock_instance = MagicMock()
            mock_instance.generate_query_plan = AsyncMock(return_value={
                "entity": "Payment",
                "operation": "list",
                "query_intent": "filter_local",
                "filters": [
                    {"field": "status", "operator": "eq", "value": "DONE"}
                ],
                "limit": 20
            })
            mock.return_value = mock_instance
            yield mock_instance

    def test_multiple_results_returns_clarification(self, client, mock_query_planner_filter_local):
        """
        시나리오: 두 개의 조회 결과가 있는 상태에서 "이전 결과에서 DONE 상태만" 요청
        기대: clarification 응답 (어떤 결과를 필터링할지 선택지 제공)
        """
        # 두 개의 결과가 있는 대화 기록
        conversation_history = [
            # 첫 번째 사용자 요청
            {
                "id": "msg-001",
                "role": "user",
                "content": "최근 결제 30건",
                "timestamp": "2024-01-15T10:00:00Z"
            },
            # 첫 번째 응답 (결과 포함)
            {
                "id": "msg-002",
                "role": "assistant",
                "content": "결제 목록입니다",
                "timestamp": "2024-01-15T10:00:05Z",
                "queryResult": {
                    "requestId": "req-001",
                    "status": "success",
                    "data": {
                        "rows": [{"paymentKey": "pay_001", "status": "DONE"}]
                    },
                    "metadata": {"rowsReturned": 30}
                },
                "queryPlan": {"entity": "Payment", "operation": "list", "limit": 30}
            },
            # 두 번째 사용자 요청
            {
                "id": "msg-003",
                "role": "user",
                "content": "환불 20건",
                "timestamp": "2024-01-15T10:01:00Z"
            },
            # 두 번째 응답 (결과 포함)
            {
                "id": "msg-004",
                "role": "assistant",
                "content": "환불 목록입니다",
                "timestamp": "2024-01-15T10:01:05Z",
                "queryResult": {
                    "requestId": "req-002",
                    "status": "success",
                    "data": {
                        "rows": [{"refundKey": "ref_001", "status": "DONE"}]
                    },
                    "metadata": {"rowsReturned": 20}
                },
                "queryPlan": {"entity": "Refund", "operation": "list", "limit": 20}
            }
        ]

        response = client.post("/api/v1/chat", json={
            "message": "이전 결과에서 DONE 상태만",
            "conversationHistory": conversation_history
        })

        assert response.status_code == 200
        data = response.json()

        # 검증: renderSpec.type이 "clarification"인지 확인
        assert data["renderSpec"]["type"] == "clarification", \
            f"Expected 'clarification', got '{data['renderSpec']['type']}'"

        # 검증: clarification 내용 확인
        assert "clarification" in data["renderSpec"]
        assert "question" in data["renderSpec"]["clarification"]
        assert "options" in data["renderSpec"]["clarification"]

        # 검증: 선택지가 2개인지 확인
        options = data["renderSpec"]["clarification"]["options"]
        assert len(options) == 2, f"Expected 2 options, got {len(options)}"

        print(f"\n[Test 2] Multiple results - renderSpec type: {data['renderSpec']['type']}")
        print(f"[Test 2] Question: {data['renderSpec']['clarification']['question']}")
        print(f"[Test 2] Options: {options}")


class TestFilterLocalWithSingleResult:
    """테스트 3: 단일 결과에서 filter_local"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_query_planner_filter_local(self):
        """filter_local 의도를 반환하는 QueryPlanner mock"""
        with patch("app.api.v1.chat.get_query_planner") as mock:
            mock_instance = MagicMock()
            mock_instance.generate_query_plan = AsyncMock(return_value={
                "entity": "Payment",
                "operation": "list",
                "query_intent": "filter_local",
                "filters": [
                    {"field": "status", "operator": "eq", "value": "DONE"}
                ],
                "limit": 30
            })
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_core_api(self):
        """Core API mock - 호출되면 안됨"""
        with patch("app.api.v1.chat.call_core_api") as mock:
            mock.return_value = {
                "requestId": "should-not-be-called",
                "status": "error",
                "error": {"code": "UNEXPECTED", "message": "This should not be called"}
            }
            yield mock

    def test_single_result_returns_filter_local(self, client, mock_query_planner_filter_local, mock_core_api):
        """
        시나리오: 단일 결과가 있는 상태에서 filter_local 요청
        기대:
        - renderSpec.type이 "filter_local"
        - targetResultIndex가 설정됨
        - Core API 호출 없음
        """
        conversation_history = [
            {
                "id": "msg-001",
                "role": "user",
                "content": "최근 결제 30건",
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
                            {"paymentKey": "pay_001", "status": "DONE"},
                            {"paymentKey": "pay_002", "status": "FAILED"},
                            {"paymentKey": "pay_003", "status": "DONE"}
                        ]
                    },
                    "metadata": {"rowsReturned": 3}
                },
                "queryPlan": {"entity": "Payment", "operation": "list", "limit": 30}
            }
        ]

        response = client.post("/api/v1/chat", json={
            "message": "조회된 결과에서 DONE 상태만 보여줘",
            "conversationHistory": conversation_history
        })

        assert response.status_code == 200
        data = response.json()

        # 검증 1: renderSpec.type이 "filter_local"
        assert data["renderSpec"]["type"] == "filter_local", \
            f"Expected 'filter_local', got '{data['renderSpec']['type']}'"

        # 검증 2: targetResultIndex가 있는지 확인
        assert "targetResultIndex" in data["renderSpec"]

        # 검증 3: filter 조건이 포함되어 있는지 확인
        assert "filter" in data["renderSpec"]

        # 검증 4: Core API가 호출되지 않았는지 확인
        mock_core_api.assert_not_called()

        print(f"\n[Test 3] Single result filter_local - renderSpec type: {data['renderSpec']['type']}")
        print(f"[Test 3] targetResultIndex: {data['renderSpec'].get('targetResultIndex')}")
        print(f"[Test 3] filter: {data['renderSpec'].get('filter')}")
        print(f"[Test 3] Core API called: {mock_core_api.called}")


class TestNoResultsFilterLocal:
    """테스트 4: 결과가 없는 상태에서 filter_local 요청"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_query_planner_filter_local(self):
        """filter_local 의도를 반환하는 QueryPlanner mock"""
        with patch("app.api.v1.chat.get_query_planner") as mock:
            mock_instance = MagicMock()
            mock_instance.generate_query_plan = AsyncMock(return_value={
                "entity": "Payment",
                "operation": "list",
                "query_intent": "filter_local",
                "filters": [
                    {"field": "status", "operator": "eq", "value": "DONE"}
                ],
                "limit": 30
            })
            mock.return_value = mock_instance
            yield mock_instance

    def test_no_results_returns_filter_local_with_negative_index(self, client, mock_query_planner_filter_local):
        """
        시나리오: 이전 결과가 없는 상태에서 filter_local 요청
        기대: targetResultIndex가 -1
        """
        # 결과가 없는 대화 기록 (user 메시지만 있음)
        conversation_history = [
            {
                "id": "msg-001",
                "role": "user",
                "content": "안녕하세요",
                "timestamp": "2024-01-15T10:00:00Z"
            },
            {
                "id": "msg-002",
                "role": "assistant",
                "content": "안녕하세요! 무엇을 도와드릴까요?",
                "timestamp": "2024-01-15T10:00:05Z"
                # queryResult 없음
            }
        ]

        response = client.post("/api/v1/chat", json={
            "message": "이전 결과에서 DONE만",
            "conversationHistory": conversation_history
        })

        assert response.status_code == 200
        data = response.json()

        # 검증: filter_local이지만 targetResultIndex가 -1
        assert data["renderSpec"]["type"] == "filter_local"
        assert data["renderSpec"]["targetResultIndex"] == -1

        print(f"\n[Test 4] No results - renderSpec type: {data['renderSpec']['type']}")
        print(f"[Test 4] targetResultIndex: {data['renderSpec'].get('targetResultIndex')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
