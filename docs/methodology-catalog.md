# Methodology Catalog

> 13종 번들 메서드 한눈에 비교. 어떤 상황에 무엇을 쓸지 결정하는 게이트.

## TL;DR — 의사결정 흐름

```
지금 뭐 하려는 중이세요?
│
├─ 🆕 0→1 (신규)
│   ├─ 단순 신규 ──────────────────────► ouroboros (기본)
│   ├─ 스토리·AC 정리 필요 ────────────► ouroboros + bmad-lite
│   ├─ 가설 먼저 검증하고 싶음 ─────────► lean-mvp (단독 또는 추가)
│   └─ 큰 아키텍처 결정 ─────────────► ouroboros + bmad-lite + rfc-driven
│
├─ 🔧 1→N (기존 확장)
│   ├─ 기능 추가 (시드 진화) ──────────► ouroboros + living-spec [+ bmad-lite]
│   ├─ 함수 시그니처 변경 ─────────────► + parallel-change
│   ├─ 모듈/시스템 교체 ──────────────► + strangler-fig
│   ├─ 복잡한 리팩터링 (의존성 불명확) ──► + mikado-method
│   └─ 클라이언트 레거시 인수 ─────────► strangler-fig (단독 가능)
│
├─ ❓ 미지수
│   ├─ 라이브러리 검증 / PoC ──────────► exploration (어느 조합에든 추가)
│   └─ 기능 효과 검증 ────────────────► lean-mvp (가설 기반 측정)
│
├─ 🧪 품질
│   └─ 테스트 우선 엄격 강제 ──────────► tdd-strict (blocking gate)
│
├─ 🛡 운영·신뢰성
│   ├─ 결제·인증·민감 정보 다룸 ──────► + threat-model-lite
│   ├─ 메트릭·SLO 설계 필요 ──────────► + observability-first
│   └─ 장애 발생 ────────────────────► + incident-review
│
└─ 🐛 단순 버그 수정 ─────────────────► (메서드 불필요, 게이트만 작동)
```

여러 메서드는 **조합 가능**. 예: `/methodology compose ouroboros bmad-lite living-spec threat-model-lite observability-first`

## 한눈에 비교 (13종)

| 메서드 | 적용 단계 | 기본 단위 | 추가 게이트 | 게이트 완화 | 페르소나 | 명령 수 |
|-------|---------|---------|-----------|-----------|---------|--------|
| **🐍 ouroboros** | 0→1 | seed (불변 명세) | (없음 — 핵심 게이트만) | 없음 | (간접) | 7 |
| **🔄 living-spec** | 1→N | seed-vN diff | 1 (warning) | 없음 | 없음 | 2 |
| **⫶ parallel-change** | 1→N | plan (4-state) | 2 (blocking) | 없음 | 없음 | 4 |
| **🎭 bmad-lite** | 0→1, 1→N | story | 1 (warning) | 없음 | 3 | 2 |
| **🔭 exploration** | 모든 단계 | spike + learning | 0 | 3 (paths) | 없음 | 2 |
| **🌿 strangler-fig** | 1→N | plan (4-state) | 1 (warning) | 없음 | 없음 | 3 |
| **🚨 incident-review** | 운영 | incident (5-state) | 1 (warning) | 없음 | 없음 | 3 |
| **🛡 threat-model-lite** | 모든 단계 | model (4-state) | 1 (warning) | 없음 | 1 | 2 |
| **📊 observability-first** | 0→1, 1→N | spec + SLO | 1 (warning) | 없음 | 없음 | 2 |
| **📜 rfc-driven** | 모든 단계 | rfc (5-state) | 1 (warning/blocking) | 없음 | 없음 | 2 |
| **🔴 tdd-strict** | 모든 단계 | cycle (4-state) | 1 (blocking) | 없음 | 없음 | 2 |
| **🧪 lean-mvp** | 0→1, 1→N | hypothesis (4-state) | 0 | 없음 | 없음 | 1 |
| **🎋 mikado-method** | 1→N | graph + nodes | 0 | 없음 | 없음 | 1 |

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

---

### 🌿 strangler-fig — Module-level Legacy Migration

> "facade로 감싸 점진적으로 교체. 다운타임 0."

**언제**: 클라이언트 레거시 인수, 모듈/서비스 단위 점진 교체. 전체 재작성 불가.

