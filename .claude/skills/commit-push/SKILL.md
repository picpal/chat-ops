---
name: commit-push
description: |
  Git commit and push workflow for ChatOps project. Use this skill when:
  (1) User asks to commit changes with "/commit" or "commit",
  (2) User asks to push changes with "/push" or "push",
  (3) User asks to commit and push together,
  (4) User requests to save/upload current work to git.
  Follows Conventional Commits format with project-specific scopes.
---

# Git Commit & Push Workflow

## Commit Message Format

```
type(scope): description

[optional body]

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `test`: Adding/updating tests
- `refactor`: Code refactoring (no feature change)
- `chore`: Build, config, dependency changes
- `perf`: Performance improvement
- `style`: Code style (formatting, no logic change)

### Scopes (Project-specific)
- `ui`: React frontend (services/ui)
- `ai`: AI Orchestrator Python (services/ai-orchestrator)
- `core`: Core API Java (services/core-api)
- `skill`: Claude Code skills
- `agent`: Agent configurations
- `db`: Database migrations/schemas
- No scope for cross-cutting changes

## Workflow

### 1. Check Status
```bash
git status
git diff --stat
```

### 2. Stage Changes
```bash
# Stage specific files
git add <files>

# Or stage all
git add -A
```

### 3. Create Commit
```bash
git commit -m "$(cat <<'EOF'
type(scope): concise description

Optional detailed explanation.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

### 4. Push (if requested)
```bash
git push origin <current-branch>
```

## Rules

1. **Never** use `-i` flag (interactive mode not supported)
2. **Never** use `--force` without explicit user request
3. **Never** commit `.env` or credential files
4. **Always** include Co-Authored-By line
5. **Always** verify staged files before committing
6. Write description in **Korean or English** matching user's language
7. Keep description under 50 characters, body under 72 chars/line

## Examples

```bash
# Feature
git commit -m "feat(ui): add Excel download to TableDetailModal"

# Bug fix
git commit -m "fix(ai): handle JSONB columns in Excel export"

# Documentation
git commit -m "docs: update API endpoint documentation"

# Multiple scopes (no scope)
git commit -m "feat: add end-to-end test infrastructure"
```
