"""
파일 파서 서비스 테스트
"""

import pytest
from io import BytesIO
from fastapi import UploadFile, HTTPException

from app.services.file_parser import FileParser, ALLOWED_EXTENSIONS, MAX_FILE_SIZE


class MockUploadFile:
    """테스트용 UploadFile mock"""
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content

    async def read(self) -> bytes:
        return self._content


class TestFileParserValidation:
    """파일 검증 테스트"""

    @pytest.mark.asyncio
    async def test_allowed_extensions(self):
        """지원 확장자 확인"""
        assert '.md' in ALLOWED_EXTENSIONS
        assert '.txt' in ALLOWED_EXTENSIONS
        assert '.pdf' in ALLOWED_EXTENSIONS

    @pytest.mark.asyncio
    async def test_reject_unsupported_extension(self):
        """지원하지 않는 확장자 거부"""
        file = MockUploadFile("test.docx", b"content")
        with pytest.raises(HTTPException) as exc_info:
            await FileParser.parse(file)
        assert exc_info.value.status_code == 400
        assert "지원하지 않는 파일 형식" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_reject_exe_extension(self):
        """실행 파일 거부"""
        file = MockUploadFile("test.exe", b"content")
        with pytest.raises(HTTPException) as exc_info:
            await FileParser.parse(file)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_reject_file_too_large(self):
        """10MB 초과 파일 거부"""
        large_content = b"x" * (MAX_FILE_SIZE + 1)
        file = MockUploadFile("test.txt", large_content)
        with pytest.raises(HTTPException) as exc_info:
            await FileParser.parse(file)
        assert exc_info.value.status_code == 400
        assert "파일 크기 초과" in exc_info.value.detail


class TestFileParserMarkdown:
    """마크다운 파일 파싱 테스트"""

    @pytest.mark.asyncio
    async def test_parse_markdown_file(self):
        """마크다운 파일 파싱"""
        content = "# Title\n\nThis is content."
        file = MockUploadFile("test_document.md", content.encode('utf-8'))

        title, parsed_content = await FileParser.parse(file)

        assert title == "test_document"
        assert parsed_content == content

    @pytest.mark.asyncio
    async def test_parse_markdown_korean(self):
        """한글 마크다운 파일 파싱"""
        content = "# 결제 가이드\n\n이것은 결제 프로세스 설명입니다."
        file = MockUploadFile("payment_guide.md", content.encode('utf-8'))

        title, parsed_content = await FileParser.parse(file)

        assert title == "payment_guide"
        assert "결제 가이드" in parsed_content


class TestFileParserText:
    """텍스트 파일 파싱 테스트"""

    @pytest.mark.asyncio
    async def test_parse_txt_file(self):
        """텍스트 파일 파싱"""
        content = "Plain text content here."
        file = MockUploadFile("readme.txt", content.encode('utf-8'))

        title, parsed_content = await FileParser.parse(file)

        assert title == "readme"
        assert parsed_content == content

    @pytest.mark.asyncio
    async def test_parse_txt_korean(self):
        """한글 텍스트 파일 파싱"""
        content = "이것은 테스트 텍스트입니다.\n여러 줄이 있습니다."
        file = MockUploadFile("한글파일.txt", content.encode('utf-8'))

        title, parsed_content = await FileParser.parse(file)

        assert title == "한글파일"
        assert "테스트 텍스트" in parsed_content


class TestFileParserTitleExtraction:
    """제목 추출 테스트"""

    @pytest.mark.asyncio
    async def test_extract_title_from_filename(self):
        """파일명에서 제목 추출 (확장자 제외)"""
        file = MockUploadFile("my_document_v2.md", b"content")
        title, _ = await FileParser.parse(file)
        assert title == "my_document_v2"

    @pytest.mark.asyncio
    async def test_extract_title_with_dots(self):
        """점이 포함된 파일명 처리"""
        file = MockUploadFile("version.1.2.3.txt", b"content")
        title, _ = await FileParser.parse(file)
        assert title == "version.1.2.3"

    @pytest.mark.asyncio
    async def test_extract_title_uppercase_extension(self):
        """대문자 확장자 처리"""
        file = MockUploadFile("DOCUMENT.MD", b"content")
        title, _ = await FileParser.parse(file)
        assert title == "DOCUMENT"

    @pytest.mark.asyncio
    async def test_extract_title_mixed_case_extension(self):
        """혼합 대소문자 확장자 처리"""
        file = MockUploadFile("Test.Md", b"content")
        title, _ = await FileParser.parse(file)
        assert title == "Test"


class TestFileParserEdgeCases:
    """엣지 케이스 테스트"""

    @pytest.mark.asyncio
    async def test_empty_file(self):
        """빈 파일 처리"""
        file = MockUploadFile("empty.md", b"")
        title, content = await FileParser.parse(file)
        assert title == "empty"
        assert content == ""

    @pytest.mark.asyncio
    async def test_file_at_max_size(self):
        """정확히 최대 크기 파일 허용"""
        content = b"x" * MAX_FILE_SIZE
        file = MockUploadFile("large.txt", content)
        # 예외 없이 파싱되어야 함
        title, parsed_content = await FileParser.parse(file)
        assert title == "large"

    @pytest.mark.asyncio
    async def test_unicode_content(self):
        """유니코드 컨텐츠 처리"""
        content = "日本語テスト 한국어 테스트 emoji 🎉"
        file = MockUploadFile("unicode.txt", content.encode('utf-8'))
        title, parsed_content = await FileParser.parse(file)
        assert parsed_content == content
