---
name: cp
description: |
  Git commit & push in one command. Trigger: "/cp", "/save", "cp", "save", "저장".
  Auto: status → stage → commit → push. Use when saving work to git.
---

# Git Commit & Push (Single Command)

When triggered, execute ALL steps automatically without asking:

## Automatic Workflow

```bash
# 1. Check current branch
git branch --show-current

# 2. Check status
git status
git diff --stat

# 3. Stage all changes (exclude .env, credentials)
git add -A

# 4. Commit with conventional format
git commit -m "$(cat <<'EOF'
type(scope): description

Body if needed.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"

# 5. Push immediately
git push origin <current-branch>
```

## Commit Message Format

```
type(scope): description (under 50 chars)
```

### Types
| Type | Use |
|------|-----|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `test` | Tests |
| `refactor` | Refactoring |
| `chore` | Config/build |

### Scopes
| Scope | Path |
|-------|------|
| `ui` | services/ui |
| `ai` | services/ai-orchestrator |
| `core` | services/core-api |
| `skill` | .claude/skills |
| `db` | Database/migrations |
| (none) | Cross-cutting |

## Rules

1. **Always** push after commit (single workflow)
2. **Never** use `--force` or `-i` flags
3. **Never** commit `.env` or credential files
4. **Always** include `Co-Authored-By` line
5. Group related changes into logical commits if multiple features exist

---

## PR 생성 모드

### 트리거

| 명령 | 동작 |
|------|------|
| `/cp --pr` | Commit + Push + PR 생성 |
| `/save --pr` | Commit + Push + PR 생성 |
| `/pr` | 현재 브랜치에서 PR만 생성 (이미 push된 상태) |

### PR 생성 워크플로우

```bash
# 1. 브랜치 검증
BRANCH=$(git branch --show-current)
if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
  echo "WARNING: main/master 브랜치에서는 PR을 생성할 수 없습니다."
  exit 1
fi

# 2. 브랜치 네이밍 검증
if ! echo "$BRANCH" | grep -qE "^(feat|fix|refactor|docs|test|chore)/"; then
  echo "WARNING: 브랜치명이 컨벤션을 따르지 않습니다: <type>/<description>"
fi

# 3. 변경사항 Stage & Commit (--pr 옵션 시)
git add -A
git commit -m "$(cat <<'EOF'
type(scope): description

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"

# 4. Push
git push -u origin $BRANCH

# 5. PR 생성
gh pr create --title "<type>(scope): description" --body "$(cat <<'EOF'
## Summary
- 변경 요약 1
- 변경 요약 2

## Changes
- `file1.ext` - 변경 내용
- `file2.ext` - 변경 내용

## Test Plan
- [ ] 단위 테스트 통과
- [ ] 빌드 성공
- [ ] 린트 에러 없음

---
Generated with Claude Code
EOF
)"
```

### 자동 PR Body 생성

PR body는 다음 정보를 자동으로 포함합니다:

```markdown
## Summary
[변경 요약 - 커밋 메시지 기반]

## Changes
- `path/to/file1.ext` - 변경 내용
- `path/to/file2.ext` - 변경 내용

## Test Plan
- [ ] 단위 테스트 통과
- [ ] 빌드 성공
- [ ] 린트 에러 없음

---
Generated with Claude Code
```

### 브랜치 검증

| 상황 | 동작 |
|------|------|
| main/master 브랜치에서 실행 | 경고 후 중단 |
| 브랜치 네이밍 컨벤션 불일치 | 경고 표시 (계속 진행) |
| 이미 PR이 존재 | 기존 PR 링크 표시 |

### 예시

```bash
# Feature 브랜치에서 작업 후 PR까지 한 번에
/cp --pr

# 이미 push된 상태에서 PR만 생성
/pr

# 일반 커밋 & 푸시 (PR 없이)
/cp
```

### 7-Phase 워크플로우 통합

| Phase | 명령 |
|-------|------|
| Phase 4 (IMPLEMENT) | `/cp` - 중간 작업 저장 |
| Phase 6 (PR REVIEW) | `/cp --pr` 또는 `/pr` - PR 생성 |