**parallel-change와 차이**: parallel-change는 **함수·시그니처 수준**. strangler-fig는 **모듈·시스템 수준** + 라우팅 facade.

**무엇을 강제**:
- 4-state 머신: legacy-only → coexist → new-primary → retired
- cutover criteria 자동 검증:
  - coexist: facade + new module 존재 + ≥1 routing rule
  - new-primary: ≥80% rules → target new
  - retired: 모든 rules → new + coverage 100%

**산출물**:
- `plans/sf-<id>.yaml` (legacy/new/facade 경로, routing rules, coverage)

**게이트**: `check-strangler-coverage.sh` (warning) — 라우팅 안 된 endpoint, 90일+ stagnation 경고

**조합 패턴**: `ouroboros + strangler-fig` (신규 모듈 설계는 시드 기반). `+ parallel-change` (모듈 안의 함수 시그니처 변경).

---

### 🚨 incident-review — Blameless Postmortem

> "What system allowed this?"

**언제**: production 장애, 배포 후 회귀, 보안 사고. Slack에서 끝나지 않게.

**exploration과 차이**: exploration은 **선험적** (모르는 걸 알고 시작). incident-review는 **사후적** (예상 못한 문제).

**무엇을 강제**:
- 5-state: recording → analyzing → published → acted-on → archived
- publish 전: blameless review + five_whys.root_cause 강제
- close 전: 모든 action items resolved (open/in-progress 0건)
- action items: owner + due_date + priority 필수

**산출물**:
- `incidents/inc-<id>.yaml` (timeline, 5-whys, contributing factors, action items)

**게이트**: `check-incident-actions.sh` (warning) — overdue action items, owner 미지정, published with 0 actions

**특별 명령**: `/incident-patterns` — 분기별 recurring root causes 집계

**조합 패턴**: 어느 조합에든 추가. action item이 task/story/spike/ADR/parallel-change/strangler-fig으로 변환 가능.

---

### 🛡 threat-model-lite — STRIDE Threat Modeling

> "Assume the attacker has read your spec."

**언제**: 결제·인증·PII 다루는 스토리. 사후 보안 패치 대신 설계 단계 차단.

**core gates와 차이**: core의 `check-secrets.sh`/`check-security.sh`는 **이미 코드에 들어간 것** 검증 (사후). threat-model은 **스토리 작성 시점** 위협 식별 (사전).

**무엇을 강제**:
- 4-state: draft → reviewed → approved → applied
- review 전: STRIDE 6 카테고리 모두 위협 OR `not_applicable_reason` 필수
- apply 전: 모든 mitigation `implemented`/`deferred`/`accepted`
- override 시 reason + history 기록

**산출물**:
- `models/tm-<id>.yaml` (STRIDE × threats × mitigations)
- `triggers.yaml` — 자동 요구 패턴 (auth/payment/pii 등)

**페르소나**: `security-reviewer` — weasel words("HTTPS 쓰니까 안전") 차단

**게이트**: `check-threat-coverage.sh` (warning) — sensitive 파일·스토리에 모델 미연결

**조합 패턴**: `+ bmad-lite` (story narrative에 sensitive 키워드 → 자동 경고). `+ ouroboros` (위협 매트릭스가 시드 AC 정당화).

---

### 📊 observability-first — Metrics, Logs, Traces, SLOs

> "Telemetry is a design output, not a retrofit."

**언제**: MVP에서 자주 스킵되는 영역. 메트릭·SLO를 스토리 작성 시점에 설계.

**무엇을 강제**:
- spec 5-state: draft → defined → instrumented → measuring → review-due
- SLO 3-state: proposed → active → retired
- instrument 전: coverage.files/symbols 필수
- 메트릭은 `--question` 필수 (어떤 질문에 답하는가)
- log field에 PII 마킹

**산출물**:
- `specs/obs-<id>.yaml` (metrics + logs + traces + SLO 링크)
- `slos/slo-<id>.yaml` (SLI + target + burn rate alert + 위반 기록)

**게이트**: `check-observability-coverage.sh` (warning) — Logic 레이어 파일 중 spec 없는 것, 90일+ 미검토 spec

**SLO target 가이드**: 99% (내부) / 99.5% (일반 API) / 99.9% (핵심) / 99.99% (결제·인증). **100% 금지**.

**조합 패턴**: `+ ouroboros` (SLO target = 시드 AC). `+ incident-review` (위반 기록이 incident 연결).

---

### 📜 rfc-driven — Design Review Before Code

