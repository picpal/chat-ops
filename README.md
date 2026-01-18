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
