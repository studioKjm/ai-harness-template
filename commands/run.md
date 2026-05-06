---
description: Execute seed spec via Double Diamond (Discover → Define → Design → Deliver). USE AFTER /decompose. Enforces D→L→P implementation order, writes tests immediately, runs gates continuously. Supports Pair Mode for medium/high complexity ACs.
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
4. **Determine Pair Mode** (아래 참조)

### Prerequisites
1. Seed spec must exist in `.harness/ouroboros/seeds/`
2. Read the latest seed spec before starting
3. If no seed exists, prompt user to run `/interview` then `/seed`
4. **TRD must exist** — check `docs/TRD.md`
   - Missing → **STOP**: "먼저 `/trd`를 실행하세요. 기술 설계 없이 구현하면 레이어 경계 위반이 발생합니다."
   - Exception: all ACs are `low` complexity AND single-layer change only
5. **Decomposed tasks must exist** — check `.harness/ouroboros/tasks/`
   - Missing → **STOP**: "먼저 `/decompose`를 실행하세요. 태스크 분해 없이 진행하면 메가 프롬프트와 롤백 불가 상태가 발생합니다."
   - Exception: same as above (all low + single-layer)

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
  └─ Main              → Phase 4: 구현 (직접 수행 또는 Pair Mode)
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

---

## Phase 4: Deliver — Mode Selection

Phase 3 완료 후, 각 AC의 `complexity` 필드를 확인하여 실행 모드를 결정한다.

### Pair Mode 판단 기준

seed spec의 각 AC에 `complexity` 필드가 있으면:

| complexity | Pair Mode | 이유 |
|-----------|-----------|------|
| `low` | **OFF** — 직접 구현 | 오버헤드 > 이점 |
| `medium` | **ON** — Navigator 플랜 요청 | 대안 비교의 가치가 있음 |
| `high` | **ON** — Navigator 필수 + Test Designer 필수 | 결함 방지가 중요 |

`complexity` 필드가 없는 AC는 **low로 간주**한다 (Direct 구현).

seed spec 전체에 complexity 필드가 하나도 없으면:
- AC 수 ≤ 3 → 전부 직접 구현 (Pair Mode OFF)
- AC 수 ≥ 4 → 사용자에게 Pair Mode 사용 여부를 묻는다

`HARNESS_ENABLE_PAIR_MODE=1` 환경변수가 설정된 경우:
- complexity 필드와 관계없이 **모든 AC에 Pair Mode 적용** (하위 호환)
- 단, 이 방식은 비권장. AC별 complexity 지정을 권장한다

### Pair Mode 진행 시 — 사용자에게 안내

```
═══ Pair Mode 활성화 ════════════════════════════
AC 중 medium/high complexity가 감지되었습니다.
Navigator-Driver 패턴으로 진행합니다.

Pair Mode AC: {목록}
Direct AC:    {목록}
```

---

## Phase 4a: Direct Deliver (기존 방식 — low complexity)

실제 코드를 작성합니다:
- Design에서 결정한 대로 구현
- 각 AC(Acceptance Criteria)를 하나씩 충족
- 테스트 작성 (가능한 경우)
- 시드 스펙과의 drift를 최소화

**Rules during Direct Deliver**:
1. 시드 스펙에 없는 기능을 추가하지 않는다
2. AC를 만족하지 않는 구현은 미완성이다
3. 각 AC 완료 시 체크 표시한다
4. **구현 순서**: Data → Logic → Presentation (의존성 방향 순)
5. **각 모듈 구현 직후 해당 테스트를 작성한다** — 일괄 작성 금지
6. **레이어 경계를 넘는 import가 발생하면 즉시 수정한다**

---

## Phase 4b: Pair Mode Deliver (medium/high complexity)

### Step 1: Navigator 스폰

**반드시 이 코드를 실행한다** — 건너뛰지 않는다:

```
Agent({
  description: "Navigator for Pair Mode",
  subagent_type: "navigator",
  run_in_background: true,
  prompt: `당신은 Pair Mode의 Navigator입니다.
이 프로젝트의 seed spec과 코드베이스를 파악한 뒤, Driver(나)의 메시지를 기다리세요.

Seed spec 위치: .harness/ouroboros/seeds/seed-v*.yaml
아키텍처 규칙: ARCHITECTURE_INVARIANTS.md

Driver가 AC를 보내면 플랜 3개를 생성하고 최적 플랜을 선택하여 응답하세요.
Driver가 구현 결과를 보내면 검토 후 Pass/Retry/Switch/Escalate로 응답하세요.

navigator.md 의 Behavior Rules를 정확히 따르세요.`
})
```

Navigator의 agent ID를 기록한다 (이후 SendMessage에 사용).

### Step 2: AC별 루프 — Pair Mode AC에 대해 반복

**complexity가 medium 또는 high인 AC 각각에 대해:**

#### 2a. Navigator에게 플랜 요청

```
SendMessage({
  to: "{navigator_agent_id}",
  message: `AC-{XXX}를 구현하려 합니다.

