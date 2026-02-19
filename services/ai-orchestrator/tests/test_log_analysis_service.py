"""
LogAnalysisService 단위 테스트
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import os
import tempfile

from app.services.log_analysis_service import LogAnalysisService, get_log_analysis_service
from app.models.log_settings import (
    LogPath, MaskingPattern, MaskingConfig, LogEntry,
    LogAnalysisResult, LogAnalysisSettings, LogAnalysisDefaults
)


class TestLogAnalysisServiceParseLogLine:
    """_parse_log_line 테스트"""

    @pytest.fixture
    def service(self):
        """DB 연결 없이 서비스 인스턴스 생성"""
        with patch("app.services.log_analysis_service.get_settings_service"):
            return LogAnalysisService()

    def test_parse_log_line_info_level(self, service):
        """INFO 레벨 로그 라인 파싱"""
        line = "2026-02-18T10:00:00.000 [INFO] Application started"
        entry = service._parse_log_line(line)

        assert entry.level == "INFO"
        assert "Application started" in entry.message
        assert entry.raw == line

    def test_parse_log_line_error_level(self, service):
        """ERROR 레벨 로그 라인 파싱"""
        line = "2026-02-18T10:01:00.000 [ERROR] Connection failed: timeout"
        entry = service._parse_log_line(line)

        assert entry.level == "ERROR"
        assert "Connection failed" in entry.message
        assert entry.raw == line

    def test_parse_log_line_warn_level(self, service):
        """WARN 레벨 로그 라인 파싱"""
        line = "2026-02-18T10:02:00.000 [WARN] Memory usage high: 85%"
        entry = service._parse_log_line(line)

        assert entry.level == "WARN"
        assert "Memory usage high" in entry.message

    def test_parse_log_line_debug_level(self, service):
        """DEBUG 레벨 로그 라인 파싱"""
        line = "2026-02-18T10:03:00.000 [DEBUG] Processing request"
        entry = service._parse_log_line(line)

        assert entry.level == "DEBUG"
        assert "Processing request" in entry.message

    def test_parse_log_line_critical_level(self, service):
        """CRITICAL 레벨 로그 라인 파싱"""
        line = "2026-02-18T10:04:00.000 [CRITICAL] System failure"
        entry = service._parse_log_line(line)

        assert entry.level == "CRITICAL"
        assert "System failure" in entry.message

    def test_parse_log_line_invalid_format(self, service):
        """비정상적인 로그 라인 파싱 - level은 None"""
        line = "Invalid log line without timestamp"
        entry = service._parse_log_line(line)

        assert entry.level is None
        assert entry.message == line
        assert entry.raw == line

    def test_parse_log_line_timestamp_parsed(self, service):
        """타임스탬프 파싱 확인"""
        line = "2026-02-18T10:00:00 [INFO] Test message"
        entry = service._parse_log_line(line)

        assert entry.timestamp is not None
        assert entry.timestamp.year == 2026
        assert entry.timestamp.month == 2
        assert entry.timestamp.day == 18

    def test_parse_log_line_space_separated_timestamp(self, service):
        """공백으로 구분된 타임스탬프 파싱"""
        line = "2026-02-18 10:00:00 [INFO] Test message"
        entry = service._parse_log_line(line)

        assert entry.level == "INFO"
        assert entry.timestamp is not None

    def test_parse_log_line_case_insensitive(self, service):
        """대소문자 무관 레벨 파싱"""
        line = "2026-02-18T10:00:00 [error] lowercase error"
        entry = service._parse_log_line(line)

        assert entry.level == "ERROR"


class TestLogAnalysisServiceValidatePath:
    """_validate_path 테스트"""

    @pytest.fixture
    def service(self):
        with patch("app.services.log_analysis_service.get_settings_service"):
            return LogAnalysisService()

    def test_validate_path_traversal_double_dot_blocked(self, service):
        """Path Traversal 공격 차단 - '..' 포함"""
        assert service._validate_path("/logs/../etc/passwd") is False

    def test_validate_path_traversal_multiple_dots_blocked(self, service):
        """Path Traversal 공격 차단 - 다중 '..'"""
        assert service._validate_path("/logs/../../root") is False

    def test_validate_path_logs_directory_allowed(self, service):
        """허용된 /logs 디렉토리"""
        assert service._validate_path("/logs/app.log") is True

    def test_validate_path_var_log_allowed(self, service):
        """허용된 /var/log 디렉토리"""
        assert service._validate_path("/var/log/app.log") is True

    def test_validate_path_app_logs_allowed(self, service):
        """허용된 /app/logs 디렉토리"""
        assert service._validate_path("/app/logs/test.log") is True

    def test_validate_path_etc_not_allowed(self, service):
        """/etc 디렉토리 차단"""
        assert service._validate_path("/etc/passwd") is False

    def test_validate_path_home_not_allowed(self, service):
        """/home 디렉토리 차단"""
        assert service._validate_path("/home/user/file.log") is False

    def test_validate_path_root_not_allowed(self, service):
        """/root 디렉토리 차단"""
        assert service._validate_path("/root/secret.log") is False

    def test_validate_path_nested_allowed_dir(self, service):
        """허용된 디렉토리의 하위 경로"""
        assert service._validate_path("/logs/2026/02/app.log") is True

    def test_validate_path_var_log_nested(self, service):
        """/var/log 하위 중첩 경로"""
        assert service._validate_path("/var/log/nginx/access.log") is True


class TestLogAnalysisServiceMaskSensitiveData:
    """_mask_sensitive_data 테스트"""

    @pytest.fixture
    def service(self):
        with patch("app.services.log_analysis_service.get_settings_service"):
            return LogAnalysisService()

    def test_mask_api_key(self, service):
        """API 키 마스킹"""
        entries = [
            LogEntry(
                message="api_key=sk-12345abc request processed",
                raw="2026-02-18 [INFO] api_key=sk-12345abc request processed"
            )
        ]
        patterns = [
            MaskingPattern(
                name="API Key",
                regex=r"(api[_-]?key)[=:]\s*['\"]?[\w-]+['\"]?",
                replacement=r"\1=***"
            )
        ]

        masked = service._mask_sensitive_data(entries, patterns)

        assert "sk-12345abc" not in masked[0].message
        assert "api_key=***" in masked[0].message

    def test_mask_password(self, service):
        """비밀번호 마스킹"""
        entries = [
            LogEntry(
                message="password=secret123 login attempt",
                raw="password=secret123 login attempt"
            )
        ]
        patterns = [
            MaskingPattern(
                name="Password",
                regex=r"(password|pwd)[=:]\s*['\"]?[^\s'\",}]+['\"]?",
                replacement=r"\1=***"
            )
        ]

        masked = service._mask_sensitive_data(entries, patterns)

        assert "secret123" not in masked[0].message
        assert "password=***" in masked[0].message

    def test_mask_email_default_patterns(self, service):
        """이메일 마스킹 - 기본 패턴 사용"""
        entries = [
            LogEntry(
                message="User email: user@example.com logged in",
                raw="User email: user@example.com logged in"
            )
        ]

        # 빈 패턴 전달 시 기본 패턴 사용
        masked = service._mask_sensitive_data(entries, [])

        assert "user@example.com" not in masked[0].message

    def test_mask_phone_default_patterns(self, service):
        """전화번호 마스킹 - 기본 패턴 사용"""
        entries = [
            LogEntry(
                message="Phone: 010-1234-5678 customer contact",
                raw="Phone: 010-1234-5678 customer contact"
            )
        ]

        masked = service._mask_sensitive_data(entries, [])

        assert "010-1234-5678" not in masked[0].message
        assert "***-****-****" in masked[0].message

    def test_mask_multiple_patterns(self, service):
        """여러 패턴 동시 마스킹"""
        entries = [
            LogEntry(
                message="api_key=sk-12345 password=secret123",
                raw="2026-02-18 [INFO] api_key=sk-12345 password=secret123"
            )
        ]
        patterns = [
            MaskingPattern(
                name="API Key",
                regex=r"(api[_-]?key)[=:]\s*['\"]?[\w-]+['\"]?",
                replacement=r"\1=***"
            ),
            MaskingPattern(
                name="Password",
                regex=r"(password|pwd)[=:]\s*['\"]?[^\s'\",}]+['\"]?",
                replacement=r"\1=***"
            ),
        ]

        masked = service._mask_sensitive_data(entries, patterns)

        assert "sk-12345" not in masked[0].message
        assert "secret123" not in masked[0].message
        assert "***" in masked[0].message

    def test_mask_invalid_regex_handled_gracefully(self, service):
        """잘못된 정규식 패턴 - 예외 없이 처리"""
        entries = [
            LogEntry(
                message="test message",
                raw="test message"
            )
        ]
        patterns = [
            MaskingPattern(
                name="Invalid",
                regex=r"[invalid regex(",  # 잘못된 regex
                replacement=r"***"
            )
        ]

        # 예외 발생 없이 처리되어야 함
        masked = service._mask_sensitive_data(entries, patterns)

        assert len(masked) == 1
        assert masked[0].message == "test message"

    def test_mask_preserves_timestamp_and_level(self, service):
        """마스킹 후 timestamp와 level 보존"""
        now = datetime(2026, 2, 18, 10, 0, 0)
        entries = [
            LogEntry(
                timestamp=now,
                level="ERROR",
                message="error with password=secret",
                raw="2026-02-18 [ERROR] error with password=secret"
            )
        ]

        masked = service._mask_sensitive_data(entries, [])

        assert masked[0].timestamp == now
        assert masked[0].level == "ERROR"

    def test_mask_empty_entries(self, service):
        """빈 엔트리 목록"""
        masked = service._mask_sensitive_data([], [])

        assert masked == []


class TestLogAnalysisServiceReadLogFile:
    """_read_log_file 테스트"""

    @pytest.fixture
    def service(self):
        with patch("app.services.log_analysis_service.get_settings_service"):
            svc = LogAnalysisService()
            # 테스트 목적으로 /tmp 허용 추가
            svc.ALLOWED_LOG_DIRS = ["/tmp", "/logs", "/var/log", "/app/logs"]
            return svc

    @pytest.fixture
    def sample_log_lines(self):
        return [
            "2026-02-18T10:00:00.000 [INFO] Application started",
            "2026-02-18T10:01:00.000 [ERROR] Connection failed: timeout",
            "2026-02-18T10:02:00.000 [WARN] Memory usage high: 85%",
            "2026-02-18T10:03:00.000 [DEBUG] Processing request",
            "Invalid log line without timestamp",
        ]

    @pytest.fixture
    def temp_log_file(self, sample_log_lines):
        """임시 로그 파일 생성"""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.log',
            delete=False,
            dir='/tmp'
        ) as f:
            f.write("\n".join(sample_log_lines))
            temp_path = f.name

        yield temp_path

        os.unlink(temp_path)

    def test_read_log_file_all_lines(self, service, temp_log_file, sample_log_lines):
        """파일 전체 읽기"""
        lines = service._read_log_file(temp_log_file, max_lines=1000)

        assert len(lines) == len(sample_log_lines)

    def test_read_log_file_max_lines_limit(self, service, temp_log_file, sample_log_lines):
        """최대 줄 수 제한"""
        lines = service._read_log_file(temp_log_file, max_lines=3)

        assert len(lines) == 3
        # 마지막 3줄이 반환되어야 함
        assert lines[-1] == sample_log_lines[-1]

    def test_read_log_file_invalid_path_raises(self, service):
        """허용되지 않은 경로 접근 시 예외"""
        with pytest.raises(ValueError, match="Invalid log path"):
            service._read_log_file("/etc/passwd")

    def test_read_log_file_not_found_raises(self, service):
        """존재하지 않는 파일 접근 시 예외"""
        with pytest.raises(FileNotFoundError):
            service._read_log_file("/tmp/nonexistent_file_99999.log")

    def test_read_log_file_strips_newlines(self, service, temp_log_file, sample_log_lines):
        """줄바꿈 문자 제거 확인"""
        lines = service._read_log_file(temp_log_file)

        for line in lines:
            assert not line.endswith('\n')


class TestLogAnalysisServiceAnalyze:
    """analyze 메서드 테스트"""

    @pytest.fixture
    def service(self):
        with patch("app.services.log_analysis_service.get_settings_service"):
            return LogAnalysisService()

    @pytest.mark.asyncio
    async def test_analyze_disabled_returns_disabled_message(self, service):
        """비활성화 상태에서 분석 시도 - 비활성화 메시지 반환"""
        with patch.object(service, '_get_settings') as mock_settings:
            mock_settings.return_value = LogAnalysisSettings(enabled=False)

            result = await service.analyze(user_question="에러 로그 확인")

            assert "비활성화" in result.summary
            assert len(result.entries) == 0

    @pytest.mark.asyncio
    async def test_analyze_no_active_paths(self, service):
        """활성화된 로그 경로가 없는 경우"""
        with patch.object(service, '_get_settings') as mock_settings:
            mock_settings.return_value = LogAnalysisSettings(
                enabled=True,
                paths=[],
                masking=MaskingConfig(enabled=True, patterns=[]),
                defaults=LogAnalysisDefaults()
            )

            result = await service.analyze(user_question="에러 로그 확인")

            assert "경로가 없습니다" in result.summary
            assert len(result.entries) == 0

    @pytest.mark.asyncio
    async def test_analyze_all_paths_disabled(self, service):
        """모든 경로가 비활성화된 경우"""
        with patch.object(service, '_get_settings') as mock_settings:
            mock_settings.return_value = LogAnalysisSettings(
                enabled=True,
                paths=[
                    LogPath(id="p1", name="App Log", path="/logs/app.log", enabled=False)
                ],
                masking=MaskingConfig(enabled=False),
                defaults=LogAnalysisDefaults()
            )

            result = await service.analyze()

            assert "경로가 없습니다" in result.summary

    @pytest.mark.asyncio
    async def test_analyze_file_not_found(self, service):
        """로그 파일이 존재하지 않는 경우"""
        with patch.object(service, '_get_settings') as mock_settings:
            mock_settings.return_value = LogAnalysisSettings(
                enabled=True,
                paths=[
                    LogPath(id="p1", name="App Log", path="/logs/nonexistent.log", enabled=True)
                ],
                masking=MaskingConfig(enabled=False),
                defaults=LogAnalysisDefaults()
            )

            result = await service.analyze()

            assert "찾을 수 없습니다" in result.summary
            assert len(result.entries) == 0

    @pytest.mark.asyncio
    async def test_analyze_path_selection_by_id(self, service):
        """특정 경로 ID로 분석"""
        with patch.object(service, '_get_settings') as mock_settings:
            mock_settings.return_value = LogAnalysisSettings(
                enabled=True,
                paths=[
                    LogPath(id="p1", name="App Log", path="/logs/app.log", enabled=True),
                    LogPath(id="p2", name="Error Log", path="/logs/error.log", enabled=True),
                ],
                masking=MaskingConfig(enabled=False),
                defaults=LogAnalysisDefaults()
            )

            with patch.object(service, '_read_log_file') as mock_read:
                mock_read.return_value = ["2026-02-18T10:00:00 [INFO] Test"]

                result = await service.analyze(log_path_id="p2")

                # p2의 경로가 사용되었는지 확인
                mock_read.assert_called_once_with("/logs/error.log", 500)

    @pytest.mark.asyncio
    async def test_analyze_error_count_calculation(self, service):
        """에러/경고 카운트 계산 - 999999분 time_range로 오래된 타임스탬프도 포함"""
        with patch.object(service, '_get_settings') as mock_settings:
            mock_settings.return_value = LogAnalysisSettings(
                enabled=True,
                paths=[
                    LogPath(id="p1", name="App Log", path="/logs/app.log", enabled=True)
                ],
                masking=MaskingConfig(enabled=False),
                defaults=LogAnalysisDefaults()
            )

            with patch.object(service, '_read_log_file') as mock_read:
                # 표준 로그 형식으로 작성, time_range_minutes=999999로 시간 필터 우회
                mock_read.return_value = [
                    "2026-02-18T10:00:00 [INFO] ok",
                    "2026-02-18T10:01:00 [ERROR] error1",
                    "2026-02-18T10:02:00 [ERROR] error2",
                    "2026-02-18T10:03:00 [WARN] warning1",
                    "2026-02-18T10:04:00 [CRITICAL] critical1",
                ]

                result = await service.analyze(time_range_minutes=999999)

                # ERROR + CRITICAL = 3
                assert result.error_count == 3
                # WARN = 1
                assert result.warn_count == 1

    @pytest.mark.asyncio
    async def test_analyze_level_filter(self, service):
        """로그 레벨 필터링 - 타임스탬프 없는 로그 사용"""
        with patch.object(service, '_get_settings') as mock_settings:
            mock_settings.return_value = LogAnalysisSettings(
                enabled=True,
                paths=[
                    LogPath(id="p1", name="App Log", path="/logs/app.log", enabled=True)
                ],
                masking=MaskingConfig(enabled=False),
                defaults=LogAnalysisDefaults()
            )

            with patch.object(service, '_read_log_file') as mock_read:
                # 타임스탬프 없는 로그 - 시간 필터 통과, level 파싱도 안됨
                # 레벨 필터링 테스트를 위해 level이 None인 항목이 포함되는지 확인
                mock_read.return_value = [
                    "INFO: info message without standard format",
                    "ERROR: error message without standard format",
                    "WARN: warn message without standard format",
                ]

                # level_filter=["ERROR"] - None 레벨도 통과
                result = await service.analyze(level_filter=["ERROR"])

                # timestamp None인 항목은 필터 통과, level None도 필터 통과
                # 총 3개 항목 모두 level=None이므로 level_filter 통과
                assert len(result.entries) == 3

    @pytest.mark.asyncio
    async def test_analyze_level_filter_with_parsed_levels(self, service):
        """로그 레벨 필터링 - 표준 형식 로그에서 레벨 필터링"""
        from datetime import datetime, timedelta

        with patch.object(service, '_get_settings') as mock_settings:
            mock_settings.return_value = LogAnalysisSettings(
                enabled=True,
                paths=[
                    LogPath(id="p1", name="App Log", path="/logs/app.log", enabled=True)
                ],
                masking=MaskingConfig(enabled=False),
                defaults=LogAnalysisDefaults()
            )

            # 매우 큰 time_range_minutes를 사용하여 오래된 타임스탬프도 통과
            with patch.object(service, '_read_log_file') as mock_read:
                mock_read.return_value = [
                    "2026-02-18T10:00:00 [INFO] info msg",
                    "2026-02-18T10:01:00 [ERROR] error msg",
                    "2026-02-18T10:02:00 [WARN] warn msg",
                ]

                # time_range_minutes를 아주 크게 설정하여 과거 로그도 포함
                result = await service.analyze(
                    level_filter=["ERROR"],
                    time_range_minutes=999999
                )

                error_entries = [e for e in result.entries if e.level == "ERROR"]
                info_entries = [e for e in result.entries if e.level == "INFO"]

                assert len(error_entries) == 1
                assert len(info_entries) == 0

    @pytest.mark.asyncio
    async def test_analyze_masking_applied(self, service):
        """마스킹 적용 확인 - 타임스탬프 없는 로그 사용"""
        with patch.object(service, '_get_settings') as mock_settings:
            mock_settings.return_value = LogAnalysisSettings(
                enabled=True,
                paths=[
                    LogPath(id="p1", name="App Log", path="/logs/app.log", enabled=True)
                ],
                masking=MaskingConfig(
                    enabled=True,
                    patterns=[
                        MaskingPattern(
                            name="Email",
                            regex=r"[\w.-]+@[\w.-]+\.\w+",
                            replacement="***@***.***"
                        )
                    ]
                ),
                defaults=LogAnalysisDefaults()
            )

            with patch.object(service, '_read_log_file') as mock_read:
                # 타임스탬프 없는 로그 - 시간 필터 통과
                mock_read.return_value = [
                    "user@example.com logged in",
                ]

                result = await service.analyze()

                assert len(result.entries) == 1
                assert "user@example.com" not in result.entries[0].message

    @pytest.mark.asyncio
    async def test_analyze_time_range_included(self, service):
        """시간 범위 정보 포함 확인"""
        with patch.object(service, '_get_settings') as mock_settings:
            mock_settings.return_value = LogAnalysisSettings(
                enabled=True,
                paths=[
                    LogPath(id="p1", name="App Log", path="/logs/app.log", enabled=True)
                ],
                masking=MaskingConfig(enabled=False),
                defaults=LogAnalysisDefaults()
            )

            with patch.object(service, '_read_log_file') as mock_read:
                mock_read.return_value = [
                    "2026-02-18T10:00:00 [INFO] test",
                ]

                result = await service.analyze(time_range_minutes=30)

                assert result.time_range == "최근 30분"


class TestLogAnalysisServiceSingleton:
    """싱글톤 패턴 테스트"""

    def test_singleton_returns_same_instance(self):
        """싱글톤 인스턴스가 동일한지 확인"""
        with patch("app.services.log_analysis_service.get_settings_service"):
            import app.services.log_analysis_service as svc_module
            # 싱글톤 리셋
            svc_module._log_analysis_service = None

            service1 = get_log_analysis_service()
            service2 = get_log_analysis_service()

            assert service1 is service2

    def test_singleton_is_log_analysis_service(self):
        """싱글톤이 LogAnalysisService 인스턴스인지 확인"""
        with patch("app.services.log_analysis_service.get_settings_service"):
            import app.services.log_analysis_service as svc_module
            svc_module._log_analysis_service = None

            service = get_log_analysis_service()

            assert isinstance(service, LogAnalysisService)


class TestLogAnalysisIntentType:
    """IntentType.LOG_ANALYSIS 테스트"""

    def test_log_analysis_intent_exists(self):
        """IntentType enum에 LOG_ANALYSIS가 존재하는지 확인"""
        from app.services.query_planner import IntentType

        assert hasattr(IntentType, 'LOG_ANALYSIS')

    def test_log_analysis_intent_value(self):
        """IntentType.LOG_ANALYSIS 값 확인"""
        from app.services.query_planner import IntentType

        assert IntentType.LOG_ANALYSIS.value == "log_analysis"

    def test_log_analysis_intent_in_enum_values(self):
        """log_analysis 값이 IntentType에 포함되어 있는지 확인"""
        from app.services.query_planner import IntentType

        values = [e.value for e in IntentType]
        assert "log_analysis" in values


class TestLogAnalysisModels:
    """Pydantic 모델 테스트"""

    def test_log_entry_minimal(self):
        """LogEntry 최소 필드 생성"""
        entry = LogEntry(message="test message", raw="test message")

        assert entry.message == "test message"
        assert entry.raw == "test message"
        assert entry.level is None
        assert entry.timestamp is None

    def test_log_entry_full(self):
        """LogEntry 전체 필드 생성"""
        now = datetime(2026, 2, 18, 10, 0, 0)
        entry = LogEntry(
            timestamp=now,
            level="ERROR",
            message="error occurred",
            raw="2026-02-18 [ERROR] error occurred"
        )

        assert entry.timestamp == now
        assert entry.level == "ERROR"
        assert entry.message == "error occurred"

    def test_log_analysis_settings_defaults(self):
        """LogAnalysisSettings 기본값 확인"""
        settings = LogAnalysisSettings()

        assert settings.enabled is False
        assert settings.paths == []
        assert settings.masking.enabled is True
        assert settings.defaults.maxLines == 500
        assert settings.defaults.timeRangeMinutes == 60

    def test_masking_config_default_empty_patterns(self):
        """MaskingConfig 기본 패턴 목록은 빈 리스트"""
        config = MaskingConfig()

        assert config.enabled is True
        assert config.patterns == []

    def test_log_analysis_result_defaults(self):
        """LogAnalysisResult 기본값"""
        result = LogAnalysisResult()

        assert result.entries == []
        assert result.summary is None
        assert result.error_count == 0
        assert result.warn_count == 0
        assert result.time_range is None

    def test_log_path_model(self):
        """LogPath 모델 생성"""
        path = LogPath(
            id="p1",
            name="Application Log",
            path="/logs/app.log"
        )

        assert path.id == "p1"
        assert path.name == "Application Log"
        assert path.path == "/logs/app.log"
        assert path.enabled is True  # 기본값

    def test_masking_pattern_model(self):
        """MaskingPattern 모델 생성"""
        pattern = MaskingPattern(
            name="Test Pattern",
            regex=r"(\w+)=\S+",
            replacement=r"\1=***"
        )

        assert pattern.name == "Test Pattern"
        assert pattern.regex == r"(\w+)=\S+"
        assert pattern.replacement == r"\1=***"
