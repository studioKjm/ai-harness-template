---
description: Break seed AC into atomic layer-aware tasks BEFORE /run. USE WHENEVER implementation spans multiple files or layers. Prevents mega-prompts; each unit is independently implementable and testable.
---

# /decompose — Atomic Task Decomposition

> /run 전에 태스크를 원자적 단위로 분해하고 검증합니다.
> 메가 프롬프트를 방지하고, 각 단위가 독립적으로 구현/테스트 가능하도록 합니다.

## Instructions

You are the **Task Decomposer**. Your job is to break down seed spec acceptance criteria into atomic, implementable units.

### Why Decompose?

- AI 에이전트는 큰 태스크보다 작은 태스크에서 정확도가 높다
- 원자적 태스크는 독립적으로 테스트 가능하다
- 실패 시 롤백 범위가 작다
- 진행률 추적이 명확하다

### Decomposition Rules

**1. Atomic Unit Criteria**

각 태스크는 다음 조건을 모두 만족해야 합니다:
- [ ] **단일 레이어** — 한 태스크가 하나의 레이어(P/L/D)만 터치
- [ ] **단일 AC** — 한 태스크가 하나의 Acceptance Criteria에 기여
- [ ] **독립 테스트 가능** — 다른 태스크 완료 없이도 테스트 가능
- [ ] **30분 이내 구현** — 너무 크면 더 분해
- [ ] **명확한 완료 기준** — "~가 되면 완료"

**2. Decomposition Process**

시드 스펙의 각 AC를 분해합니다:

```
AC-001: "사용자가 검색어를 입력하면 관련 매물을 보여준다"
    ↓
Task 1 [Data]:    검색 쿼리 레포지토리 메서드 구현 + 테스트
Task 2 [Logic]:   검색 필터링 서비스 (거리 2km, 미판매) + 테스트
Task 3 [Logic]:   검색 결과 정렬/페이지네이션 서비스 + 테스트
Task 4 [Present]: 검색 API 엔드포인트 + 테스트
Task 5 [Present]: 검색 UI 컴포넌트 + 테스트
```

**3. Dependency Ordering**

태스크 간 의존성을 명시하고 실행 순서를 결정합니다:

```
Task 1 (Data)
    ↓
Task 2 (Logic) ← depends on Task 1
Task 3 (Logic) ← depends on Task 1
    ↓
Task 4 (Present) ← depends on Task 2, 3
Task 5 (Present) ← depends on Task 4
```

### Validation Checklist

분해 완료 후 검증:

```
═══ Decomposition Validation ══════════════════════
  Total tasks:     {N}
  By layer:        Data: {n} | Logic: {n} | Present: {n}
  Dependencies:    {dependency graph valid? YES/NO}
  All testable:    {YES/NO}
  All < 30min:     {YES/NO}
  AC coverage:     {all ACs covered? YES/NO}
  ─────────────────────────────
  Result:          VALID | NEEDS_REFINE
```

### Anti-patterns to Detect

| Anti-pattern | 증상 | 해결 |
|-------------|------|------|
| **Mega Task** | 하나의 태스크가 여러 레이어를 터치 | 레이어별로 분할 |
| **Orphan Task** | 어떤 AC에도 기여하지 않는 태스크 | 제거 또는 AC에 연결 |
| **Circular Dep** | 태스크 A→B→A 순환 의존 | 공통 부분을 별도 태스크로 추출 |
| **Missing Test** | 테스트 작성이 계획에 없음 | 각 태스크에 테스트 포함 |
| **Too Small** | 한 줄짜리 태스크 | 관련 태스크와 병합 |

### Output Format

```yaml
decomposition:
  seed_ref: "seed-v1.yaml"
  total_tasks: N
  tasks:
    - id: "T-001"
      ac_ref: "AC-001"
      layer: "data"
      description: "검색 쿼리 레포지토리 메서드 구현"
      test: "검색 조건별 쿼리 결과 검증"
      depends_on: []
      estimated_minutes: 20
    - id: "T-002"
      ac_ref: "AC-001"
      layer: "logic"
      description: "검색 필터링 서비스 구현"
      test: "거리/판매상태 필터 로직 단위 테스트"
      depends_on: ["T-001"]
      estimated_minutes: 25
  execution_order:
    - phase: 1
      tasks: ["T-001"]
    - phase: 2
      tasks: ["T-002", "T-003"]
    - phase: 3
      tasks: ["T-004", "T-005"]
```

### After Decomposition

분해가 완료되면:
1. 사용자에게 태스크 목록과 실행 순서를 제시
2. 확인 후 `/run`으로 각 태스크를 순서대로 실행
3. 각 태스크 완료 시 즉시 테스트 실행
4. 태스크 실패 시 `/rollback`으로 해당 태스크만 되돌림
