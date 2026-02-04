"""파일 파싱 서비스 - md, txt, pdf 지원"""

import os
from typing import Tuple
from fastapi import UploadFile, HTTPException

ALLOWED_EXTENSIONS = {'.md', '.txt', '.pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class FileParser:
    @staticmethod
    async def parse(file: UploadFile) -> Tuple[str, str]:
        """
        파일을 파싱하여 (title, content) 반환
        - title: 파일명에서 추출 (확장자 제외)
        - content: 파일 내용
        """
        # 1. 확장자 검증
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"지원하지 않는 파일 형식: {ext}")

        # 2. 파일 크기 검증
        content_bytes = await file.read()
        if len(content_bytes) > MAX_FILE_SIZE:
            raise HTTPException(400, f"파일 크기 초과: 최대 10MB")

        # 3. 파일 파싱
        title = os.path.splitext(file.filename)[0]

        if ext == '.pdf':
            content = FileParser._parse_pdf(content_bytes)
        else:
            try:
                content = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                raise HTTPException(400, "파일 인코딩 오류: UTF-8 형식이 아닙니다.")

        return title, content

    @staticmethod
    def _parse_pdf(content_bytes: bytes) -> str:
        """PDF 파일에서 텍스트 추출"""
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
        from io import BytesIO

        try:
            reader = PdfReader(BytesIO(content_bytes))
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text() or '')
            return '\n\n'.join(text_parts)
        except PdfReadError as e:
            raise HTTPException(400, f"PDF 파일 읽기 오류: {str(e)}")
        except Exception as e:
            raise HTTPException(400, f"PDF 파싱 오류: {str(e)}")
