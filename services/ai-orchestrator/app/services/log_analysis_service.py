"""
LogAnalysisService - 외부 서버 로그 분석 서비스
"""

import re
import os
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from app.models.log_settings import (
    LogPath, MaskingPattern, LogEntry, LogAnalysisResult, LogAnalysisSettings
)
from app.services.settings_service import get_settings_service

logger = logging.getLogger(__name__)


class LogAnalysisService:
    """로그 파일 분석 서비스"""

    # 표준 로그 패턴 (timestamp + level + message)
    STANDARD_LOG_PATTERN = r'^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s*\[?(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL)\]?\s*(.+)$'

    # 기본 마스킹 패턴
    DEFAULT_MASKING_PATTERNS = [
        {"name": "API Key", "regex": r"(api[_-]?key)[=:]\s*['\"]?[\w-]+['\"]?", "replacement": r"\1=***"},
        {"name": "Password", "regex": r"(password|pwd)[=:]\s*['\"]?[^\s'\",}]+['\"]?", "replacement": r"\1=***"},
        {"name": "Email", "regex": r"[\w.-]+@[\w.-]+\.\w+", "replacement": "***@***.***"},
        {"name": "Phone", "regex": r"\d{2,3}-\d{3,4}-\d{4}", "replacement": "***-****-****"},
    ]

    # 허용된 로그 디렉토리 (Path Traversal 방지)
    # 환경 변수로 설정 가능: LOG_ALLOWED_DIRS=/var/log,/home/user/logs
    DEFAULT_LOG_DIRS = ["/logs", "/var/log", "/app/logs"]
    _env_log_dirs = os.getenv("LOG_ALLOWED_DIRS", "")
    ALLOWED_LOG_DIRS = [d.strip() for d in _env_log_dirs.split(",") if d.strip()] if _env_log_dirs else DEFAULT_LOG_DIRS

    def __init__(self):
        self.settings_service = get_settings_service()

    def _get_settings(self) -> LogAnalysisSettings:
        """로그 분석 설정 조회"""
        setting = self.settings_service.get_setting("log_analysis")
        if setting is None:
            return LogAnalysisSettings()
        return LogAnalysisSettings(**setting.get("value", {}))

    def _validate_path(self, path: str) -> bool:
        """경로 유효성 검증 (Path Traversal 방지)"""
        # .. 포함 여부 확인
        if ".." in path:
            logger.warning(f"Path traversal attempt detected: {path}")
            return False

        # 허용된 디렉토리 확인
        normalized = os.path.normpath(path)
        for allowed_dir in self.ALLOWED_LOG_DIRS:
            if normalized.startswith(allowed_dir):
                return True

        logger.warning(f"Path not in allowed directories: {path}")
        return False

    def _read_log_file(self, path: str, max_lines: int = 500) -> List[str]:
        """로그 파일 읽기 (최근 N줄)"""
        if not self._validate_path(path):
            raise ValueError(f"Invalid log path: {path}")

        if not os.path.exists(path):
            raise FileNotFoundError(f"Log file not found: {path}")

        # 파일 크기 체크 (100MB 제한)
        file_size = os.path.getsize(path)
        if file_size > 100 * 1024 * 1024:
            logger.warning(f"Large log file: {path} ({file_size} bytes)")

        lines = []
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            # 마지막 N줄 읽기 (효율적인 방법)
            all_lines = f.readlines()
            lines = all_lines[-max_lines:] if len(all_lines) > max_lines else all_lines

        return [line.rstrip('\n') for line in lines]

    def _parse_log_line(self, line: str) -> LogEntry:
        """로그 라인 파싱"""
        match = re.match(self.STANDARD_LOG_PATTERN, line, re.IGNORECASE)

        if match:
            timestamp_str, level, message = match.groups()
            try:
                # ISO 형식 파싱 시도
                timestamp = datetime.fromisoformat(timestamp_str.replace(' ', 'T'))
            except ValueError:
                timestamp = None

            return LogEntry(
                timestamp=timestamp,
                level=level.upper(),
                message=message,
                raw=line
            )

        # 파싱 실패 시 원본 그대로 반환
        return LogEntry(message=line, raw=line)

    def _mask_sensitive_data(self, entries: List[LogEntry], patterns: List[MaskingPattern]) -> List[LogEntry]:
        """민감정보 마스킹"""
        masked_entries = []

        # 패턴이 없으면 기본 패턴 사용
        if not patterns:
            patterns = [MaskingPattern(**p) for p in self.DEFAULT_MASKING_PATTERNS]

        for entry in entries:
            masked_message = entry.message
            masked_raw = entry.raw

            for pattern in patterns:
                try:
                    regex = re.compile(pattern.regex, re.IGNORECASE)
                    masked_message = regex.sub(pattern.replacement, masked_message)
                    masked_raw = regex.sub(pattern.replacement, masked_raw)
                except re.error as e:
                    logger.warning(f"Invalid masking pattern {pattern.name}: {e}")

            masked_entries.append(LogEntry(
                timestamp=entry.timestamp,
                level=entry.level,
                message=masked_message,
                raw=masked_raw
            ))

        return masked_entries

    async def _generate_analysis_summary(
        self,
        entries: List[LogEntry],
        user_question: str
    ) -> str:
        """LLM을 통한 로그 분석 요약 생성"""
        from langchain_openai import ChatOpenAI
        from langchain_anthropic import ChatAnthropic

        # 에러/경고 로그 추출
        error_entries = [e for e in entries if e.level in ("ERROR", "CRITICAL")]
        warn_entries = [e for e in entries if e.level in ("WARN", "WARNING")]

        # 최근 로그 샘플 (최대 50줄)
        sample_logs = "\n".join([e.raw for e in entries[-50:]])

        # LLM 설정
        llm_provider = os.getenv("LLM_PROVIDER", "openai")
        if llm_provider == "anthropic":
            llm = ChatAnthropic(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
                temperature=0
            )
        else:
            llm = ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0
            )

        prompt = f"""당신은 서버 로그 분석 전문가입니다. 아래 로그를 분석하고 사용자 질문에 답변하세요.

## 로그 통계
- 전체 로그 수: {len(entries)}건
- 에러 로그: {len(error_entries)}건
- 경고 로그: {len(warn_entries)}건

## 에러 로그 (최근 10건)
{chr(10).join([e.raw for e in error_entries[-10:]])}

## 최근 로그 샘플
{sample_logs}

## 사용자 질문
{user_question}

## 응답 형식
1. 간단한 요약 (2-3문장)
2. 발견된 주요 이슈 (있다면)
3. 권장 조치 사항 (있다면)

마크다운 형식으로 작성하세요.
"""

        response = await llm.ainvoke(prompt)
        return response.content.strip()

    async def analyze(
        self,
        log_path_id: Optional[str] = None,
        time_range_minutes: int = 60,
        max_lines: int = 500,
        level_filter: Optional[List[str]] = None,
        user_question: Optional[str] = None
    ) -> LogAnalysisResult:
        """
        로그 분석 수행

        Args:
            log_path_id: 로그 경로 ID (없으면 첫 번째 활성 경로 사용)
            time_range_minutes: 분석할 시간 범위 (분)
            max_lines: 최대 읽기 줄 수
            level_filter: 필터링할 로그 레벨 목록
            user_question: 사용자 질문 (LLM 분석용)

        Returns:
            LogAnalysisResult
        """
        settings = self._get_settings()

        if not settings.enabled:
            return LogAnalysisResult(
                entries=[],
                summary="로그 분석 기능이 비활성화되어 있습니다. 설정에서 활성화해주세요."
            )

        # 로그 경로 결정
        log_path: Optional[LogPath] = None
        if log_path_id:
            log_path = next((p for p in settings.paths if p.id == log_path_id and p.enabled), None)
        else:
            log_path = next((p for p in settings.paths if p.enabled), None)

        if not log_path:
            return LogAnalysisResult(
                entries=[],
                summary="활성화된 로그 경로가 없습니다. 설정에서 로그 경로를 추가해주세요."
            )

        try:
            # 로그 파일 읽기
            lines = self._read_log_file(log_path.path, max_lines)

            # 파싱
            entries = [self._parse_log_line(line) for line in lines]

            # 시간 범위 필터링
            cutoff_time = datetime.now() - timedelta(minutes=time_range_minutes)
            entries = [
                e for e in entries
                if e.timestamp is None or e.timestamp >= cutoff_time
            ]

            # 레벨 필터링
            if level_filter:
                level_filter_upper = [l.upper() for l in level_filter]
                entries = [e for e in entries if e.level in level_filter_upper or e.level is None]

            # 마스킹 적용
            if settings.masking.enabled:
                entries = self._mask_sensitive_data(entries, settings.masking.patterns)

            # 통계 계산
            error_count = sum(1 for e in entries if e.level in ("ERROR", "CRITICAL"))
            warn_count = sum(1 for e in entries if e.level in ("WARN", "WARNING"))

            # LLM 분석 요약 (질문이 있는 경우)
            summary = None
            if user_question and entries:
                summary = await self._generate_analysis_summary(entries, user_question)

            return LogAnalysisResult(
                entries=entries,
                summary=summary,
                error_count=error_count,
                warn_count=warn_count,
                time_range=f"최근 {time_range_minutes}분"
            )

        except FileNotFoundError as e:
            logger.error(f"Log file not found: {e}")
            return LogAnalysisResult(
                entries=[],
                summary=f"로그 파일을 찾을 수 없습니다: {log_path.path}"
            )
        except Exception as e:
            logger.error(f"Log analysis error: {e}", exc_info=True)
            return LogAnalysisResult(
                entries=[],
                summary=f"로그 분석 중 오류가 발생했습니다: {str(e)}"
            )


# 싱글톤 인스턴스
_log_analysis_service: Optional[LogAnalysisService] = None


def get_log_analysis_service() -> LogAnalysisService:
    """LogAnalysisService 싱글톤 반환"""
    global _log_analysis_service
    if _log_analysis_service is None:
        _log_analysis_service = LogAnalysisService()
    return _log_analysis_service
