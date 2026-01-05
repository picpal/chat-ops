#!/usr/bin/env python3
"""
문서 임베딩 업데이트 스크립트
OpenAI API를 사용하여 문서 임베딩을 생성합니다.
"""

import os
import sys
import psycopg
from pgvector.psycopg import register_vector

try:
    from openai import OpenAI
except ImportError:
    print("openai 패키지가 설치되어 있지 않습니다.")
    print("설치: pip3 install openai")
    sys.exit(1)

# 설정
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://chatops_user:chatops_pass@localhost:5432/chatops"
)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-ada-002"
BATCH_SIZE = 10


def create_embedding(client: OpenAI, text: str) -> list:
    """OpenAI로 텍스트 임베딩 생성"""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding


def update_embeddings():
    """임베딩이 없는 문서들의 임베딩을 생성"""
    print("=" * 50)
    print("문서 임베딩 업데이트 시작")
    print("=" * 50)

    if not OPENAI_API_KEY:
        print("✗ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("  export OPENAI_API_KEY=sk-...")
        sys.exit(1)

    # OpenAI 클라이언트 초기화
    client = OpenAI(api_key=OPENAI_API_KEY)
    print("✓ OpenAI 클라이언트 초기화 완료")

    # 데이터베이스 연결
    try:
        conn = psycopg.connect(DATABASE_URL)
        register_vector(conn)
        print("✓ 데이터베이스 연결 성공")
    except Exception as e:
        print(f"✗ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    try:
        with conn.cursor() as cur:
            # 임베딩이 없는 문서 개수 확인
            cur.execute("SELECT COUNT(*) FROM documents WHERE embedding IS NULL")
            pending_count = cur.fetchone()[0]

            if pending_count == 0:
                print("\n모든 문서에 이미 임베딩이 있습니다.")
                return

            print(f"\n임베딩이 필요한 문서: {pending_count}개")
            print()

            # 배치로 처리
            updated_count = 0
            while True:
                cur.execute(
                    """
                    SELECT id, title, content
                    FROM documents
                    WHERE embedding IS NULL
                    LIMIT %s
                    """,
                    (BATCH_SIZE,)
                )
                rows = cur.fetchall()

                if not rows:
                    break

                for row in rows:
                    doc_id, title, content = row
                    try:
                        # 제목과 내용을 결합하여 임베딩 생성
                        text = f"{title}\n\n{content}"
                        embedding = create_embedding(client, text)

                        # 임베딩 저장
                        cur.execute(
                            "UPDATE documents SET embedding = %s::vector WHERE id = %s",
                            (embedding, doc_id)
                        )
                        conn.commit()

                        updated_count += 1
                        print(f"  [{updated_count}/{pending_count}] {title[:50]}")

                    except Exception as e:
                        print(f"  ✗ 문서 {doc_id} 임베딩 실패: {e}")
                        continue

            print()
            print("=" * 50)
            print(f"✓ 임베딩 업데이트 완료: {updated_count}개")
            print("=" * 50)

            # 최종 현황 출력
            cur.execute(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(embedding) as with_embedding
                FROM documents
                """
            )
            row = cur.fetchone()
            print(f"\n현재 상태: 전체 {row[0]}개 중 {row[1]}개 임베딩 완료")

    except Exception as e:
        print(f"✗ 임베딩 업데이트 실패: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    update_embeddings()
