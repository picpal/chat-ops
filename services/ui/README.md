# ChatOps UI

> React 기반 AI 백오피스 프론트엔드

## Tech Stack

- **React 18** + TypeScript
- **Vite** 빌드 시스템
- **Tailwind CSS** 스타일링
- **Zustand** 상태 관리
- **TanStack Query** 데이터 페칭
- **Recharts** 데이터 시각화
- **React Markdown** 마크다운 렌더링

## 실행 방법

### Prerequisites

- Node.js 18+
- 백엔드 서비스 실행 중:
  - AI Orchestrator: `http://localhost:8000`
  - Core API: `http://localhost:8080`

### 설치 및 실행

```bash
# 의존성 설치
npm install

# 개발 서버 시작
npm run dev
```

앱이 http://localhost:3000 에서 시작됩니다.

### 스크립트

| 명령어 | 설명 |
|--------|------|
| `npm run dev` | 개발 서버 시작 |
| `npm run build` | 프로덕션 빌드 |
| `npm run preview` | 빌드 미리보기 |
| `npm run lint` | ESLint 실행 |
| `npm run type-check` | TypeScript 타입 검사 |

## 현재 구현 상태

### 핵심 기능

- ✅ 채팅 인터페이스 (실시간 메시징)
- ✅ 사이드바 네비게이션 + 세션 히스토리
- ✅ RenderSpec 렌더러 (Table, Text, Chart, Log)
- ✅ 페이지네이션 (queryToken 기반)
- ✅ 별점 평가 시스템 (1-5점)
- ✅ 시나리오 관리 대시보드
- ✅ Quality Answer RAG 토글
- ✅ 마크다운 테이블 렌더링

### 페이지 구성

| 경로 | 컴포넌트 | 설명 |
|------|----------|------|
| `/` | `ChatPage` | 채팅 인터페이스 |
| `/scenarios` | `ScenariosPage` | 시나리오 관리 대시보드 |
| `/documents` | `DocumentsPage` | RAG 문서 관리 |

## 프로젝트 구조

```
src/
├── api/              # API 클라이언트
│   ├── chat.ts
│   ├── documents.ts
│   ├── ratings.ts
│   └── settings.ts
├── components/
│   ├── chat/         # 채팅 컴포넌트
│   │   ├── ChatInput.tsx
│   │   ├── ChatMessage.tsx
│   │   └── MessageRating.tsx
│   ├── common/       # 공통 UI
│   ├── layout/       # 레이아웃 (Sidebar, Header)
│   ├── modals/       # 모달 다이얼로그
│   ├── renderers/    # RenderSpec 렌더러
│   │   ├── TableRenderer.tsx
│   │   ├── ChartRenderer.tsx
│   │   └── TextRenderer.tsx
│   └── scenarios/    # 시나리오 관리
│       ├── ScenariosPage.tsx
│       ├── QualityAnswerToggle.tsx
│       └── RatingSummaryCards.tsx
├── hooks/            # 커스텀 훅
│   ├── useChat.ts
│   ├── useRatings.ts
│   └── useSettings.ts
├── store/            # Zustand 스토어
├── types/            # TypeScript 타입
└── utils/            # 유틸리티
```

## 주요 컴포넌트

### ChatMessage

AI 응답 메시지 렌더링:
- 마크다운 파싱 및 렌더링
- RenderSpec 기반 테이블/차트 표시
- 별점 평가 UI

### ScenariosPage

시나리오 관리 대시보드:
- 기간별 필터 (오늘/7일/30일/전체)
- 별점 분포 차트
- 상세 목록 테이블
- Quality Answer RAG 토글

### QualityAnswerToggle

고품질 답변 RAG 기능 ON/OFF:
- 실시간 상태 조회
- 저장된 답변 수 표시
- 토글 상태 변경

## 환경 변수

```env
VITE_AI_API_URL=http://localhost:8000
VITE_CORE_API_URL=http://localhost:8080
VITE_APP_NAME=ChatOps AI Backoffice
VITE_APP_VERSION=2.4
```

## 디자인 시스템

### 색상

| 용도 | 색상 |
|------|------|
| Primary | `#137fec` |
| Success | `emerald-500/600/700` |
| Error | `red-500/600/700` |
| Warning | `amber-500/600/700` |
| Neutral | `slate-50 ~ slate-900` |

### 타이포그래피

- 폰트: Inter (400, 500, 700, 900)
- 아이콘: Material Symbols Outlined

## 트러블슈팅

### CORS 오류

Vite 프록시 설정 확인 (`vite.config.ts`):
```ts
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true
  }
}
```

### API 연결 오류

1. 백엔드 서비스 실행 확인:
   - AI: `curl http://localhost:8000/health`
   - Core: `curl http://localhost:8080/api/v1/query/health`

2. `.env` 파일 확인

### 빌드 오류

```bash
# 클린 설치
rm -rf node_modules package-lock.json
npm install

# Vite 캐시 삭제
rm -rf node_modules/.vite
npm run dev
```

## API 통합

### AI Orchestrator API

```typescript
// 채팅 메시지 전송
POST /api/v1/chat
{ message: string, sessionId?: string }

// 별점 저장
POST /api/v1/ratings
{ requestId: string, rating: number }

// Quality Answer RAG 상태
GET /api/v1/settings/quality-answer-rag/status
```

### Core API

```typescript
// QueryPlan 실행
POST /api/v1/query/start
{ requestId, entity, operation, filters, timeRange }

// 페이지네이션
GET /api/v1/query/page/{token}
```
