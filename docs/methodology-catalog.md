# Methodology Catalog

> 5종 번들 메서드 한눈에 비교. 어떤 상황에 무엇을 쓸지 결정하는 게이트.

## TL;DR — 의사결정 흐름

```
프로젝트 시작 시점은?
├─ 0→1 (신규 프로젝트, 스펙 미확정) ───────► ouroboros (기본)
├─ 미지수가 막아서 스펙 작성 못 함 ──────► exploration (스파이크)
└─ 1→N (기존 시스템 확장)
   ├─ 기능 추가/스토리 분해 ──────────────► bmad-lite (+ ouroboros)
   ├─ 시드 진화 (스펙 변경) ──────────────► living-spec (+ ouroboros)
   └─ 호환 깨는 변경 (DB/API breaking) ───► parallel-change (+ ouroboros)
```

여러 메서드는 **조합 가능**. 예: `/methodology compose ouroboros bmad-lite living-spec`

## 한눈에 비교

| 메서드 | 적용 단계 | 기본 단위 | 추가 게이트 | 게이트 완화 | 페르소나 | 명령 수 |
|-------|---------|---------|-----------|-----------|---------|--------|
| **🐍 ouroboros** | 0→1 | seed (불변 명세) | (없음 — 핵심 게이트만) | 없음 | (간접) | 7 |
| **🔄 living-spec** | 1→N | seed-vN diff | 1 (warning) | 없음 | 없음 | 2 |
| **⫶ parallel-change** | 1→N | plan (state machine) | 2 (blocking) | 없음 | 없음 | 4 |
| **🎭 bmad-lite** | 0→1, 1→N | story | 1 (warning) | 없음 | 3 | 2 |
| **🔭 exploration** | 모든 단계 | spike + learning | 0 | 3 (paths) | 없음 | 2 |

## 메서드별 카드

### 🐍 ouroboros — Specification-First

> "프롬프팅을 멈추고, 명세부터 시작하라."

**언제**: 신규 프로젝트, 스펙이 아직 모호함, 명확한 AC가 필요할 때.

**무엇을 강제**: Ambiguity ≤ 0.2까지 인터뷰 반복. seed.yaml은 불변. 변경은 새 버전.

**산출물**:
- `seed-vN.yaml` (불변 명세)
- `interviews/`, `evaluations/`
- 태스크 분해는 별도 (`/decompose`)

**워크플로우**: `/interview → /seed → /decompose → /trd → /run → /evaluate → /evolve`

**조합 패턴**: 거의 항상 base. 다른 메서드는 ouroboros 위에 얹음.

---

### 🔄 living-spec — Spec Evolution

> "명세는 살아있다 — 변경의 의미를 추적하라."

**언제**: seed-v1이 이미 있고, 신규 요구로 v2가 필요할 때.

**무엇을 강제**:
- 두 시드 버전의 의미적 diff (entities/AC/architecture)
- 🔴 Breaking-change indicator
- 기존 태스크 분류 (unchanged / modified / deprecated / added)

**산출물**:
- `seeds/.diffs/v1-to-v2.md`
- `tasks/migration-plans/<id>.yaml`

**게이트**: `check-spec-drift.sh` (warning) — 코드가 현재 시드에 없는 엔티티 참조 시 경고

**조합 패턴**: `ouroboros + living-spec`. 시드 v2가 breaking이면 → `+ parallel-change` 자동 권고.

---

### ⫶ parallel-change — Expand · Migrate · Contract

> "호환 깨는 변경을 다운타임 0으로."

**언제**: DB 스키마/API 시그니처/함수 시그니처를 바꾸는데 caller가 여러 곳일 때.

**무엇을 강제**:
- 4-state 머신: expand → migrate → contract → done
- expand: old/new 공존 (둘 다 caller > 0)
- contract: old caller 0건 강제 (커밋 차단)
- 단계 건너뛰기 차단

**산출물**:
- `plans/pc-<id>.yaml` (state machine)

**게이트** (둘 다 blocking):
- `check-parallel-state.sh` — phase 일관성
- `check-parallel-callers.sh` — contract 단계 caller=0 강제

**조합 패턴**: 보통 `ouroboros + parallel-change`. living-spec가 breaking-change 감지하면 자동 제안 (v0.2).

---

### 🎭 bmad-lite — Persona-driven Story Decomposition

> "Same brain, different lens — 페르소나가 모호한 스펙을 차단."

**언제**: 시드 위에 신규 기능 추가, 스토리·AC를 명확히 잡아야 할 때.

**무엇을 강제**:
- narrative (As a / I want / so that) 형식
- Given/When/Then AC
- pm-strict가 weasel word("fast", "secure" 등) 차단