> "큰 변경은 페이퍼 트레일."

**언제**: 아키텍처 리팩터, 새 의존성, breaking migration. 합의 없는 진행 위험.

**ADR과의 차이**: ADR은 **결정 후** (사실 기록). RFC는 **결정 전** (협의 + 대안 검토).

**무엇을 강제**:
- 5-state: draft → proposed → accepted/rejected → superseded
- propose 전: summary/motivation/design + ≥2 alternatives + ≥1 drawback 필수
- accept/reject: `--decided-by` + `--rationale` 필수
- supersede: 양방향 자동 링크

**산출물**:
- `rfcs/rfc-<id>.yaml` (motivation, design, alternatives, drawbacks, decision)
- `.rfc-links.yaml` — 파일/모듈 → RFC 매핑 (게이트 소비)
- `config.yaml` — LOC 임계값 (per_file 500 / total 1000), 필수/면제 경로

**게이트**: `check-rfc-required.sh` (warning, config로 blocking 가능) — 큰 변경에 RFC 링크 없으면 경고

**조합 패턴**: `+ ouroboros` (accepted RFC가 시드 input). `+ parallel-change`/`+ strangler-fig` (마이그레이션 RFC가 plan 생성). `+ incident-review` (incident가 motivation evidence).

---

### 🔴 tdd-strict

**언제**: 테스트 우선 원칙을 "규칙"이 아닌 게이트로 강제하고 싶을 때. 팀/AI가 자주 소스 먼저 짜는 패턴 반복 시.

**핵심**: `check-test-first.sh` (blocking gate) — 스테이지된 소스 파일의 대응 테스트가 git 히스토리에 먼저 존재하지 않으면 커밋 차단.

**무엇을 강제**:
- 4-state cycle: red → green → refactor → done
- 소스 파일은 테스트보다 나중에 커밋되어야 함
- `[refactor]`/`[chore]`/`[docs]`/`[ci]` prefix로 면제
- 테스트 페어링 컨벤션 설정 가능 (tdd-config.yaml)

**산출물**:
- `.harness/tdd-strict/cycles/tdd-YYYYMMDD-NNN.yaml` — 사이클별 상태
- `.harness/tdd-strict/config.yaml` — 페어링 컨벤션, 면제 경로

**게이트**: `check-test-first.sh` (blocking) — 소스 파일이 테스트 파일보다 git 히스토리에 먼저 등장하면 커밋 차단

**조합 패턴**: `+ ouroboros` (시드 AC → TDD 사이클 1:1 매핑). `+ lean-mvp` (가설 검증 구현에 TDD 강제). `+ mikado-method` (리팩터링 나뭇잎 노드에 TDD 적용).

---

### 🧪 lean-mvp

**언제**: 기능을 풀로 구현하기 전 가설을 세우고 최소 MVP로 검증하고 싶을 때. "이게 실제로 효과 있을까?" 물음이 먼저인 상황.

**핵심**: Build → Measure → Learn. 하나의 지표(metric)로 판단. 결정은 persist / pivot / abandon 셋 중 하나.

**무엇을 강제**:
- 4-state: proposed → testing → measuring → decided
- build 전: metric 이름 + 목표값 필수 (require_metric_before_build: true)
- pivot/abandon: rationale 필수
- measurement_window로 시간 제한

**산출물**:
- `.harness/lean-mvp/hypotheses/hyp-YYYYMMDD-NNN.yaml` — 가설별 상태 + 데이터
- `.harness/lean-mvp/config.yaml` — 기본 측정 기간, 동시 가설 수 제한

**게이트**: 없음 (가설 실험이므로 blocking 아님)

**조합 패턴**: `+ ouroboros` (가설 → 시드 스펙 → 구현). `+ tdd-strict` (MVP 구현 시 TDD). `+ observability-first` (SLO를 가설 metric으로 연결). `+ rfc-driven` (대형 실험은 RFC 선행).

---

### 🎋 mikado-method

**언제**: 복잡한 리팩터링에서 어디서부터 손댈지 모를 때. 변경 시도 → 컴파일 오류/테스트 실패 → 원인이 다른 곳에 있는 패턴 반복 시.

**핵심**: Goal을 Try → 막히면 Revert + 전제조건 기록 → 나뭇잎(prereq 없는 노드)부터 해결. 코드베이스는 항상 그린 상태 유지.

