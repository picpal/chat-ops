# ChatOps (AI Backoffice)

## Prerequisites
- Docker & Docker Compose

## Quick Start

```bash
# 1. 환경 설정
cp infra/docker/.env.example infra/docker/.env
# .env 파일에서 OPENAI_API_KEY 설정 필수

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
