# AI Harness Engineering Template

> 한국어 · [English](./README.en.md)

AI 에이전트가 자율적으로 일하되, 안전하게 통제할 수 있는 환경을 만드는 템플릿.
**Harness(구조적 가드레일) + Ouroboros(명세 기반 개발) + 3-Tier Architecture(클린 아키텍처)**를 통합.

> "프롬프트는 부탁이고, 하네스는 강제다."
> "프롬프팅을 멈추고, 명세부터 시작하라."

---

## 목차

- [시스템 전체 구조](#시스템-전체-구조)
- [Quick Start](#quick-start)
- [하네스 6가지 구성요소](#하네스-6가지-구성요소)
- [Ouroboros 워크플로우](#ouroboros-워크플로우)
- [11개 게이트](#11개-게이트)
- [3-Tier Layered Architecture](#3-tier-layered-architecture)
- [9개 에이전트 페르소나 + Orchestration](#9개-에이전트-페르소나)
- [Lite vs Pro 비교](#lite-vs-pro)
- [Pro 버전 상세](#pro-버전-상세)
- [설치 상세](#설치-상세)
- [디렉토리 구조](#디렉토리-구조)
- [데이터 흐름](#데이터-흐름)
- [Examples](#examples)
- [Acknowledgments](#acknowledgments--inspirations)

---

## 시스템 전체 구조

```
┌───────────────────────────────────────────────────────────────────┐
│  OUROBOROS (명세 기반 개발 루프)                                    │
│  /interview → /seed → /trd → /decompose → /run → /evaluate       │
│       ↑                                                │          │
│       └──────── /evolve (수렴까지 반복) ────────────────┘          │
└───────────────────────────────────────────────────────────────────┘
                          ↕ (강제됨)
┌───────────────────────────────────────────────────────────────────┐
│  HARNESS GATES (11개 구조적 가드레일)                               │
│  boundaries | layers | secrets | security | structure | spec       │
│  | complexity | deps | mutation | performance | ai-antipatterns    │
└───────────────────────────────────────────────────────────────────┘
                          ↕ (학습됨)
┌───────────────────────────────────────────────────────────────────┐
│  FEEDBACK LOOP (자기 강화)                                         │
│  위반 감지 → 분류 → 규칙 추가 → 게이트 반영 → 시스템 강건화          │
└───────────────────────────────────────────────────────────────────┘
```

### 핵심 원칙

| 원칙 | 설명 |
|------|------|
| 명세가 먼저 | 코딩 전에 인터뷰 → 시드 스펙 확정 |
| 구조적 강제 | 규칙은 가이드라인이 아닌 게이트(차단)로 강제 |
| 불변 명세 | 시드 스펙은 수정 불가, 변경은 새 버전 생성 |
| 자기 강화 | 위반 → 규칙 진화 → 시스템이 점점 강건해짐 |
| 3-tier 아키텍처 | Presentation / Logic / Data 레이어 분리 필수 |
| 점진적 채택 | 전부 쓸 필요 없이 개별 컴포넌트 선택 가능 |

---

## Quick Start

### 옵션 A: Claude Code 플러그인 (가장 간단)

```
/plugin marketplace add studioKjm/ai-harness-template
/plugin install harness@studioKjm-harness
```

커맨드/에이전트만 설치됩니다. 게이트·훅·템플릿까지 원하면 옵션 B 사용.

### 옵션 B: 풀 설치 (권장)

```bash
# === Lite (bash only, zero dependencies) ===
git clone https://github.com/studioKjm/ai-harness-template.git
./ai-harness-template/init.sh /path/to/your-project

# === Pro (Python-enhanced) ===
./ai-harness-template/pro/install.sh /path/to/your-project

# === Pro + MCP Server ===
pip install ai-harness-pro[mcp]
harness mcp-serve  # AI 에이전트에서 게이트를 MCP 도구로 호출
```

---

## 하네스 6가지 구성요소

| # | 구성요소 | 설명 | 구현물 |
|---|---------|------|--------|
| 1 | **규칙 전달** (CLAUDE.md) | AI가 읽는 컨텍스트 파일 | `CLAUDE.md.hbs`, `ARCHITECTURE_INVARIANTS.md.hbs`, `code-convention.yaml` |
| 2 | **위험 차단** (Permissions) | AI 접근 범위 제한 | `boundaries/presets/` (strict/standard/permissive) |
| 3 | **자동 검증** (Hooks) | 편집/커밋 시 자동 실행 | `pre-commit-gate.sh`, `post-edit-lint.sh`, Pro hooks |
| 4 | **테스트 도구** (MCP) | 외부 에이전트에서 게이트 호출 | `mcp/server.py` — 11개 게이트 + 시드/인터뷰/감사 도구 |
| 5 | **AI 분리** (Subagent) | 작업별 에이전트 위임 | `/seed`, `/run`, `/evaluate`, `/evolve`에 명시적 subagent 패턴 |
| 6 | **진화 원칙** (메타 원칙) | 실패 → 규칙 추가 → 진화 | `evolve-rules.md`, `/evolve` 커맨드, 수렴 판정 |

---

## Ouroboros 워크플로우

```
/interview    →    /seed    →    /trd     →   /decompose  →    /run    →    /evaluate    →    /evolve
 (명세 확정)    (스펙 생성)    (기술 설계)    (태스크 분해)     (구현)      (검증)           (진화)
      ↑                                                                                      │
      └────────────────────────── ontology 수렴까지 반복 ─────────────────────────────────────┘
```

### 10개 커맨드

| Command | Description | Agent | Subagent |
|---------|-------------|-------|----------|
| `/interview` | 소크라테스 인터뷰 (숨겨진 가정 발견) | Interviewer | - |
| `/seed` | 불변 시드 스펙 생성 | Seed Architect | Ontologist (도메인 추출) |
| `/trd` | 3-tier 기반 기술 설계서 (논의 먼저 → 설계) | Executor | - |
| `/decompose` | 원자적 태스크 분해 + 레이어별 검증 | Decomposer | - |
| `/run` | Double Diamond 실행 (D→L→P 순서) | Executor | Explore (병렬 탐색) |
| `/evaluate` | 3단계 검증 (Mechanical→Semantic→Judgment) | Evaluator | Gate Runner (기계적 검증) |
| `/evolve` | 진화 루프 (수렴까지) | Evolver | Contrarian+Simplifier+Researcher (병렬 분석) |
| `/rollback` | Saga 패턴 롤백 (stash/checkout/branch) | Rollback Guardian | - |
| `/unstuck` | 막혔을 때 5 에이전트 다각도 돌파 | 5 Agents | - |
| `/pm` | PRD 자동 생성 | PM | - |

### /interview — 소크라테스식 인터뷰

4개 차원 추적으로 모호성을 수치화:

| 차원 | 비중 | 목표 질문 |
|------|------|----------|
| Goal Clarity | 40% | 무엇을 만들고 싶은가? 누구를 위한 것인가? |
| Constraint Clarity | 30% | 절대 하면 안 되는 것은? 기술 스택 제약은? |
| Success Criteria | 30% | 완료를 어떻게 판단하나? 엣지 케이스는? |
| Context Clarity | 15% | 기존 코드 구조는? 영향 범위는? (brownfield만) |

> Greenfield: G(40%) + C(30%) + S(30%) = 100%.
> Brownfield: G(35%) + C(25%) + S(25%) + X(15%) = 100% (자동 재조정).

**게이트**: `ambiguity = 1.0 - Σ(clarity_i × weight_i)` ≤ 0.2 이어야 `/seed` 진행 가능

### /seed — 불변 명세

시드 스펙 구조:
```yaml
version: 1
goal: { summary, detail, non_goals }
constraints: { must, must_not, should }
acceptance_criteria: [{ id, description, verification, priority }]
ontology:
  entities: [{ name, fields, relationships }]
  actions: [{ name, actor, input, output, side_effects }]
architecture:
  pattern: "3-tier-layered"
  layers: { presentation, logic, data }
  layer_communication: { presentation_to_logic, logic_to_data, data_format }
scope: { mvp, future }
tech_decisions: [{ decision, reason, alternatives }]
```

**불변 원칙**: seed-v1.yaml 생성 후 수정 불가. 변경은 seed-v2.yaml로.

### /trd — 기술 설계서

바로 설계서를 작성하지 않는다. **논의 먼저**:

```
Phase 1: 탐색 (문서/코드 파악) → Phase 2: 큰 그림 (P/L/D별)
→ Phase 3: 논의점 (resource/impact 설명) → Phase 4: 최종 설계서
→ Phase 5: 레이어별 테스트 설계
```

### /decompose — 원자적 태스크 분해

각 AC를 레이어 단위로 분해하고 의존성 순서를 결정:
```
AC-001: "사용자가 검색하면 매물을 보여준다"
  → T-001 [Data]: 검색 쿼리 레포지토리 + 테스트
  → T-002 [Logic]: 필터링 서비스 + 테스트
  → T-003 [Present]: 검색 API 엔드포인트 + 테스트
```

### /run — Double Diamond (레이어 기반)

| Phase | 활동 |
|-------|------|
| Discover | 시드 재확인, 코드베이스 탐색 (subagent 병렬) |
| Define | 범위 확정, 구현 순서, 테스트 전략 |
| **Design** | **레이어 영향 분석 → 레이어별 설계 → DTO 계약 → 테스트 전략** |
| **Deliver** | **Data → Logic → Presentation 순서, 모듈마다 즉시 테스트** |

### /evaluate — 3단계 검증

```
Stage 1 Mechanical: 게이트 + lint + build + tests
Stage 2 Semantic:   AC 준수 + 목표 정합 + 레이어 컴플라이언스 + 온톨로지 드리프트
Stage 3 Judgment:   코드 품질 + 엣지 케이스 (선택적)
```

### /evolve — 진화 루프

`Wonder → Reflect → Re-seed`. 수렴 판정: 온톨로지 유사도 ≥ 0.95 → 완료.

---

## 11개 게이트

### 차단 게이트 (위반 시 커밋/CI 차단)

| 게이트 | 검사 대상 |
|--------|----------|
| `check-boundaries.sh` | `boundaries.yaml` 기반 금지 import 패턴 |
| `check-layers.sh` | 3-tier 레이어 분리 (P→D 스킵, L→P 역참조) |
| `check-secrets.sh` | 35+ 시크릿 패턴 (AWS, GitHub, Stripe, JWT, Firebase 등) |
| `check-security.sh` | SAST 정적 보안 분석 (Semgrep/Bandit + 11개 내장 패턴) |
| `check-structure.sh` | 파일 배치 규칙 (.env, SQL migrations) |
| `check-spec.sh` | 시드 스펙 필수 필드 완성도 |
| `check-deps.sh` | npm/pip/go/cargo audit 의존성 취약점 |
| `check-mutation.sh` | 뮤테이션 테스트 점수 (mutmut/Stryker) |

### 경고 게이트 (차단하지 않음, 리뷰 권장)

| 게이트 | 검사 대상 |
|--------|----------|
| `check-complexity.sh` | 함수 길이(80L), 파라미터(5개), 파일 길이(500L), 중첩(5단계) |
| `check-performance.sh` | 파일 크기, 의존성 수, 빌드 출력, import 깊이 |
| `check-ai-antipatterns.sh` | 환각 API, 과잉 추상화, 네이밍 드리프트, 미사용 import |

### 실행 시점

```
git commit  → pre-commit hook → 자동 실행
CI push/PR  → .github/workflows/harness-gates.yaml
수동        → .harness/detect-violations.sh
MCP         → harness mcp-serve (외부 에이전트에서 호출)
```

---

## 3-Tier Layered Architecture

### 레이어 정의

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Presentation    │────→│     Logic        │────→│      Data        │
│  (사용자 소통)    │     │  (비즈니스 규칙)   │     │  (데이터 소통)    │
├──────────────────┤     ├──────────────────┤     ├──────────────────┤
│ UI, HTTP 경계     │     │ 알고리즘, 검증    │     │ DB 조작          │
│ 입력 검증         │     │ 트랜잭션 관리     │     │ 외부 API 호출    │
│ 응답 포맷팅       │     │ 서비스 조율       │     │ 캐싱             │
└──────────────────┘     └──────────────────┘     └──────────────────┘

  ✅ Presentation → Logic → Data (순방향만 허용)
  ❌ Presentation → Data (레이어 스킵 금지)
  ❌ Logic → Presentation (역참조 금지)
  ❌ Data → Logic (역참조 금지)
```

### 스택별 매핑

| Layer | Next.js | NestJS | FastAPI | Django |
|-------|---------|--------|---------|--------|
| **Presentation** | pages, Components | Controllers, DTOs | Routes, Pydantic | Views, Templates |
| **Logic** | services, Server Actions | Services, Domain | Services | Models/Managers |
| **Data** | Prisma Client, repos | TypeORM, Repositories | SQLAlchemy, repos | Django ORM |

### 레이어별 테스트

| Layer | 테스트 유형 | 원칙 |
|-------|-----------|------|
| **Logic** | 단위 테스트 | 순수 비즈니스 로직, mock은 경계에서만 |
| **Data** | 통합 테스트 | 실제 DB/외부 서비스 |
| **Presentation** | E2E/API | UI 렌더링, 라우팅 |

**핵심**: 구현과 테스트를 함께 작성. 일괄 작성 금지. mock으로 접착제 코드를 테스트하지 않는다.

---

## 9개 에이전트 페르소나

### 코어 (4개)

| Agent | Role | When |
|-------|------|------|
| **Interviewer** | 질문만 한다 (답 금지) | `/interview` |
| **Ontologist** | 도메인 모델 추출 | `/seed` (subagent) |
| **Seed Architect** | 스펙 결정화 | `/seed` |
| **Evaluator** | 3단계 검증 | `/evaluate` |

### 확장 (5개)

| Agent | Perspective | When |
|-------|------------|------|
| **Contrarian** | "만약 반대라면?" | `/unstuck`, `/evolve` |
| **Simplifier** | "제거할 건 없나?" | `/unstuck`, `/evolve` |
| **Researcher** | "증거는?" | `/unstuck`, `/evolve` |
| **Architect** | "구조가 원인인가?" | `/unstuck` |
| **Hacker** | "우회로는?" | `/unstuck` |

### Orchestration Topology (`agents/topology.yaml`)

| 패턴 | 설명 | 사용 |
|------|------|------|
| **Pipeline** | 순차 실행 (출력→입력) | `/interview` → `/seed` |
| **Fan-out** | 병렬 실행 + 결과 병합 | `/evolve` (3 subagent 동시) |
| **Expert Pool** | 전문가 풀 전원 투입 | `/unstuck` (5 관점) |
| **Producer-Reviewer** | 생산-검증 분리 | `/run` → `/evaluate` |

---

## Lite vs Pro

### 어느 쪽을 써야 하나?

**Lite로 시작하라.** Lite만으로도 가치의 80%를 얻는다.

**Pro로 업그레이드해야 할 시점** — 아래 중 2개 이상 해당:
- 팀이 3명 이상이고 협업 세션이 길어진다
- 프로젝트가 3개월 이상 지속될 예정이다
- 게이트 실행 내역과 감사 로그를 추적해야 한다
- 다른 AI 도구(Cursor, Cline 등)에서도 같은 게이트를 쓰고 싶다 (MCP)
- CI에서 객관적 점수(ambiguity, drift)를 수치로 남겨야 한다

**Pro가 과할 때** — Lite로 충분:
- 솔로 개발
- 프로토타입/해커톤
- 한 달 이내 단기 프로젝트
- 게이트 + 커맨드 + 에이전트만 필요

### 기능 비교

| | **Lite** | **Pro** |
|---|---|---|
| 의존성 | bash only (제로 의존성) | Python 3.11+ |
| 설치 | `./init.sh` | `./pro/install.sh` |
| 11개 게이트 | O | O |
| 10개 슬래시 커맨드 | O (AI 기반) | O (AI + 엔진) |
| 9 에이전트 페르소나 | O | O |
| 실제 모호성 점수 계산 | - | O |
| 온톨로지 유사도 추적 | - | O |
| 3단계 자동 평가 | - | O |
| 세션 영속성 (SQLite) | - | O |
| 드리프트 모니터링 훅 | - | O |
| 테스트 스캐폴드 생성 | - | O |
| 감사 로그 | - | O |
| Agent Observability | - | O |
| MCP 서버 | - | O |
| CLI (`harness` 커맨드) | - | O |

---

## Pro 버전 상세

### 아키텍처

```
pro/src/harness_pro/
├── cli.py                  # Typer CLI (10개 커맨드)
├── interview/engine.py     # 인터뷰 + 명확도 자동 점수화
├── scoring/ambiguity.py    # 모호성 가중 수식 계산
├── ontology/extractor.py   # 엔티티/관계/액션 추출 + 유사도
├── evaluation/pipeline.py  # 3단계 자동 평가 + 감사 로그
├── persistence/store.py    # SQLite EventStore (sessions, events, audit_log)
├── drift/monitor.py        # 시드 대비 드리프트 측정
├── testing/scaffold.py     # AC → 테스트 스캐폴드 생성
├── observability/tracer.py # Agent 의사결정 트레이싱
└── mcp/server.py           # MCP 서버 (게이트를 도구로 노출)
```

### CLI 커맨드

```bash
harness interview "topic"         # 인터뷰 시작, 모호성 점수 반환
harness seed                      # 최신 인터뷰 → 시드 생성
harness score                     # 현재 모호성 점수 표시
harness evaluate                  # 3단계 검증 실행
harness drift <file>              # 시드 대비 드리프트 측정
harness status                    # 세션 상태 표시
harness audit [--summary]         # 감사 로그 조회
harness trace [--recent N]        # Agent observability 트레이스 조회
harness test-scaffold --stack ts  # AC → 테스트 스캐폴드 생성
harness mcp-serve                 # MCP 서버 시작 (stdio/sse)
```

### MCP 서버

외부 AI 에이전트에서 하네스 기능을 MCP 도구로 호출:

```bash
pip install ai-harness-pro[mcp]
harness mcp-serve  # Claude Code, Cursor 등에서 연결
```

**제공 도구**: 11개 게이트 (`check_boundaries`, `check_layers`, ...) + `get_seed_spec` + `get_interview` + `get_ambiguity_score` + `get_trace` + `get_audit_log` + `run_all_gates`

**제공 리소스**: `harness://architecture-invariants`, `harness://code-conventions`, `harness://boundary-rules`

### Pro Hooks

| Hook | 트리거 | 역할 |
|------|--------|------|
| `keyword-detector.py` | UserPromptSubmit | 커맨드 키워드 감지 → CLI 라우팅 |
| `drift-monitor.py` | PostToolUse(Edit/Write) | 편집 후 자동 드리프트 측정 |
| `session-start.py` | SessionStart | 세션 초기화, EventStore 연결 |

---

## 설치 상세

### init.sh 실행 과정 (12 Steps)

```
./init.sh /path/to/project
    │
    ├─ [사전 검증] 디렉토리 존재/쓰기 권한/소스 파일 무결성
    ├─ [Step 1]  스택 감지 (lib/detect-stack.sh)
    ├─ [Step 2]  권한 프리셋 선택 (strict/standard/permissive)
    ├─ [Step 3]  프로젝트 이름 입력
    ├─ [Step 4]  CLAUDE.md 생성 (스택별 조건부)
    ├─ [Step 5]  ARCHITECTURE_INVARIANTS.md 생성
    ├─ [Step 6]  docs/ 생성 (code-convention, adr)
    ├─ [Step 7]  .claude/settings.local.json 설치
    ├─ [Step 8]  커맨드(10개) & 에이전트(9개) 복사
    ├─ [Step 9]  게이트(11개) & 규칙 설치
    ├─ [Step 10] pre-commit hook 설치
    ├─ [Step 11] GitHub Actions 워크플로우 (선택)
    └─ [Step 12] .gitignore 업데이트
```

### 지원 스택 (자동 감지)

| 카테고리 | 감지 대상 |
|----------|----------|
| **Node.js** | Next.js, NestJS, React, Vue, Nuxt, Svelte, SvelteKit, Remix, Astro, Express, Fastify, Hono |
| **Python** | FastAPI, Django, Flask |
| **Go** | Go, Gin, Chi |
| **Rust** | Rust, Actix, Axum |
| **Java/Kotlin** | Spring, Gradle, Maven |
| **ORM/DB** | Prisma, Alembic, Drizzle |
| **모노레포** | pnpm-workspace, Turborepo, Lerna |
| **인프라** | Docker, GitHub Actions |
| **패키지 매니저** | npm, yarn, pnpm, bun, pip, poetry, uv, pipenv, go, cargo, maven/gradle |

### 권한 프리셋

| Preset | 대상 | 차단 |
|--------|------|------|
| **strict** | 프로덕션/클라이언트 | rm -rf, DROP TABLE, sudo, git reset --hard |
| **standard** (기본) | 일반 개발 | rm -rf /, force push, sudo rm |
| **permissive** | 프로토타이핑 | rm -rf /, main force push |

### 문서 우선순위

```
1. ARCHITECTURE_INVARIANTS.md  (최상위 — 모든 것에 우선)
2. docs/adr.yaml              (아키텍처 결정 기록)
3. CLAUDE.md                   (AI 에이전트 컨텍스트)
4. docs/code-convention.yaml   (코딩 컨벤션)
```

---

## 디렉토리 구조

### 설치된 프로젝트

```
my-project/
├── CLAUDE.md                        # AI 에이전트 컨텍스트 (자동 생성)
├── ARCHITECTURE_INVARIANTS.md       # 절대 불변 규칙 (3-tier invariant 포함)
├── docs/
│   ├── code-convention.yaml         # 코딩 컨벤션 (LAYER + 스택별 규칙)
│   ├── adr.yaml                     # 아키텍처 결정 기록
│   └── TRD.md                       # 기술 설계서 (/trd 커맨드로 생성됨)
├── .claude/
│   ├── settings.local.json          # 권한 프리셋
│   ├── commands/                    # 슬래시 커맨드 (10개)
│   │   ├── interview.md, seed.md, trd.md, decompose.md, run.md
│   │   ├── evaluate.md, evolve.md, rollback.md, unstuck.md, pm.md
│   └── agents/                      # 에이전트 (9개 + topology)
│       ├── interviewer.md ... hacker.md
│       └── topology.yaml            # 에이전트 협업 패턴
├── .harness/
│   ├── gates/                       # 게이트 스크립트 (11개)
│   │   ├── check-boundaries.sh      check-layers.sh
│   │   ├── check-secrets.sh         check-security.sh
│   │   ├── check-structure.sh       check-spec.sh
│   │   ├── check-complexity.sh      check-deps.sh
│   │   ├── check-mutation.sh        check-performance.sh
│   │   ├── check-ai-antipatterns.sh
│   │   └── rules/
│   │       ├── boundaries.yaml      # 의존성 + 레이어 규칙
│   │       └── structure.yaml       # 파일 배치 규칙
│   ├── hooks/
│   │   ├── post-edit-lint.sh        # 편집 후 자동 린트
│   │   └── pre-commit-gate.sh       # 커밋 전 게이트
│   └── detect-violations.sh         # 전체 게이트 통합 실행
├── .ouroboros/
│   ├── seeds/seed-v*.yaml           # 불변 시드 스펙 (버전별)
│   ├── interviews/*.yaml            # 인터뷰 기록
│   ├── evaluations/*.yaml           # 평가 결과
│   ├── templates/seed-spec.yaml
│   ├── scoring/ambiguity-checklist.yaml
│   └── session.db                   # Pro: SQLite EventStore
└── .github/
    └── workflows/harness-gates.yaml  # CI 워크플로우 (선택)
```

---

## 데이터 흐름

### 전체 워크플로우

```
[사용자 요구]
    ▼
/interview ── 질문 → 답변 → 차원별 명확도 → ambiguity ≤ 0.2 통과
    ▼
/seed ─────── 인터뷰 → 온톨로지 추출 (subagent) → 불변 명세
    ▼
/trd ──────── 논의 먼저 → 레이어별 설계 → docs/TRD.md
    ▼
/decompose ── AC → 원자적 태스크 (레이어별, 의존성 순서)
    ▼
/run ──────── Double Diamond: Discover → Define → Design → Deliver
              구현 순서: Data → Logic → Presentation
              모듈마다 즉시 테스트 작성
    ▼
게이트 자동 실행 ── layers + boundaries + secrets + security
    ▼
/evaluate ──── Stage 1 (Mechanical) → Stage 2 (Semantic) → Stage 3 (Judgment)
    ▼
├── PASS → git commit → pre-commit 게이트 → push → CI
└── FAIL → /evolve → Wonder → Reflect → Re-seed → 반복
```

### 게이트 실행 흐름

```
git commit -m "..."
    ↓
.git/hooks/pre-commit → .harness/hooks/pre-commit-gate.sh
    ↓
┌─ check-secrets.sh --staged (35+ 패턴)
├─ check-boundaries.sh (boundaries.yaml)
└─ check-structure.sh (.env, SQL 위치)
    ↓
ANY FAIL → 커밋 차단 | ALL PASS → 커밋 허용
```

### 피드백 루프

```
위반 발생 → detect-violations.sh
    → 분류 (규칙 부재 | 불명확 | 게이트 미비 | 오탐)
    → 규칙 추가 (boundaries.yaml / code-convention.yaml / adr.yaml)
    → 게이트 반영 → 검증 → 시스템 강건화
```

---

## Examples

`examples/` 디렉토리에 스택별 설정 예시:

- `examples/nextjs-fastapi/` — Next.js + FastAPI
- `examples/nextjs-nestjs/` — Next.js + NestJS
- `examples/nextjs-django/` — Next.js + Django
- `examples/python-only/` — Python standalone

---

## Acknowledgments & Inspirations

- [vibemafiaclub/mafia-codereview-harness](https://github.com/vibemafiaclub/mafia-codereview-harness) — Early reference for code review pipeline structure and convention categorization approach (our conventions are independently authored)
- [greatSumini/gpters-lecture](https://github.com/greatSumini/gpters-lecture-260323) — 3-tier layered architecture prompting patterns
- [Q00/ouroboros](https://github.com/Q00/ouroboros) — Ouroboros specification-first development concepts
- Peter Steinberger (OpenClaw) — Planning-first development philosophy
- Addy Osmani — Harness Engineering concept
- "Human steers, Agent executes" — OpenAI

## License

MIT
