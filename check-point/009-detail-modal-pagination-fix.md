# 009. 상세보기 모달 페이지네이션 버그 수정

## 날짜
2026-01-13

## 문제 상황

### 증상
1. "최근 거래 30건 보여줘" 입력 시 미리보기는 30건 정상 표시
2. 상세보기(모달) 클릭 시:
   - 30건이 아닌 전체 1,000건이 표시됨
   - 페이지네이션 버튼 클릭 시 동작하지 않음

### 콘솔 에러
```
Access to XMLHttpRequest at 'http://localhost:8080/api/v1/query/page/.../goto/4'
from origin 'http://localhost:3000' has been blocked by CORS policy:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

## 근본 원인

### 1. CORS 설정 누락
- Core API의 `/api/v1/query/page/{token}/goto/{pageNumber}` 엔드포인트에 CORS 헤더 없음
- UI(localhost:3000)에서 Core API(localhost:8080)로의 요청 차단

### 2. 상세보기 설계 의도 불일치
- 기존 설계: 상세보기에서 전체 데이터를 서버 페이지네이션으로 표시
- 사용자 기대: "30건 보여줘" 요청 시 상세보기에서도 30건만 표시

## 수정 내용

### 1. Core API CORS 설정 추가
**파일**: `services/core-api/src/main/java/com/chatops/core/controller/QueryController.java`

```java
@Slf4j
@RestController
@RequestMapping("/api/v1/query")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")  // 추가
public class QueryController {
```

### 2. 상세보기 서버 페이지네이션 비활성화
**파일**: `services/ui/src/components/modals/TableDetailModal.tsx`

```typescript
// 변경 전
const useServerSide = !!(
  serverPagination?.queryToken &&
  (serverPagination?.hasMore || (serverPagination?.totalRows ?? 0) > initialRows.length)
)

// 변경 후
// 상세보기에서는 요청한 건수만 표시 (전체 DB가 아님)
const useServerSide = false
```

## 동작 변경

### 변경 전
- 미리보기: 30건
- 상세보기: 1,000건 (전체 DB, 서버 페이지네이션)

### 변경 후
- 미리보기: 30건
- 상세보기: 30건 (요청한 건수, 클라이언트 페이지네이션으로 10건씩)

## 배포 절차

```bash
# Core API 재빌드 및 재시작
docker-compose -f infra/docker/docker-compose.yml build core-api
docker-compose -f infra/docker/docker-compose.yml up -d core-api

# UI는 Vite HMR로 자동 반영
```

## 테스트 확인

1. "최근 거래 30건 보여줘" 입력
2. 미리보기에서 30건 확인
3. 상세보기 버튼 클릭
4. 상세보기에서 30건만 표시되는지 확인
5. 클라이언트 페이지네이션 동작 확인 (10건씩)

## 향후 고려사항

- 사용자가 "전체 조회"를 명시적으로 요청할 경우 서버 페이지네이션 활성화 로직 필요
- 현재는 모든 상세보기에서 요청한 건수만 표시