**무엇을 강제**:
- per-node 상태: pending → attempted → blocked/done ← reverted
- done: 모든 prerequisites가 done이어야 가능
- revert 후 pending 상태에서도 미완료 prereq 있으면 try 차단

**산출물**:
- `.harness/mikado-method/graphs/mik-YYYYMMDD-NNN.yaml` — 트리 전체 상태
- `/mikado tree` — ASCII 트리 시각화 (완료/차단/진행 현황)

**게이트**: 없음 (리팩터링 자체가 이미 안전 메커니즘)

**조합 패턴**: `+ parallel-change` (나뭇잎 노드를 parallel-change로 안전 구현). `+ strangler-fig` (모듈 교체 진행도를 mikado 트리로 추적). `+ tdd-strict` (각 나뭇잎 노드 구현에 TDD 적용). `+ ouroboros` (리팩터링 목표를 시드 스펙으로 결정화 후 mikado).

## 조합 매트릭스

✅ = 권장 / 기본 워크플로우
⭕ = 가능 (서로 보완)
❌ = 충돌 / 중복

|  | ouro | living | p-change | bmad | explore | strangler | incident | threat | observe | rfc | tdd | lean | mikado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **ouroboros** | base | ✅ | ✅ | ✅ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ |
| **living-spec** | ✅ | base | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ |
| **parallel-change** | ✅ | ⭕ | base | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ✅ | ⭕ | ✅ |
| **bmad-lite** | ✅ | ⭕ | ⭕ | base | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ |
| **exploration** | ⭕ | ⭕ | ⭕ | ⭕ | base | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ |
| **strangler-fig** | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | base | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ✅ |
| **incident-review** | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | base | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ |
| **threat-model-lite** | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | base | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ |
| **observability-first** | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | base | ⭕ | ⭕ | ✅ | ⭕ |
| **rfc-driven** | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | base | ⭕ | ⭕ | ⭕ |
| **tdd-strict** | ⭕ | ⭕ | ✅ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | base | ✅ | ✅ |
| **lean-mvp** | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ⭕ | ✅ | ⭕ | ✅ | base | ⭕ |
| **mikado-method** | ⭕ | ⭕ | ✅ | ⭕ | ⭕ | ✅ | ⭕ | ⭕ | ⭕ | ⭕ | ✅ | ⭕ | base |

→ **충돌 없음**. 13종 모두 동시 활성화 가능 (실용적이진 않지만 가능).

**전형적 조합**:

| 시나리오 | 조합 |
|---------|-----|
| 사이드 프로젝트 (실험) | `ouroboros` 또는 `exploration` 단독 |
| 신규 외주 SaaS MVP | `ouroboros + bmad-lite` |
| 외주 SaaS 보안 강화 | `+ threat-model-lite + observability-first` |
| 외주 SaaS 유지보수 | `ouroboros + bmad-lite + living-spec + incident-review` |
| 레거시 인수 + 점진 개편 | `strangler-fig + parallel-change [+ ouroboros]` |
| 큰 아키텍처 결정 | `+ rfc-driven` |
| 막혔을 때 | 어느 조합 + `exploration` 추가 |
| 풀 SaaS 운영 (모든 안전망) | `ouroboros + bmad-lite + living-spec + threat-model-lite + observability-first + incident-review + rfc-driven` |

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

## 버전 매트릭스

| 메서드 | 버전 | 안정성 | 다음 (v0.2 후보) |
|-------|------|-------|------|
| ouroboros | 1.0.0 | stable | (Phase 1 마이그레이션 cleanup) |
| living-spec | 0.1.0 | beta | AST 기반 drift 감지 |
| parallel-change | 0.1.0 | beta | living-spec 자동 통합 |
| bmad-lite | 0.1.0 | beta | ux-designer 컴포넌트 스캔 |
| exploration | 0.1.0 | beta | gate consumer 자동화 |
| strangler-fig | 0.1.0 | beta | APM 연동 (legacy traffic 0건 자동 검증) |
| incident-review | 0.1.0 | beta | 외부 모니터링 timeline 자동 수집 |
| threat-model-lite | 0.1.0 | beta | DREAD 점수, OWASP Top 10 자동 매핑 |
| observability-first | 0.1.0 | beta | Datadog/Prometheus 자동 sync |
| rfc-driven | 0.1.0 | beta | Slack/GitHub 리뷰어 알림 |

자세한 진화 계획은 각 메서드의 README 참조.
