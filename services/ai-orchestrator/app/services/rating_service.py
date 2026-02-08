"""
별점 평가 DB 저장/조회 서비스
"""

import json
import os
import logging
import asyncio
from typing import Optional
from datetime import datetime

import psycopg

logger = logging.getLogger(__name__)

# Quality Answer RAG 서비스 lazy import (순환 의존성 방지)
_qa_service = None
_settings_service = None


def _get_qa_service():
    """QualityAnswerService lazy loading"""
    global _qa_service
    if _qa_service is None:
        from app.services.quality_answer_service import get_quality_answer_service
        _qa_service = get_quality_answer_service()
    return _qa_service


def _get_settings_service():
    """SettingsService lazy loading"""
    global _settings_service
    if _settings_service is None:
        from app.services.settings_service import get_settings_service
        _settings_service = get_settings_service()
    return _settings_service


class RatingService:
    """별점 평가 DB 서비스"""

    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://chatops_user:chatops_pass@localhost:5432/chatops"
        )

    def _get_connection(self):
        """PostgreSQL 연결 생성"""
        return psycopg.connect(self.database_url)

    def _fetch_conversations_snapshot(self, cur, session_id: str, request_id: str) -> Optional[str]:
        """평가 대상 메시지 기준 이전 6개 메시지를 조회하여 JSON 문자열로 반환"""
        # 현재 메시지의 created_at 기준점
        cur.execute(
            "SELECT created_at FROM chat_messages WHERE message_id = %s",
            (request_id,),
        )
        msg_row = cur.fetchone()
        if msg_row is None:
            return None

        ref_time = msg_row[0]

        # 해당 시점 이전의 메시지 6개 (user 3 + assistant 3)
        cur.execute(
            """
            SELECT role, content, created_at
            FROM chat_messages
            WHERE session_id = %s AND created_at <= %s
            ORDER BY created_at DESC
            LIMIT 6
            """,
            (session_id, ref_time),
        )
        rows = list(reversed(cur.fetchall()))

        # user-assistant 쌍으로 묶기
        conversations = []
        i = 0
        while i < len(rows) - 1:
            if rows[i][0] == 'user' and rows[i + 1][0] == 'assistant':
                conversations.append({
                    "userQuestion": rows[i][1] or "",
                    "aiResponse": rows[i + 1][1] or "",
                    "createdAt": rows[i + 1][2].isoformat() if rows[i + 1][2] else None,
                })
                i += 2
            else:
                i += 1

        return json.dumps(conversations, ensure_ascii=False) if conversations else None

    def _live_query_conversations(self, cur, session_id: str, ref_time) -> list[dict]:
        """chat_messages에서 실시간으로 대화 이력 조회"""
        cur.execute(
            """
            SELECT role, content, created_at
            FROM chat_messages
            WHERE session_id = %s AND created_at <= %s
            ORDER BY created_at DESC
            LIMIT 6
            """,
            (session_id, ref_time),
        )
        rows = list(reversed(cur.fetchall()))

        conversations = []
        i = 0
        while i < len(rows) - 1:
            if rows[i][0] == 'user' and rows[i + 1][0] == 'assistant':
                conversations.append({
                    "userQuestion": rows[i][1] or "",
                    "aiResponse": rows[i + 1][1] or "",
                    "createdAt": rows[i + 1][2].isoformat() if rows[i + 1][2] else None,
                })
                i += 2
            else:
                i += 1

        return conversations

    def save_rating(
        self,
        request_id: str,
        rating: int,
        feedback: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> dict:
        """별점 저장 (upsert) - 대화 이력 스냅샷 포함"""
        if not session_id:
            raise ValueError("session_id is required for saving a rating")
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # 대화 이력 스냅샷 생성 (실패해도 rating 저장은 진행)
                conversations_json = None
                if session_id:
                    try:
                        conversations_json = self._fetch_conversations_snapshot(
                            cur, session_id, request_id
                        )
                    except Exception as e:
                        logger.warning(f"Failed to create conversations snapshot: {e}")
                        conversations_json = None

                cur.execute(
                    """
                    INSERT INTO message_ratings (request_id, session_id, rating, feedback, conversations, updated_at)
                    VALUES (%s, %s, %s, %s, %s::jsonb, CURRENT_TIMESTAMP)
                    ON CONFLICT (request_id) DO UPDATE SET
                        rating = EXCLUDED.rating,
                        feedback = EXCLUDED.feedback,
                        conversations = COALESCE(EXCLUDED.conversations, message_ratings.conversations),
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING request_id, rating, feedback, updated_at
                    """,
                    (request_id, session_id, rating, feedback, conversations_json),
                )
                row = cur.fetchone()
                conn.commit()

                logger.info(f"Rating saved: request_id={request_id}, rating={rating}")

                # Quality Answer RAG: 높은 별점 답변 자동 저장
                try:
                    settings_svc = _get_settings_service()
                    if settings_svc.is_quality_answer_rag_enabled():
                        min_rating = settings_svc.get_quality_answer_min_rating()
                        if rating >= min_rating:
                            # 대화 이력에서 질문/답변 추출
                            conversations = None
                            if conversations_json:
                                conversations = json.loads(conversations_json) if isinstance(conversations_json, str) else conversations_json

                            if conversations and len(conversations) > 0:
                                last_conv = conversations[-1]
                                user_question = last_conv.get("userQuestion", "")
                                ai_response = last_conv.get("aiResponse", "")

                                if user_question and ai_response:
                                    qa_svc = _get_qa_service()
                                    # 비동기 함수를 동기 컨텍스트에서 실행
                                    try:
                                        loop = asyncio.get_event_loop()
                                        if loop.is_running():
                                            # 이미 이벤트 루프가 실행 중이면 태스크 생성
                                            asyncio.create_task(
                                                qa_svc.save_quality_answer(
                                                    request_id=request_id,
                                                    user_question=user_question,
                                                    ai_response=ai_response,
                                                    rating=rating,
                                                    session_id=session_id
                                                )
                                            )
                                        else:
                                            loop.run_until_complete(
                                                qa_svc.save_quality_answer(
                                                    request_id=request_id,
                                                    user_question=user_question,
                                                    ai_response=ai_response,
                                                    rating=rating,
                                                    session_id=session_id
                                                )
                                            )
                                        logger.info(f"Quality answer saved for request_id={request_id}, rating={rating}")
                                    except RuntimeError:
                                        # 이벤트 루프 없는 경우 새로 생성
                                        asyncio.run(
                                            qa_svc.save_quality_answer(
                                                request_id=request_id,
                                                user_question=user_question,
                                                ai_response=ai_response,
                                                rating=rating,
                                                session_id=session_id
                                            )
                                        )
                                        logger.info(f"Quality answer saved for request_id={request_id}, rating={rating}")
                except Exception as qa_error:
                    # Quality Answer 저장 실패해도 rating 저장은 성공으로 처리
                    logger.warning(f"Failed to save quality answer (non-blocking): {qa_error}")

                return {
                    "requestId": row[0],
                    "rating": row[1],
                    "feedback": row[2],
                    "savedAt": row[3].isoformat() if row[3] else datetime.now().isoformat(),
                }
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save rating: {e}")
            raise
        finally:
            conn.close()

    def get_ratings_by_session(self, session_id: str) -> list[dict]:
        """세션별 별점 일괄 조회"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT request_id, rating, feedback, created_at
                    FROM message_ratings
                    WHERE session_id = %s
                    ORDER BY created_at ASC
                    """,
                    (session_id,),
                )
                rows = cur.fetchall()
                return [
                    {
                        "requestId": row[0],
                        "rating": row[1],
                        "feedback": row[2],
                        "createdAt": row[3].isoformat() if row[3] else None,
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get ratings by session: {e}")
            raise
        finally:
            conn.close()

    def get_rating(self, request_id: str) -> Optional[dict]:
        """별점 조회"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT request_id, rating, feedback, created_at
                    FROM message_ratings
                    WHERE request_id = %s
                    """,
                    (request_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None

                return {
                    "requestId": row[0],
                    "rating": row[1],
                    "feedback": row[2],
                    "createdAt": row[3].isoformat() if row[3] else None,
                }
        except Exception as e:
            logger.error(f"Failed to get rating: {e}")
            raise
        finally:
            conn.close()


    # === Analytics Methods ===

    def get_summary(self, period: str = "all") -> dict:
        """별점 요약 통계"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                where = self._period_where(period)
                cur.execute(
                    f"""
                    SELECT
                        COUNT(*) AS total_count,
                        COALESCE(AVG(rating), 0) AS average_rating,
                        COUNT(*) FILTER (WHERE feedback IS NOT NULL AND feedback != '') AS with_feedback_count
                    FROM message_ratings
                    {where}
                    """
                )
                row = cur.fetchone()
                total_count = row[0]
                average_rating = round(float(row[1]), 2)
                with_feedback_count = row[2]

                cur.execute(
                    f"""
                    SELECT rating, COUNT(*) AS cnt
                    FROM message_ratings
                    {where}
                    GROUP BY rating
                    ORDER BY rating
                    """
                )
                dist_rows = cur.fetchall()
                distribution = {str(r[0]): r[1] for r in dist_rows}

                return {
                    "totalCount": total_count,
                    "averageRating": average_rating,
                    "distribution": distribution,
                    "withFeedbackCount": with_feedback_count,
                    "period": period,
                }
        except Exception as e:
            logger.error(f"Failed to get summary: {e}")
            raise
        finally:
            conn.close()

    def get_distribution(self, period: str = "30d") -> dict:
        """별점 분포"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                where = self._period_where(period)
                cur.execute(
                    f"""
                    SELECT rating, COUNT(*) AS cnt
                    FROM message_ratings
                    {where}
                    GROUP BY rating
                    ORDER BY rating
                    """
                )
                rows = cur.fetchall()
                total = sum(r[1] for r in rows)
                distribution = [
                    {
                        "rating": r[0],
                        "count": r[1],
                        "percentage": round(r[1] / total * 100, 1) if total > 0 else 0,
                    }
                    for r in rows
                ]
                # fill missing ratings
                existing = {d["rating"] for d in distribution}
                for r in range(1, 6):
                    if r not in existing:
                        distribution.append({"rating": r, "count": 0, "percentage": 0})
                distribution.sort(key=lambda x: x["rating"])

                return {"distribution": distribution, "period": period}
        except Exception as e:
            logger.error(f"Failed to get distribution: {e}")
            raise
        finally:
            conn.close()

    def get_trend(self, period: str = "30d", granularity: str = "day") -> dict:
        """일별 평균 추이"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                where = self._period_where(period)
                trunc = "day" if granularity == "day" else "week"
                cur.execute(
                    f"""
                    SELECT DATE_TRUNC('{trunc}', created_at)::date AS d,
                           ROUND(AVG(rating)::numeric, 2) AS avg_rating,
                           COUNT(*) AS cnt
                    FROM message_ratings
                    {where}
                    GROUP BY d
                    ORDER BY d
                    """
                )
                rows = cur.fetchall()
                trend = [
                    {
                        "date": r[0].isoformat(),
                        "averageRating": float(r[1]),
                        "count": r[2],
                    }
                    for r in rows
                ]
                return {"trend": trend, "period": period}
        except Exception as e:
            logger.error(f"Failed to get trend: {e}")
            raise
        finally:
            conn.close()

    def get_details(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        min_rating: Optional[int] = None,
        max_rating: Optional[int] = None,
        has_feedback: Optional[bool] = None,
    ) -> dict:
        """별점 상세 목록 (페이지네이션)"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                conditions = []
                params: list = []

                if min_rating is not None:
                    conditions.append("mr.rating >= %s")
                    params.append(min_rating)
                if max_rating is not None:
                    conditions.append("mr.rating <= %s")
                    params.append(max_rating)
                if has_feedback is True:
                    conditions.append("mr.feedback IS NOT NULL AND mr.feedback != ''")
                elif has_feedback is False:
                    conditions.append("(mr.feedback IS NULL OR mr.feedback = '')")

                where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

                # count
                cur.execute(
                    f"SELECT COUNT(*) FROM message_ratings mr {where}",
                    params,
                )
                total = cur.fetchone()[0]
                total_pages = max(1, (total + page_size - 1) // page_size)

                # allowed sort columns
                allowed_sort = {"created_at", "rating"}
                col = sort_by if sort_by in allowed_sort else "created_at"
                order = "ASC" if sort_order.upper() == "ASC" else "DESC"

                offset = (page - 1) * page_size
                cur.execute(
                    f"""
                    SELECT mr.request_id, mr.session_id, cs.title,
                        COALESCE(
                            (SELECT cm2.content FROM chat_messages cm2
                             WHERE cm2.session_id = mr.session_id AND cm2.role = 'user'
                               AND cm2.created_at <= COALESCE(cm.created_at, mr.created_at)
                             ORDER BY cm2.created_at DESC LIMIT 1),
                            (mr.conversations -> (jsonb_array_length(mr.conversations) - 1)) ->> 'userQuestion'
                        ) AS user_question,
                        COALESCE(
                            LEFT(cm.content, 200),
                            LEFT((mr.conversations -> (jsonb_array_length(mr.conversations) - 1)) ->> 'aiResponse', 200)
                        ) AS ai_response_summary,
                        mr.rating, mr.feedback, mr.created_at
                    FROM message_ratings mr
                    LEFT JOIN chat_messages cm ON cm.message_id = mr.request_id
                    LEFT JOIN chat_sessions cs ON cs.session_id = mr.session_id
                    {where}
                    ORDER BY mr.{col} {order}
                    LIMIT %s OFFSET %s
                    """,
                    params + [page_size, offset],
                )
                rows = cur.fetchall()
                items = [
                    {
                        "requestId": r[0],
                        "sessionId": r[1],
                        "sessionTitle": r[2],
                        "userQuestion": r[3],
                        "aiResponseSummary": r[4],
                        "rating": r[5],
                        "feedback": r[6],
                        "createdAt": r[7].isoformat() if r[7] else None,
                    }
                    for r in rows
                ]
                return {
                    "items": items,
                    "total": total,
                    "page": page,
                    "pageSize": page_size,
                    "totalPages": total_pages,
                }
        except Exception as e:
            logger.error(f"Failed to get details: {e}")
            raise
        finally:
            conn.close()

    def get_rating_context(self, request_id: str) -> Optional[dict]:
        """평가 컨텍스트 조회 (스냅샷 우선, 없으면 live query fallback)"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # 1) 평가 정보 + 세션 정보 + 스냅샷
                cur.execute(
                    """
                    SELECT mr.request_id, mr.session_id, cs.title,
                           mr.rating, mr.feedback, mr.created_at, mr.conversations
                    FROM message_ratings mr
                    LEFT JOIN chat_sessions cs ON cs.session_id = mr.session_id
                    WHERE mr.request_id = %s
                    """,
                    (request_id,),
                )
                rating_row = cur.fetchone()
                if rating_row is None:
                    return None

                session_id = rating_row[1]
                snapshot = rating_row[6]  # conversations JSONB

                # 2) 스냅샷이 있으면 사용, 없으면 live query fallback
                if snapshot is not None:
                    conversations = snapshot if isinstance(snapshot, list) else json.loads(snapshot)
                else:
                    # live query fallback
                    cur.execute(
                        "SELECT created_at FROM chat_messages WHERE message_id = %s",
                        (request_id,),
                    )
                    msg_row = cur.fetchone()
                    ref_time = msg_row[0] if msg_row else rating_row[5]

                    if session_id and ref_time:
                        conversations = self._live_query_conversations(cur, session_id, ref_time)
                    else:
                        conversations = []

                return {
                    "requestId": rating_row[0],
                    "sessionId": rating_row[1],
                    "sessionTitle": rating_row[2],
                    "rating": rating_row[3],
                    "feedback": rating_row[4],
                    "createdAt": rating_row[5].isoformat() if rating_row[5] else None,
                    "conversations": conversations,
                }
        except Exception as e:
            logger.error(f"Failed to get rating context: {e}")
            raise
        finally:
            conn.close()

    def update_feedback(self, request_id: str, feedback: str) -> Optional[dict]:
        """피드백 수정"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE message_ratings
                    SET feedback = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE request_id = %s
                    RETURNING request_id, rating, feedback, updated_at
                    """,
                    (feedback, request_id),
                )
                row = cur.fetchone()
                conn.commit()
                if row is None:
                    return None
                return {
                    "requestId": row[0],
                    "rating": row[1],
                    "feedback": row[2],
                    "savedAt": row[3].isoformat() if row[3] else None,
                }
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update feedback: {e}")
            raise
        finally:
            conn.close()

    @staticmethod
    def _period_where(period: str) -> str:
        """기간 필터 WHERE 절 생성"""
        if period == "today":
            return "WHERE created_at >= CURRENT_DATE"
        elif period == "7d":
            return "WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'"
        elif period == "30d":
            return "WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'"
        return ""  # 'all'


# Singleton instance
_rating_service: Optional[RatingService] = None


def get_rating_service() -> RatingService:
    """RatingService 싱글톤 반환"""
    global _rating_service
    if _rating_service is None:
        _rating_service = RatingService()
    return _rating_service
