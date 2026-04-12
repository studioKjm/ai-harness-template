---
description: Execute seed spec via Double Diamond (Discover → Define → Design → Deliver). USE AFTER /decompose. Enforces D→L→P implementation order, writes tests immediately, runs gates continuously.
---

# /run — Double Diamond Execution

> 시드 스펙을 기반으로 Double Diamond 프로세스를 실행한다

## Instructions

You are now the **Executor**. Follow the Double Diamond methodology strictly.

### Phase 0: State Audit (FIRST STEP)

1. **Read latest seed** from `.harness/ouroboros/seeds/seed-v*.yaml`
2. **Check for prior run artifacts**:
   - Uncommitted changes? (`git status`) — existing work to resume?
   - Decomposed tasks in `.harness/ouroboros/tasks/`? — pick up unfinished
   - Prior evaluation results? — check if failed tasks need retry
3. **Determine mode**:
   - No prior work → **fresh run**
   - Partial work + decomposed tasks → **resume** (skip completed, continue pending)
   - Uncommitted + no tasks → ask user: continue manually or `/rollback` first?

### Prerequisites
1. Seed spec must exist in `.harness/ouroboros/seeds/`
2. Read the latest seed spec before starting
3. If no seed exists, prompt user to run `/interview` then `/seed`

### Double Diamond Process

```
  Discover          Define           Design          Deliver
  (넓게 탐색)       (좁혀 확정)       (넓게 설계)     (좁혀 구현)
    /\                \/                /\              \/
   /  \              /  \              /  \            /  \
  /    \            /    \            /    \          /    \
 /      \          /      \          /      \        /      \
```

### Subagent Delegation

실행 효율을 높이기 위해 **subagent를 활용**합니다:

```
Main Agent (Executor)
  ├─ Subagent(Explore) → Phase 1: 코드베이스 탐색, 영향 범위 분석
  ├─ Subagent(Explore) → Phase 1: 관련 패턴/라이브러리 조사  (병렬)
  ├─ Main              → Phase 2-3: 정의 및 설계 (subagent 결과 기반)
  └─ Main              → Phase 4: 구현 (직접 수행)
```

**Claude Code에서 subagent 사용**:
- Discover 단계에서 `Agent` 도구로 Explore 에이전트를 spawn하여 코드베이스 탐색 위임
- 여러 탐색을 **병렬**로 실행하여 시간 절약
- 결과를 받아 메인 에이전트가 Define/Design/Deliver 수행
- worktree 격리가 필요한 실험적 구현은 `isolation: "worktree"`로 별도 브랜치에서 진행

### Phase 1: Discover (탐색)

문제를 넓게 탐색합니다 (subagent 병렬 탐색 권장):
- 시드 스펙의 goal과 constraints를 다시 읽는다
- 관련 코드베이스를 탐색한다 (기존 코드가 있다면)
- 유사한 패턴이나 라이브러리가 있는지 조사한다
- 영향 받는 파일/모듈을 식별한다
- 잠재적 리스크를 나열한다

**Output**: Discovery notes (inline, 별도 파일 불필요)

### Phase 2: Define (정의)

핵심 문제를 좁혀 확정합니다:
- Discovery에서 나온 정보를 바탕으로 실제 해결할 범위를 확정
- 구현 순서를 결정 (의존성 기반)
- 파일별 변경 계획을 세운다
- 테스트 전략을 결정한다

**Output**: Implementation plan (task list)

### Phase 3: Design (설계) — Layer-Aware

해결 방법을 3-tier 레이어 기준으로 설계합니다:

**3a. 레이어 영향 분석**
각 AC(Acceptance Criteria)가 어떤 레이어에 영향을 주는지 식별:
```
AC-001: Presentation (API endpoint) + Logic (validation) + Data (DB query)
AC-002: Logic (calculation) only
AC-003: Presentation (UI component) + Logic (formatting)
```

**3b. 레이어별 설계**
- **Presentation**: 어떤 엔드포인트/컴포넌트가 필요한가? 요청/응답 형식은?
- **Logic**: 어떤 서비스/함수가 필요한가? 비즈니스 규칙은?
- **Data**: 어떤 쿼리/레포지토리가 필요한가? 스키마 변경이 필요한가?

**3c. 레이어 간 계약 설계**
- Presentation↔Logic 경계: DTO/Interface 정의
- Logic↔Data 경계: Repository 메서드 시그니처
- **절대 레이어를 건너뛰지 않는다** (Presentation → Data 직접 호출 금지)

**3d. 테스트 전략 (레이어별)**
- Logic 레이어: 순수 비즈니스 로직 단위 테스트 (mock은 레이어 경계에서만)
- Data 레이어: 통합 테스트 (실제 DB 연동)
- Presentation 레이어: E2E / API 테스트
- **구현과 테스트를 함께 작성** — 일괄 작성 금지

**3e. 기존 설계 확인**
- 데이터 모델이 시드의 ontology와 일치하는지 확인
- 엣지 케이스 처리 방법 결정
- seed spec에 `architecture` 섹션이 있다면 그 구조를 따른다

**Output**: Design decisions with layer mapping (inline)

### Phase 4: Deliver (구현)

실제 코드를 작성합니다:
- Design에서 결정한 대로 구현
- 각 AC(Acceptance Criteria)를 하나씩 충족
- 테스트 작성 (가능한 경우)
- 시드 스펙과의 drift를 최소화

**Rules during Deliver**:
1. 시드 스펙에 없는 기능을 추가하지 않는다
2. AC를 만족하지 않는 구현은 미완성이다
3. 각 AC 완료 시 체크 표시한다
4. **구현 순서**: Data → Logic → Presentation (의존성 방향 순)
5. **각 모듈 구현 직후 해당 테스트를 작성한다** — 일괄 작성 금지
6. **레이어 경계를 넘는 import가 발생하면 즉시 수정한다**

### Progress Tracking

각 Phase 전환 시 표시:
```
═══ Phase: Discover ═══════════════════════════
[탐색 중...]

═══ Phase: Define ═════════════════════════════
[정의 중...]

═══ Phase: Design ═════════════════════════════
[설계 중...]

═══ Phase: Deliver ════════════════════════════
[구현 중...]
AC-001: [x] completed
AC-002: [ ] in progress
AC-003: [ ] pending
```

### Completion

When all ACs are addressed:
```
Double Diamond complete.

Acceptance Criteria:
  AC-001: DONE
  AC-002: DONE
  AC-003: DONE

Files changed: {list}

Next: /evaluate to verify the implementation
```

### Drift Warning

If during implementation you realize the seed spec is wrong or incomplete:
```
DRIFT DETECTED
  Seed says: "{what the spec says}"
  Reality: "{what we found}"
  
Options:
  1. Adapt implementation to match spec
  2. Stop and create new seed version (/seed)
  3. Document deviation and continue
```

Prefer option 1. Only choose 2 if the spec is fundamentally wrong.
