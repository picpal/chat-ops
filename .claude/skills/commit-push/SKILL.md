---
name: commit-push
description: |
  Git commit and push in one command for ChatOps project. Trigger with "/commit-push" or "커밋 푸시".
  Automatically: (1) Check status, (2) Stage all changes, (3) Commit with Conventional Commits format, (4) Push to origin.
  Use when user wants to save and upload current work to git repository.
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
