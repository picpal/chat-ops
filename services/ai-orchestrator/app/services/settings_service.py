"""
Settings 서비스 - 애플리케이션 설정 관리
"""

import json
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

import psycopg

logger = logging.getLogger(__name__)


class SettingsService:
    """애플리케이션 설정 관리 서비스"""

    # Quality Answer RAG 설정 키
    QUALITY_ANSWER_RAG_KEY = "quality_answer_rag"

    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://chatops_user:chatops_pass@localhost:5432/chatops"
        )

    def _get_connection(self):
        """PostgreSQL 연결 생성"""
        return psycopg.connect(self.database_url)

    def get_setting(self, key: str) -> Optional[Dict[str, Any]]:
        """
        설정 조회

        Args:
            key: 설정 키

        Returns:
            설정 정보 또는 None
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT key, value, description, updated_at
                    FROM settings
                    WHERE key = %s
                    """,
                    (key,)
                )
                row = cur.fetchone()
                if row is None:
                    return None

                return {
                    "key": row[0],
                    "value": row[1] if isinstance(row[1], dict) else json.loads(row[1]),
                    "description": row[2],
                    "updatedAt": row[3].isoformat() if row[3] else None
                }
        except Exception as e:
            logger.error(f"Failed to get setting {key}: {e}")
            raise
        finally:
            conn.close()

    def update_setting(
        self,
        key: str,
        value: Dict[str, Any],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        설정 업데이트 (upsert)

        Args:
            key: 설정 키
            value: 설정 값 (기존 값과 병합)
            description: 설정 설명 (옵션)

        Returns:
            업데이트된 설정 정보
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # 기존 값 조회
                cur.execute(
                    "SELECT value FROM settings WHERE key = %s",
                    (key,)
                )
                row = cur.fetchone()

                if row:
                    # 기존 값과 병합
                    existing_value = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                    merged_value = {**existing_value, **value}

                    # 업데이트
                    if description:
                        cur.execute(
                            """
                            UPDATE settings
                            SET value = %s::jsonb, description = %s, updated_at = CURRENT_TIMESTAMP
                            WHERE key = %s
                            RETURNING key, value, description, updated_at
                            """,
                            (json.dumps(merged_value), description, key)
                        )
                    else:
                        cur.execute(
                            """
                            UPDATE settings
                            SET value = %s::jsonb, updated_at = CURRENT_TIMESTAMP
                            WHERE key = %s
                            RETURNING key, value, description, updated_at
                            """,
                            (json.dumps(merged_value), key)
                        )
                else:
                    # 신규 삽입
                    cur.execute(
                        """
                        INSERT INTO settings (key, value, description)
                        VALUES (%s, %s::jsonb, %s)
                        RETURNING key, value, description, updated_at
                        """,
                        (key, json.dumps(value), description)
                    )

                row = cur.fetchone()
                conn.commit()

                logger.info(f"Setting updated: key={key}")
                return {
                    "key": row[0],
                    "value": row[1] if isinstance(row[1], dict) else json.loads(row[1]),
                    "description": row[2],
                    "updatedAt": row[3].isoformat() if row[3] else None
                }
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update setting {key}: {e}")
            raise
        finally:
            conn.close()

    def is_quality_answer_rag_enabled(self) -> bool:
        """
        Quality Answer RAG 기능 활성화 여부 확인

        Returns:
            활성화 여부 (기본값: True)
        """
        try:
            setting = self.get_setting(self.QUALITY_ANSWER_RAG_KEY)
            if setting is None:
                return True  # 기본값: 활성화

            return setting.get("value", {}).get("enabled", True)
        except Exception as e:
            logger.warning(f"Failed to check quality_answer_rag status, defaulting to True: {e}")
            return True

    def get_quality_answer_min_rating(self) -> int:
        """
        Quality Answer RAG 최소 별점 기준 조회

        Returns:
            최소 별점 (기본값: 4)
        """
        try:
            setting = self.get_setting(self.QUALITY_ANSWER_RAG_KEY)
            if setting is None:
                return 4  # 기본값

            return setting.get("value", {}).get("minRating", 4)
        except Exception as e:
            logger.warning(f"Failed to get minRating, defaulting to 4: {e}")
            return 4

    def get_quality_answer_rag_status(self, stored_count: int = 0) -> Dict[str, Any]:
        """
        Quality Answer RAG 상태 조회

        Args:
            stored_count: 저장된 고품질 답변 수

        Returns:
            상태 정보
        """
        setting = self.get_setting(self.QUALITY_ANSWER_RAG_KEY)

        if setting is None:
            return {
                "enabled": True,
                "minRating": 4,
                "storedCount": stored_count,
                "lastUpdated": None
            }

        value = setting.get("value", {})
        return {
            "enabled": value.get("enabled", True),
            "minRating": value.get("minRating", 4),
            "storedCount": stored_count,
            "lastUpdated": setting.get("updatedAt")
        }


# 싱글톤 인스턴스
_settings_service: Optional[SettingsService] = None


def get_settings_service() -> SettingsService:
    """SettingsService 싱글톤 반환"""
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service
