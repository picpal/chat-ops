---
name: setup
description: |
  프로젝트 초기 설정을 자동화합니다. Docker 환경 확인, API 키 설정,
  전체 스택 실행, RAG 문서 시딩까지 한 번에 수행합니다.

  사용 시점: 새 PC에서 프로젝트를 처음 설정할 때, 개발 환경 초기화가 필요할 때
---

# ChatOps 프로젝트 초기 설정 Skill

You are a project setup assistant for the ChatOps development environment.
모든 응답은 한국어로 합니다.

## Your Role

새 PC에서 프로젝트를 처음 설정하는 사용자를 위해 전체 개발 환경을 자동 구축합니다.

## Setup Steps

### Step 1: 사전 조건 확인

1. Docker 설치 및 실행 확인:
   ```bash
   docker info > /dev/null 2>&1
   ```
   - 실패 시: "Docker Desktop을 설치하고 실행해주세요" 안내

2. 필요 포트 사용 가능 여부 확인 (80, 3000, 5432, 8000, 8080):
   ```bash
   lsof -i :PORT 2>/dev/null
   ```
   - 사용 중인 포트가 있으면 어떤 프로세스가 사용 중인지 알려주고 해결 방법 제시

### Step 2: 환경 변수 설정

1. AskUserQuestion으로 LLM 제공자 선택 (OpenAI / Anthropic)
2. 선택한 제공자에 맞는 API 키 입력 요청
3. LLM 모델 선택:
   - OpenAI: gpt-4o-mini (권장, 저렴) / gpt-4o (고성능)
   - Anthropic: claude-3-5-haiku-latest (권장, 저렴) / claude-sonnet-4-20250514 (균형)
4. infra/docker/.env 파일 생성:
   ```
   POSTGRES_DB=chatops
   POSTGRES_USER=chatops_user
   POSTGRES_PASSWORD=chatops_pass
   POSTGRES_READONLY_PASS=readonly_pass

   # LLM Provider 설정
   LLM_PROVIDER=<openai 또는 anthropic>
   OPENAI_API_KEY=<OpenAI 선택 시>
   ANTHROPIC_API_KEY=<Anthropic 선택 시>
   LLM_MODEL=<선택한 모델>

   RAG_ENABLED=true
   LOG_LEVEL=INFO
   ```

### Step 3: Docker Compose 실행

1. infra/docker 디렉토리로 이동
2. 전체 스택 빌드 및 실행:
   ```bash
   docker compose -f infra/docker/docker-compose.yml up -d --build
   ```
3. 빌드 진행 상황을 사용자에게 보여줌

### Step 4: 서비스 헬스체크

각 서비스가 정상 시작될 때까지 대기:
1. PostgreSQL: `docker compose -f infra/docker/docker-compose.yml exec -T postgres pg_isready -U chatops_user -d chatops`
2. Core API: `curl -sf http://localhost:8080/api/v1/query/health`
3. AI Orchestrator: `curl -sf http://localhost:8000/health`
4. UI: `curl -sf http://localhost:3000`

각 서비스 상태를 체크마크로 표시하며 진행

### Step 5: 데이터 시딩 (선택)

1. AskUserQuestion으로 RAG 테스트 문서 생성 여부 질문
2. RAG 시딩 선택 시:
   ```bash
   python3 scripts/seed-rag-documents.py
   python3 scripts/update-embeddings.py
   ```

3. AskUserQuestion으로 테스트 데이터 시딩 여부 및 규모 질문:
   - **skip**: 시딩하지 않음 (기존 DB 마이그레이션 데이터만 사용)
   - **small**: 가맹점 3개, 결제 300건 (빠른 테스트용)
   - **medium (권장)**: 가맹점 10개, 결제 1,000건 (일반 개발용)
   - **large**: 가맹점 30개, 결제 10,000건 (대용량 테스트)

4. 테스트 데이터 시딩 선택 시:
   ```bash
   python3 scripts/seed-test-data.py --scale <선택값>
   ```

5. 시딩 결과 통계 출력

### Step 6: 설정 완료 안내

성공 메시지와 함께 다음 정보 표시:
- UI: http://localhost:3000
- Core API: http://localhost:8080
- AI Orchestrator: http://localhost:8000
- PostgreSQL: localhost:5432

빠른 시작 가이드:
- 채팅 테스트: "오늘 결제 현황 알려줘"
- 서비스 중지: `./scripts/dev-down.sh`
- 로그 확인: `docker compose -f infra/docker/docker-compose.yml logs -f [service]`

## Error Handling

| 오류 상황 | 대응 방법 |
|----------|----------|
| Docker 미실행 | Docker Desktop 설치/실행 안내 |
| 포트 충돌 | 충돌 프로세스 확인 및 종료 방법 안내 |
| 빌드 실패 | 관련 에러 로그 표시 및 해결책 제시 |
| API 키 오류 | 올바른 키 재입력 요청 |

## 헬스체크 대기 로직

```bash
# PostgreSQL 대기 (최대 60초)
timeout=60
while ! docker compose -f infra/docker/docker-compose.yml exec -T postgres pg_isready -U chatops_user -d chatops > /dev/null 2>&1; do
    sleep 2
    timeout=$((timeout - 2))
    if [ $timeout -le 0 ]; then
        echo "PostgreSQL 시작 실패"
        exit 1
    fi
done

# Core API 대기 (최대 120초 - Java 빌드 시간)
timeout=120
while ! curl -sf http://localhost:8080/api/v1/query/health > /dev/null 2>&1; do
    sleep 5
    timeout=$((timeout - 5))
    if [ $timeout -le 0 ]; then
        echo "Core API 시작 실패"
        exit 1
    fi
done
```

## Important Notes

- 이 skill은 순차적으로 각 단계를 수행합니다.
- 각 단계에서 오류가 발생하면 즉시 사용자에게 알리고 해결 방법을 안내합니다.
- Docker 이미지 빌드는 최초 실행 시 3-5분 정도 소요될 수 있습니다.
- RAG 문서 시딩은 선택사항이며, 임베딩 생성에 API 호출이 필요합니다.
- 테스트 데이터 시딩은 선택사항이며, DB 마이그레이션과 별도로 추가 데이터를 생성합니다.
- 테스트 데이터는 기존 마이그레이션 데이터(V12)와 ID가 충돌하지 않도록 별도 prefix를 사용합니다.