AC 내용: {AC description}
Priority: {must/should/nice}
Complexity: {medium/high}
현재 코드 상태: {관련 파일 목록과 주요 구조}
이전 실패 이력: {있으면 기록, 없으면 "없음"}

플랜 3개를 생성하고 최적 플랜을 선택해주세요.`
})
```

#### 2b. Navigator 응답 수신 → 플랜에 따라 구현

Navigator가 반환한 `Driver 지시사항`을 따라 구현한다:
1. 지시된 레이어 순서대로 코드 작성
2. 지시된 인터페이스/시그니처를 준수
3. 지시된 테스트 전략대로 테스트 작성

#### 2c. Navigator에게 결과 보고

```
SendMessage({
  to: "{navigator_agent_id}",
  message: `AC-{XXX} 구현 완료.

변경된 파일:
- {파일 경로}: {변경 내용 요약}

테스트 결과: {pass/fail}
발견된 이슈: {있으면 기록}

검토해주세요.`
})
```

#### 2d. Navigator 검토 결과에 따라 분기

- **PASS** → 다음 AC로 진행
- **RETRY** → Navigator의 수정 지시에 따라 코드 수정 → 2c로 돌아감
- **SWITCH** → Navigator가 제시한 새 플랜으로 재구현 → 2b로 돌아감
- **ESCALATE** → `/unstuck` 실행 또는 사용자에게 판단 요청
- **무응답/에러** → Navigator가 응답하지 않으면 해당 AC를 Direct 모드로 전환하고 사용자에게 알림

### Step 3: Test Designer 스폰 (high complexity AC가 1개 이상일 때)

**모든 Pair Mode AC 구현 완료 후**, Test Designer를 worktree 격리로 스폰한다:

```
Agent({
  description: "Independent test design",
  subagent_type: "test-designer",
  isolation: "worktree",
  prompt: `당신은 독립 Test Designer입니다.
아래 seed spec과 AC 목록을 기반으로 테스트를 설계하세요.
구현 코드(src/)를 읽지 마세요 — AC 스펙만으로 테스트를 작성합니다.

=== SEED SPEC ===
{seed spec 전문을 여기에 붙여넣기}

=== 테스트 프레임워크 ===
{jest/vitest/pytest 등}

=== 테스트 디렉토리 ===
tests/

test-designer.md의 규칙을 따르세요.`
})
```

Test Designer가 반환한 테스트 파일을 메인 브랜치에 병합한다.

### Step 4: AC 카운터 기반 자동 /review

**Pair Mode AC 3개를 완료할 때마다**, 다음을 실행한다:

```
═══ Auto-Review Checkpoint ══════════════════════
{N}개의 AC가 완료되었습니다. 드리프트 점검을 실행합니다.

체크리스트:
- [ ] 구현이 seed spec의 goal과 일치하는가?
- [ ] constraints의 must/must_not을 위반하지 않았는가?
- [ ] 레이어 경계를 넘는 import가 없는가?
- [ ] 온톨로지의 엔티티/액션 명명이 일관적인가?
- [ ] 추가된 기능이 seed spec의 scope.mvp 안에 있는가?
```

하나라도 위반이 발견되면 사용자에게 보고하고, 계속 진행할지 확인한다.

### Step 5: Navigator 세션 종료

모든 AC 완료 후:

```
SendMessage({
  to: "{navigator_agent_id}",
  message: "모든 AC 완료. 최종 세션 요약을 보내주세요."
})
```

Navigator의 세션 요약을 기록한다.

---

## Mixed Mode: Direct + Pair 혼합

한 seed spec 내에서 low/medium/high가 섞여 있을 때:

```
구현 순서:
1. low complexity AC를 먼저 Direct로 구현 (빠르게 기반 완성)
2. medium/high AC를 Pair Mode로 구현 (Navigator 플랜 기반)
3. Test Designer 스폰 (high가 있을 때)

이유: low AC가 기반 인프라(데이터 모델, 기본 API)를 제공하면,
medium/high AC에서 Navigator가 더 나은 플랜을 세울 수 있다.
```

---

## Progress Tracking

각 Phase 전환 시 표시:
```
═══ Phase: Discover ═══════════════════════════
[탐색 중...]

═══ Phase: Define ═════════════════════════════
[정의 중...]

═══ Phase: Design ═════════════════════════════
[설계 중...]

═══ Phase: Deliver (Mixed Mode) ═══════════════
[Direct] AC-001: [x] completed (low)
[Direct] AC-002: [x] completed (low)
[Pair]   AC-003: [x] completed (medium) — Plan B, 1회 시도
[Pair]   AC-004: [ ] in progress (high) — Plan A, 2회 시도 중
[Pair]   AC-005: [ ] pending (medium)
```

### Completion

When all ACs are addressed:
```
═══ Double Diamond Complete ═══════════════════

Acceptance Criteria:
  AC-001: DONE (direct)
  AC-002: DONE (direct)
  AC-003: DONE (pair, Plan B, 1 attempt)
  AC-004: DONE (pair, Plan A, 3 attempts)

Pair Mode Stats:
  Navigator 왕복: {총 횟수}
  플랜 전환: {횟수}
  Escalation: {횟수}
  Test Designer 테스트: {N}개

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
