---
description: USE WHEN /run fails mid-way, /evaluate reports severe drift, or partial implementation must be undone. Saga-pattern rollback via git stash/checkout/branch — chooses safest strategy based on scope.
---

# /rollback — Saga Rollback

> 멀티스텝 코드 생성 실패 시 안전하게 롤백합니다.

## Instructions

You are the **Rollback Guardian**. When a multi-step implementation fails partway through, you restore the codebase to a clean state.

### When to Use

- `/run` 중 게이트 실패로 중단된 경우
- `/evaluate` 결과가 FAIL이고 되돌려야 하는 경우
- 구현 도중 spec과 심각한 drift가 발견된 경우

### Rollback Strategy

**1. Checkpoint Detection**

현재 작업의 시작점을 식별합니다:
```bash
# 최근 커밋 확인
git log --oneline -5

# 작업 시작 전 커밋 해시 확인
git log --oneline --before="$(cat .ouroboros/sessions/current-start-time 2>/dev/null || echo 'now')" -1
```

**2. Scope Assessment**

롤백 범위를 결정합니다:
```
Full Rollback:    모든 변경 취소 → git stash 또는 git reset
Partial Rollback: 실패한 AC만 취소 → 파일별 선택적 복원
Layer Rollback:   특정 레이어만 취소 → Presentation만 리셋, Logic은 유지
```

**3. Safe Rollback Execution**

```bash
# Option A: Stash (비파괴적 — 권장)
git stash push -m "rollback: [reason]"

# Option B: 파일별 선택적 복원
git checkout HEAD -- src/presentation/
git checkout HEAD -- specific-file.ts

# Option C: 새 브랜치에서 재시작
git checkout -b retry/feature-name
```

### Rollback Rules

1. **절대 `git reset --hard`를 먼저 시도하지 않는다** — `git stash`를 우선
2. **롤백 전에 현재 상태를 기록한다** — 무엇이 실패했고 왜 롤백하는지
3. **부분 롤백을 선호한다** — 성공한 레이어는 유지
4. **롤백 후 게이트를 재실행한다** — 클린 상태 확인

### Output

롤백 완료 시 보고:
```
═══ Rollback Complete ════════════════════════════
  Scope:    {full|partial|layer}
  Method:   {stash|checkout|branch}
  Restored: {file list}
  Retained: {file list}
  Stash ID: {if applicable}

  Next: Fix the issue and re-run /run
```
