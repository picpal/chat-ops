# ChatOps (AI Backoffice)

## Prerequisites
- Docker & Docker Compose

## Quick Start

### Option 1: Claude Code 사용 (권장)

```bash
/setup
```

`/setup` 명령어가 자동으로 수행하는 작업:
- Docker 설치 및 실행 상태 확인
- 필요 포트 (80, 3000, 5432, 8000, 8080) 가용성 확인
- LLM 제공자 선택 (OpenAI / Anthropic) 및 API 키 설정
- 환경 변수 파일 자동 생성
- Docker Compose로 전체 스택 빌드 및 실행
- 각 서비스 헬스체크
- RAG 문서 시딩 (선택)

### Option 2: 수동 설정

```bash
# 1. 환경 설정
cp infra/docker/.env.example infra/docker/.env
# .env 파일에서 API 키 설정 (OPENAI_API_KEY 또는 ANTHROPIC_API_KEY)

# 2. 실행
cd infra/docker
docker compose up -d --build

# 3. 종료
docker compose down
```

## Ports
| Service | URL |
|---------|-----|
| UI | http://localhost:3000 |
| AI Orchestrator | http://localhost:8000 |
| Core API | http://localhost:8080 |
| PostgreSQL | localhost:5432 |

## Local Development (Optional)
PostgreSQL만 Docker로 실행하고 나머지는 로컬에서 개발:
```bash
./scripts/dev-up.sh
```

## Features

### 핵심 기능
- **자연어 데이터 조회**: Text-to-SQL 또는 QueryPlan 기반으로 자연어를 DB 쿼리로 변환
- **RAG 기반 업무 지식 응답**: pgvector를 활용한 문서 검색 및 LLM 답변 생성
- **Quality Answer RAG**: 높은 별점(4~5점) 답변을 자동 저장하고 유사 질문 시 참고
- **일일점검 템플릿**: 결제/환불/정산 현황을 한 번에 조회
- **시나리오 관리**: 별점 분석 대시보드로 AI 응답 품질 모니터링

### Quality Answer RAG
사용자가 높은 별점(4~5점)을 부여한 답변을 자동으로 저장하고, 유사한 질문이 들어오면 해당 답변을 참고하여 일관되고 품질 높은 응답을 생성합니다.

- **자동 저장**: 별점 4점 이상 답변 자동 저장
- **유사 검색**: 새 질문 시 유사도 기반 고품질 답변 검색
- **토글 제어**: 시나리오 관리 페이지에서 ON/OFF 가능

## Demo

### 업무 데이터 조회
자연어로 PG 결제/환불/정산 데이터를 조회하는 시연입니다.

![업무 데이터 조회 데모](./assets/demos/data-query-demo.gif)

**주요 기능:**
- 자연어 → QueryPlan/Text-to-SQL 변환
- 결제/환불/정산 데이터 실시간 조회
- 집계 결과 마크다운 테이블 렌더링

---

### 업무지식 기반 조회
RAG 기반으로 업무 지식을 검색하고 LLM이 답변을 생성하는 시연입니다.

![업무지식 기반 조회 데모](./assets/demos/knowledge-query-demo.gif)

**주요 기능:**
- pgvector 벡터 검색으로 관련 문서 탐색
- LLM이 문서 기반 답변 생성
- 참조 문서 출처 표시

---

### 답변 평가
AI 응답에 별점을 부여하고 품질을 관리하는 시연입니다.

![답변 평가 데모](./assets/demos/rating-demo.gif)

**주요 기능:**
- 1~5점 별점 평가
- 시나리오 관리 페이지에서 통계 확인
- Quality Answer RAG로 고품질 답변 자동 저장

---

### 일일점검 시나리오
자연어로 PG 결제 백오피스 데이터를 조회하는 일일점검 테스트 시연입니다.

![일일점검 데모](./assets/demos/daily-check-demo.gif)

**테스트 시나리오:**
1. 어제 결제 현황 조회 (건수, 금액, 결제수단별 분포)
2. 환불/취소 현황 확인
3. 정산 상태 점검
4. 이상 거래 탐지