**산출물**:
- `stories/st-<id>.yaml`
- `epics/ep-<id>.yaml`

**페르소나 (3종)**:
- `analyst` — 도메인 엔티티/행위 매핑
- `ux-designer` — 플로우 + 상태 커버리지
- `pm-strict` — AC 품질 검증 (block 권한)

**게이트**: `check-story-format.sh` (warning) — placeholder/빈 AC/weasel words 경고

**BMAD와의 차이**: PRD/Architecture Doc 같은 무거운 문서 사이클 제거. 6 페르소나 → 3 페르소나. 1인~소규모용.

**조합 패턴**: `ouroboros + bmad-lite`. living-spec과 같이 쓰면 시드 진화 시 영향 받는 스토리 자동 추적.

---

### 🔭 exploration — Time-boxed Spikes

> "I don't know yet, and that's the question."

**언제**: 라이브러리/API/아키텍처 검증, 스토리가 기술 미지수에 막혔을 때.

**무엇을 강제**:
- question 필수 (물음표 끝)
- timebox 필수 (기본 4h)
- 4-state 머신: questioning → spiking → learned → applied
- promotion 의무 (ADR/seed/code 중 하나)

**산출물**:
- `spikes/sp-<id>/spike.yaml`
- `spikes/sp-<id>/sandbox/` ← **게이트 완화 영역**
- `learnings/ln-<id>.yaml`

**게이트 완화 (Relaxation)**:
- 활성 스파이크의 sandbox/는 `boundaries`, `spec`, `structure` 게이트 우회
- `secrets`, `security`는 절대 완화 안 함

**조합 패턴**: 모든 메서드와 조합 가능. 어느 단계든 막히면 spike 따고, 학습 끝나면 본 흐름으로 복귀.

## 조합 매트릭스

✅ = 권장 / 기본 워크플로우
⭕ = 가능 (서로 보완)
❌ = 충돌 / 중복

| | ouroboros | living-spec | parallel-change | bmad-lite | exploration |
|---|---|---|---|---|---|
| **ouroboros** | base | ✅ requires | ✅ requires | ✅ requires | ⭕ |
| **living-spec** | ✅ | base+ | ⭕ (breaking 시 자동 제안) | ⭕ | ⭕ |
| **parallel-change** | ✅ | ⭕ | base+ | ⭕ | ⭕ |
| **bmad-lite** | ✅ | ⭕ | ⭕ | base+ | ⭕ |
| **exploration** | ⭕ | ⭕ | ⭕ | ⭕ | base |

**전형적 조합**:
- 신규 프로젝트 단순: `ouroboros`
- 신규 + 스토리 분해: `ouroboros + bmad-lite`
- 외주 SaaS 확장: `ouroboros + bmad-lite + living-spec`
- 호환 깨는 마이그레이션: `ouroboros + parallel-change`
- 막혔을 때: 위 어느 조합 + `exploration` 추가

## 활성화 명령 (공통)

```bash
/methodology list                    # 사용 가능한 메서드 목록
/methodology current                 # 현재 활성 메서드
/methodology use <name>              # 단일 메서드 활성화
/methodology compose <name1> <name2> ...   # 다중 조합
/methodology deactivate <name>       # 비활성화
/methodology info <name>             # 메서드 상세 정보
```

## 어떤 메서드도 안 맞는 경우

- **단순 버그 수정**: 메서드 없이 그냥 코드 수정. 게이트는 그대로 작동.
- **6명 이상 팀의 풀 BMAD 필요**: BMAD 본가([github.com/bmadcode/BMAD-METHOD](https://github.com/bmadcode/BMAD-METHOD)) 사용
- **레거시 마이그레이션 (Strangler Fig)**: 현재 미지원. v0.2 후보.
- **DDD/Event Sourcing 같은 무거운 메타-아키텍처**: 별도 도입. 하네스는 메서드와 직교.

## 메서드 추가하기 (사용자 정의)

```bash
# 1. methodologies/<your-name>/manifest.yaml 작성
# 2. methodology/_registry.yaml 에 등록
# 3. /methodology list 로 확인
```

스키마: [methodology/_schema/manifest.yaml](../methodology/_schema/manifest.yaml)

## 버전 매트릭스 (v0.1)

| 메서드 | 버전 | 안정성 | 다음 |
|-------|------|-------|------|
| ouroboros | 1.0.0 | stable | (마이그레이션은 차후) |
| living-spec | 0.1.0 | beta | AST 기반 drift 감지 |
| parallel-change | 0.1.0 | beta | living-spec 자동 통합 |
| bmad-lite | 0.1.0 | beta | ux-designer 컴포넌트 스캔 |
| exploration | 0.1.0 | beta | gate consumer 자동화 |

자세한 진화 계획은 각 메서드의 README 참조.
