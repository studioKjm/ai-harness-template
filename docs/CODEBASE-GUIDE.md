# AI Harness + Ouroboros 코드베이스 가이드

> **"프롬프트는 요청이고, 하네스는 강제다"**
>
> AI 에이전트 하네스 엔지니어링 + Ouroboros(명세 기반 개발) 통합 프레임워크.
> Lite(bash only) / Pro(Python enhanced) 두 가지 버전을 제공합니다.

---

## 목차

1. [시스템 전체 구조](#1-시스템-전체-구조)
2. [설치 흐름 (init.sh)](#2-설치-흐름)
3. [Ouroboros 워크플로우](#3-ouroboros-워크플로우)
4. [7개 게이트 (자동 강제)](#4-7개-게이트)
5. [3-Tier Layered Architecture](#5-3-tier-layered-architecture)
6. [9개 에이전트 페르소나](#6-9개-에이전트-페르소나)
7. [권한 프리셋](#7-권한-프리셋)
8. [컨텍스트 파일](#8-컨텍스트-파일)
9. [Pro 버전 (Python 강화)](#9-pro-버전)
10. [피드백 루프](#10-피드백-루프)
11. [디렉토리 구조](#11-디렉토리-구조)
12. [데이터 흐름](#12-데이터-흐름)
13. [파일별 역할 레퍼런스](#13-파일별-역할-레퍼런스)

---

## 1. 시스템 전체 구조

```
┌───────────────────────────────────────────────────────────────┐
│  OUROBOROS (명세 기반 개발 루프)                                │
│  /interview → /seed → /trd → /run → /evaluate → /evolve       │
│       ↑                                              │        │
│       └──────────── (수렴까지 반복) ─────────────────┘        │
└───────────────────────────────────────────────────────────────┘
                        ↕ (강제됨)
┌───────────────────────────────────────────────────────────────┐
│  HARNESS GATES (구조적 가드레일)                               │
│  boundaries | layers | secrets | structure | complexity | deps │
└───────────────────────────────────────────────────────────────┘
                        ↕ (학습됨)
┌───────────────────────────────────────────────────────────────┐
│  FEEDBACK LOOP (자기 강화)                                    │
│  위반 감지 → 분류 → 규칙 추가 → 게이트 반영 → 시스템 강건화     │
└───────────────────────────────────────────────────────────────┘
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

## 2. 설치 흐름

### init.sh 실행 과정

```
./init.sh /path/to/project
    │
    ├─ [사전 검증] 디렉토리 존재/쓰기 권한/소스 파일 무결성
    │
    ├─ [Step 1] lib/detect-stack.sh
    │   → JSON {stacks, package_manager, frontend_dir, backend_dir}
    │
    ├─ [Step 2] 권한 프리셋 선택
    │   → strict | standard(기본) | permissive
    │
    ├─ [Step 3-4] lib/render-template.sh
    │   → CLAUDE.md (스택별 조건부 섹션 포함)
    │   → ARCHITECTURE_INVARIANTS.md (3-tier invariant 프리필)
    │
    ├─ [Step 5] docs/ 생성
    │   → code-convention.yaml, adr.yaml
    │
    ├─ [Step 6] .claude/settings.local.json 설치
    │
    ├─ [Step 7] 커맨드 & 에이전트 복사
    │   → .claude/commands/ (8개 .md)
    │   → .claude/agents/ (9개 .md)
    │
    ├─ [Step 8] 게이트 & 규칙 설치
    │   → .harness/gates/ (7개 .sh + rules/*.yaml)
    │   → .harness/hooks/ (pre-commit-gate, post-edit-lint)
    │
    ├─ [Step 9] pre-commit hook 설치
    │
    ├─ [Step 10] GitHub Actions 워크플로우 (선택)
    │
    └─ [Step 11] .gitignore 업데이트
```

### 스택 감지 (lib/detect-stack.sh)

| 카테고리 | 감지 대상 |
|----------|----------|
| **Node.js** | Next.js, NestJS, React, Vue, Nuxt, Svelte, SvelteKit, Remix, Astro, Express, Fastify, Hono |
| **Python** | FastAPI, Django, Flask |
| **Go** | Go, Gin, Chi |
| **Rust** | Rust, Actix, Axum |
| **Java/Kotlin** | Spring, Gradle, Maven |
| **ORM/DB** | Prisma, Alembic, Drizzle, TypeORM |
| **모노레포** | pnpm-workspace, Turborepo, Lerna |
| **인프라** | Docker, GitHub Actions |
| **패키지 매니저** | npm, yarn, pnpm, bun, pip, poetry, uv, pipenv, go, cargo, maven/gradle |

### 템플릿 렌더링 (lib/render-template.sh)

Handlebars 스타일 템플릿 엔진:
- `{{KEY}}` → 변수 치환
- `{{#IF_HAS_NEXTJS}}...{{/IF_HAS_NEXTJS}}` → 조건부 블록

---

## 3. Ouroboros 워크플로우

### 전체 흐름

```
/interview    →    /seed    →    /trd     →    /run    →    /evaluate    →    /evolve
 (명세 확정)    (스펙 생성)    (기술 설계)    (구현)      (검증)           (진화)
```

### 3.1 /interview — 소크라테스식 인터뷰

**에이전트**: Interviewer (질문만 함, 답을 주지 않음)

**4개 차원 추적**:

| 차원 | 비중 | 목표 질문 |
|------|------|----------|
| Goal Clarity | 40% | 무엇을 만들고 싶은가? 누구를 위한 것인가? |
| Constraint Clarity | 30% | 절대 하면 안 되는 것은? 기술 스택 제약은? |
| Success Criteria | 30% | 완료를 어떻게 판단하나? 엣지 케이스는? |
| Context Clarity | 15% | 기존 코드 구조는? 영향 범위는? (brownfield만) |

**모호성 점수 계산**:
```
ambiguity = 1.0 - Σ(clarity_i × weight_i)
게이트: ambiguity ≤ 0.2 이어야 /seed 진행 가능
```

**출력**: `.ouroboros/interviews/YYYY-MM-DD-HH-MM.yaml`

### 3.2 /seed — 불변 명세 생성

**에이전트**: Seed Architect

시드 스펙 구조 (`seed-v{N}.yaml`):
```yaml
version: 1
goal: { summary, detail, non_goals }
constraints: { must, must_not, should }
acceptance_criteria:
  - { id, description, verification, priority }
ontology:
  entities: [{ name, fields, relationships }]
  actions: [{ name, actor, input, output, side_effects }]
architecture:
  pattern: "3-tier-layered"
  layers: { presentation, logic, data }
  layer_communication: { ... }
scope: { mvp, future }
tech_decisions: [{ decision, reason, alternatives }]
```

**검증 항목**: 필수 필드 존재, AC ≥ 2개, TODO/TBD 없음

**불변 원칙**: 한번 생성된 seed-v1.yaml은 절대 수정 불가. 변경은 seed-v2.yaml로.

### 3.3 /trd — 기술 설계서

**핵심 원칙**: 바로 설계서를 작성하지 않는다. **논의 먼저**.

```
Phase 1: 탐색 (문서/코드베이스 파악)
    ↓
Phase 2: 큰 그림 제시 (Presentation/Logic/Data별)
    ↓
Phase 3: 논의점 제시 (모호한 부분, 결정 사항, resource/impact 설명)
    ↓
Phase 4: 최종 설계서 (/docs/TRD.md)
    ↓
Phase 5: 테스트 설계 (모듈 책임만 정확히 테스트)
```

**출력**: `/docs/TRD.md` (레이어별 설계 + 테스트 전략 + 구현 순서)

### 3.4 /run — Double Diamond 실행

**4 Phase**:

| Phase | 이름 | 활동 |
|-------|------|------|
| 1 | Discover (탐색) | 시드 재확인, 코드베이스 탐색, 리스크 식별 |
| 2 | Define (정의) | 범위 확정, 구현 순서(의존성 기반), 테스트 전략 |
| 3 | **Design (설계)** | **레이어 영향 분석 → 레이어별 설계 → 계약(DTO) 설계 → 레이어별 테스트 전략** |
| 4 | Deliver (구현) | **Data → Logic → Presentation 순서 구현, 모듈마다 즉시 테스트 작성** |

**Deliver 규칙**:
1. 시드 스펙에 없는 기능 추가 금지
2. AC 미충족 = 미완성
3. 구현 순서: Data → Logic → Presentation
4. 모듈 구현 직후 해당 테스트 즉시 작성 (일괄 작성 금지)
5. 레이어 경계 import 위반 발견 시 즉시 수정

### 3.5 /evaluate — 3단계 검증

```
Stage 1: Mechanical ($0)
├── 게이트 실행 (boundaries, layers, secrets, structure)
├── Lint (ESLint, ruff)
├── Type check (tsc, mypy)
├── Build (npm run build)
└── Tests (npm test, pytest)

Stage 2: Semantic
├── AC 준수 여부 (MET / PARTIALLY MET / NOT MET)
├── 목표 정합성 (ALIGNED / DRIFTED)
├── 제약 위반 (must/must_not)
├── 온톨로지 드리프트 (LOW / MEDIUM / HIGH)
├── 레이어 컴플라이언스 (check-layers.sh)
└── 레이어별 테스트 커버리지

Stage 3: Judgment (선택적)
├── 코드 품질 (1-5)
├── 엣지 케이스 (COVERED / GAPS)
├── 에러 핸들링 (ADEQUATE / INSUFFICIENT)
└── 리뷰 준비 (YES / NO)
```

**출력**: `.ouroboros/evaluations/eval-{seed-version}-{date}.yaml`

### 3.6 /evolve — 진화 루프

```
Wonder (뭘 모르나?) → Reflect (학습 반영) → Re-seed (필요시 v2 생성)
```

**수렴 판정**:
```
Ontology Similarity = 0.5 × name_overlap + 0.3 × type_match + 0.2 × exact_match
similarity ≥ 0.95 → 수렴 완료 (루프 종료)
```

**안티패턴 감지**: 진동(같은 변경 반복), 정체(유사도 변화 없음), 폭발(무한 팽창)

### 3.7 /unstuck — 다관점 문제 해결

5명의 에이전트가 각자 관점에서 분석:
- Contrarian(반대), Simplifier(단순화), Researcher(조사), Architect(구조), Hacker(우회)

### 3.8 /pm — PRD 자동 생성

인터뷰 결과 → Product Requirements Document 생성

---

## 4. 7개 게이트

### 게이트 목록

| 게이트 | 파일 | 검사 대상 | 차단 |
|--------|------|----------|------|
| **Boundaries** | `check-boundaries.sh` | `boundaries.yaml` 기반 금지 import | 차단 |
| **Layers** | `check-layers.sh` | 3-tier 레이어 분리 위반 | 차단 |
| **Secrets** | `check-secrets.sh` | 35+ 시크릿 패턴 | 차단 |
| **Structure** | `check-structure.sh` | 파일 배치 규칙 | 차단 |
| **Spec** | `check-spec.sh` | 시드 스펙 필수 필드 | 차단 |
| **Complexity** | `check-complexity.sh` | 함수/파일 길이, 파라미터 수, 중첩 깊이 | 경고 |
| **Dependencies** | `check-deps.sh` | npm/pip/go/cargo audit 위임 | 차단 |

### 실행 시점

```
개발자: git commit → pre-commit hook → 자동 실행 (secrets, boundaries, structure)
CI: push/PR → .github/workflows/harness-gates.yaml → 전체 게이트
수동: .harness/detect-violations.sh → 전체 게이트
```

### boundaries.yaml 규칙 형식

```yaml
nextjs:
  - from: "src/components"
    cannot_import: ["prisma", "@prisma/client", "pg"]
    reason: "[LAYER:P→D] 프론트엔드 컴포넌트에서 DB 직접 접근 금지"
    stacks: [nextjs]
    file_patterns: ["*.tsx", "*.ts"]
```

### check-layers.sh 검사 내용

| 검사 | 설명 | 예시 |
|------|------|------|
| P→D 스킵 | Presentation에서 Data 직접 접근 | 컴포넌트에서 PrismaClient import |
| L→P 역참조 | Logic에서 Presentation 프레임워크 의존 | 서비스에서 React import |
| D→P 역참조 | Data에서 Presentation 의존 | 레포지토리에서 express.Response import |
| 대형 Presentation 파일 | 200줄 초과 → 비즈니스 로직 혼입 의심 | 500줄짜리 Controller |

### 시크릿 패턴 (check-secrets.sh)

| 카테고리 | 패턴 수 | 예시 |
|----------|---------|------|
| AWS | 2 | `AKIA...`, `ASIA...` |
| OpenAI/Stripe | 3 | `sk-...`, `sk_live_...`, `rk_live_...` |
| GitHub | 5 | `ghp_...`, `ghs_...`, `github_pat_...` |
| Slack | 4 | `xoxb-...`, `xoxp-...`, `xapp-...` |
| Firebase/Google | 2 | `AIza...`, `"type": "service_account"` |
| Twilio/SendGrid | 3 | `SK...`, `AC...`, `SG.....` |
| 기타 | 10+ | JWT, Vercel, Supabase, Anthropic, Private Keys |
| 접속 문자열 | 8 | postgres://, mongodb+srv://, redis://, amqp:// |
| 제네릭 | 6 | password=, secret=, api_key=, DATABASE_URL= |

### 복잡도 임계값 (check-complexity.sh)

| 메트릭 | 기본값 | 설정 가능 |
|--------|--------|----------|
| 함수 길이 | 80줄 | `--max-lines=N` |
| 파라미터 수 | 5개 | `--max-params=N` |
| 파일 길이 | 500줄 | `--max-file-lines=N` |
| 중첩 깊이 | 5단계 | - |

---

## 5. 3-Tier Layered Architecture

### 레이어 정의

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Presentation    │────→│     Logic        │────→│      Data        │
│  (사용자 소통)    │     │  (비즈니스 규칙)   │     │  (데이터 소통)    │
├──────────────────┤     ├──────────────────┤     ├──────────────────┤
│ UI, HTTP 경계     │     │ 알고리즘, 검증    │     │ DB 조작          │
│ 입력 검증         │     │ 트랜잭션 관리     │     │ 외부 API 호출    │
│ 응답 포맷팅       │     │ 서비스 조율       │     │ 캐싱             │
├──────────────────┤     ├──────────────────┤     ├──────────────────┤
│ ❌ 비즈니스 로직  │     │ ❌ UI 코드       │     │ ❌ 비즈니스 로직  │
│ ❌ DB 직접 접근   │     │ ❌ Raw SQL       │     │ ❌ Presentation   │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

### 통신 규칙

```
✅ Presentation → Logic (via service injection/call)
✅ Logic → Data (via repository/ORM)
❌ Presentation → Data (레이어 스킵 — 금지)
❌ Data → Logic (역참조 — 금지)
❌ Logic → Presentation (역참조 — 금지)
```

- 레이어 간 통신은 **DTO/Interface**를 통해서만
- 내부 도메인 객체나 ORM Entity를 레이어 경계 너머로 직접 전달 금지

### 스택별 매핑

| Layer | Next.js | NestJS | FastAPI | Django |
|-------|---------|--------|---------|--------|
| **Presentation** | pages, app, Components | Controllers, DTOs, Guards | Routes, Pydantic Models | Views, Templates, Serializers |
| **Logic** | services, lib, Server Actions | Services, Domain Models | Services, Domain Logic | Models/Managers, Services |
| **Data** | repositories, Prisma Client | Repositories, TypeORM | SQLAlchemy, Repositories | Django ORM, QuerySets |

### 레이어별 테스트 전략

| Layer | 테스트 유형 | 핵심 원칙 |
|-------|-----------|----------|
| **Logic** | 단위 테스트 | 순수 비즈니스 로직에 집중, mock은 레이어 경계에서만 |
| **Data** | 통합 테스트 | 실제 DB/외부 서비스 연동 검증 |
| **Presentation** | E2E/API 테스트 | UI 렌더링, 라우팅, 요청/응답 검증 |

**원칙**: 구현과 테스트를 함께 작성. 일괄 작성 금지. mock으로 접착제 코드를 테스트하지 않는다.

### 강제 메커니즘

| 도구 | 역할 |
|------|------|
| `CLAUDE.md.hbs` | 레이어 정의 + 스택별 매핑 명시 |
| `architecture-invariants.md.hbs` | 3개 기본 invariant 프리필 |
| `code-convention.yaml` | LAYER-001~006 규칙 |
| `boundaries.yaml` | layer_logic, layer_data, layer_skip 규칙 |
| `check-layers.sh` | 자동 import 패턴 검출 게이트 |
| `seed-spec.yaml` | architecture 섹션 (layers, communication) |
| `/trd` 커맨드 | 레이어별 설계 워크플로우 |
| `/run` 커맨드 | Design이 레이어 기준, Deliver가 D→L→P 순서 |
| `/evaluate` 커맨드 | Stage 2에 Layer Compliance 체크 |

---

## 6. 9개 에이전트 페르소나

### 코어 에이전트 (4개)

| 에이전트 | 역할 | 사용 시점 | 핵심 제약 |
|----------|------|----------|----------|
| **Interviewer** | 질문만 한다 | `/interview` | 답/해결책 제시 금지 |
| **Ontologist** | 본질을 정의한다 | `/seed` | 도메인 모델 추출 |
| **Seed Architect** | 스펙을 결정화한다 | `/seed` | 불변 명세 생성 |
| **Evaluator** | 검증한다 | `/evaluate` | 3단계 검증 수행 |

### 확장 에이전트 (5개 — `/unstuck` 용)

| 에이전트 | 관점 | 질문 패턴 |
|----------|------|----------|
| **Contrarian** | 반대 상황 | "만약 ~가 아니라면?" |
| **Simplifier** | 불필요한 복잡성 제거 | "이것이 정말 필요한가?" |
| **Researcher** | 근거 기반 조사 | "실제 데이터/사례는?" |
| **Architect** | 구조적 근본 원인 | "구조가 이 문제를 만드는가?" |
| **Hacker** | 우회로/대안 | "규칙을 깨지 않고 다르게 할 수 있나?" |

---

## 7. 권한 프리셋

| 프리셋 | 대상 | 허용 | 차단 |
|--------|------|------|------|
| **strict** | 프로덕션/클라이언트 | Read, Glob, Grep, git (읽기만) | rm -rf, DROP TABLE, sudo, git reset --hard, chmod 777 |
| **standard** (기본) | 일반 개발 | 모든 도구 + npm, pip, docker, pytest | rm -rf /, DROP DATABASE, git --force, sudo rm |
| **permissive** | 프로토타이핑 | Bash(*) — 거의 전부 | rm -rf /, main force push |

설치 위치: `.claude/settings.local.json`

### Hook 통합

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": { "tool": "Edit" },
      "command": ".harness/hooks/post-edit-lint.sh $CLAUDE_FILE_PATH"
    }],
    "PreCommit": [{
      "command": ".harness/hooks/pre-commit-gate.sh"
    }]
  }
}
```

- **post-edit-lint.sh**: 편집 후 자동 포맷 (ESLint, Prettier, ruff, black)
- **pre-commit-gate.sh**: 커밋 전 게이트 자동 실행

---

## 8. 컨텍스트 파일

### 문서 우선순위

```
1. ARCHITECTURE_INVARIANTS.md  (최상위 — 모든 것에 우선)
2. docs/adr.yaml              (아키텍처 결정 기록)
3. CLAUDE.md                   (AI 에이전트 컨텍스트)
4. docs/code-convention.yaml   (코딩 컨벤션)
```

### CLAUDE.md (자동 생성)

`templates/CLAUDE.md.hbs`에서 스택별 조건부 생성:

- **공통**: Absolute Rules, Architecture Layers (3-Tier), Development Workflow
- **스택별**: `{{#IF_HAS_NEXTJS}}`, `{{#IF_HAS_NESTJS}}` 등으로 조건부 포함
- **게이트**: 사용 가능한 게이트 커맨드 목록
- **에이전트**: 9개 에이전트 테이블

### ARCHITECTURE_INVARIANTS.md (자동 생성)

5개 파트:
1. **Absolute Invariants** — 레이어 분리, 서비스 경계, DTO 계약 (3개 프리필 + TODO)
2. **Dependency Boundaries** — 스택별 금지 import 테이블
3. **Work Guidelines** — 체크리스트, 의존성 추가 절차
4. **CI/CD Rules** — PR 게이트, --no-verify 금지
5. **Document Maintenance** — 분기 1회 리뷰

### code-convention.yaml

```yaml
three_tier:    # LAYER-001 ~ LAYER-006 (전 스택 공통)
general:       # GEN-001 ~ GEN-006
typescript:    # TS-001 ~ TS-005
python:        # PY-001 ~ PY-004
nextjs:        # NEXT-001 ~ NEXT-004
nestjs:        # NEST-001 ~ NEST-004
fastapi:       # FA-001 ~ FA-004
django:        # DJ-001 ~ DJ-003
monorepo:      # MONO-001 ~ MONO-003
```

### adr.yaml (Architecture Decision Records)

```yaml
- id: ADR-001
  title: "API Response Format Unification"
  status: adopted|deprecated|superseded
  date: 2026-01-01
  stacks: [all]
  context: "..."
  decision: "..."
  consequence: "..."
```

---

## 9. Pro 버전

### 아키텍처

```
pro/src/harness_pro/
├── cli.py                 # Typer CLI (8개 커맨드)
├── interview/engine.py    # 인터뷰 엔진 + 명확도 점수화
├── scoring/ambiguity.py   # 모호성 수식 계산
├── ontology/extractor.py  # 엔티티/관계/액션 추출
├── evaluation/pipeline.py # 3단계 자동 평가
├── persistence/store.py   # SQLite EventStore (sessions, events, audit_log)
├── drift/monitor.py       # 시드 대비 드리프트 측정
└── testing/scaffold.py    # AC → 테스트 스캐폴드 생성
```

### CLI 커맨드

```bash
harness interview "topic"      # 인터뷰 시작, 모호성 점수 반환
harness seed                   # 최신 인터뷰 → 시드 생성
harness score                  # 현재 모호성 점수 표시
harness evaluate               # 3단계 검증 실행
harness drift <file>           # 시드 대비 드리프트 측정
harness status                 # 세션 상태 표시
harness audit [--summary]      # 감사 로그 조회
harness test-scaffold --stack  # AC → 테스트 스캐폴드 생성
```

### 주요 모듈 상세

#### Interview Engine (`interview/engine.py`)

- **질문 생성**: 차원별(Goal/Constraint/Success/Context) 질문 셋 제공
- **명확도 자동 점수화**: 답변 길이, 시그널 키워드, 구체성 휴리스틱으로 0~1 점수 계산
- **감쇠 수익**: 같은 차원에 답변이 쌓일수록 기여도 감소 (`remaining × delta`)
- **의사결정/가정 자동 추출**: 정규식 패턴으로 "will use", "assuming" 등 감지
- **출력**: `.ouroboros/interviews/YYYY-MM-DD-HH-MM.yaml`

#### Ontology Extractor (`ontology/extractor.py`)

- **엔티티 추출**: 대문자 용어, 빈출 명사, 도메인 패턴 (user, order, product 등)
- **관계 추출**: "has many", "belongs to", "creates" 등 패턴 매칭
- **액션 추출**: 동사 패턴 ("user creates order" → `create_order`)
- **유사도 계산**: `0.5 × name_overlap + 0.3 × type_match + 0.2 × exact_match`

#### Evaluation Pipeline (`evaluation/pipeline.py`)

3단계 자동 평가:
1. **Mechanical**: 게이트 실행 + lint + build + tests
2. **Semantic**: AC 준수(키워드 매칭), 목표 정합(goal 키워드), 온톨로지 커버리지, 제약 위반 검출
3. **Judgment**: Stage 2 결과가 모호할 때만 실행

감사 로그 자동 기록 (`store.log_audit()`)

#### Drift Monitor (`drift/monitor.py`)

3가지 드리프트 측정:
1. **온톨로지 정합** — 시드 엔티티/필드 이름이 코드에 존재하는지 (snake_case/camelCase 변형 포함)
2. **범위 드리프트** — non_goals 키워드가 파일 경로에 나타나는지
3. **제약 준수** — must_not 키워드가 코드에 나타나는지

#### Test Scaffold Generator (`testing/scaffold.py`)

시드 스펙의 `acceptance_criteria`에서 테스트 파일 생성:

| 스택 | 프레임워크 | 확장자 |
|------|-----------|--------|
| Next.js, React, NestJS | Jest | `.test.tsx`, `.spec.ts` |
| Vue, Svelte, Remix, Hono | Vitest | `.test.ts` |
| FastAPI, Django, Flask, Python | pytest | `_test.py` |
| Go | go test | `_test.go` |
| Rust | cargo test | `.rs` (tests/) |

#### EventStore (`persistence/store.py`)

SQLite 기반 3개 테이블:
- **sessions**: id, created, phase, seed_ref, generation
- **events**: id, session_id, event_type, timestamp, data
- **audit_log**: id, timestamp, action, actor, target, result, details

### Pro 설치

```bash
pro/install.sh /path/to/project
# 1. Python 3.11+ 확인
# 2. Lite 먼저 설치 (init.sh)
# 3. pip install -e . (pydantic, pyyaml, aiosqlite, rich, typer)
# 4. Pro hooks 설치 (keyword-detector, drift-monitor, session-start)
```

### Pro Hooks

| Hook | 트리거 | 역할 |
|------|--------|------|
| `keyword-detector.py` | UserPromptSubmit | `/interview`, `/seed` 등 키워드 감지 → CLI 라우팅 |
| `drift-monitor.py` | PostToolUse(Edit/Write) | 편집 후 자동 드리프트 측정 |
| `session-start.py` | SessionStart | 세션 초기화, EventStore 연결 |

---

## 10. 피드백 루프

### 자기 강화 사이클

```
위반 발생
    ↓
detect-violations.sh (전체 게이트 실행)
    ↓
분류: 규칙 부재 | 규칙 불명확 | 게이트 미비 | 오탐
    ↓
규칙 추가/수정
  ├── boundaries.yaml (의존성 제한)
  ├── code-convention.yaml (코딩 표준)
  ├── structure.yaml (파일 배치)
  └── adr.yaml (아키텍처 결정)
    ↓
게이트 반영 → 검증 → 시스템 강건화
```

### evolve-rules.md 프로세스

```
Mistake → Analysis → Add Rule → Gate Reflection → Validation → System Strengthens
```

**원칙**:
- 구체적으로 작성 (모호한 규칙은 오히려 해로움)
- 과도하게 규제하지 않음
- 정기적으로 리뷰 (분기 1회)
- 오탐(false positive)은 즉시 수정

---

## 11. 디렉토리 구조

### 하네스 템플릿 저장소

```
harness/
├── init.sh                              # Lite 설치 스크립트
├── CLAUDE.md                            # 하네스 메타 문서
├── README.md                            # 프로젝트 설명 (한국어)
├── LICENSE                              # MIT
│
├── lib/                                 # 공유 유틸리티
│   ├── colors.sh                        #   터미널 색상 출력
│   ├── detect-stack.sh                  #   스택 자동 감지
│   └── render-template.sh              #   Handlebars 템플릿 렌더링
│
├── templates/                           # 프로젝트에 생성할 템플릿
│   ├── CLAUDE.md.hbs                    #   AI 컨텍스트 (스택별 조건부)
│   ├── architecture-invariants.md.hbs   #   아키텍처 불변 규칙
│   ├── code-convention.yaml             #   코딩 컨벤션
│   ├── adr.yaml                         #   ADR 템플릿
│   └── github-actions-gates.yaml        #   CI 워크플로우
│
├── commands/                            # Ouroboros 슬래시 커맨드 (8개)
│   ├── interview.md                     #   /interview
│   ├── seed.md                          #   /seed
│   ├── trd.md                           #   /trd
│   ├── run.md                           #   /run
│   ├── evaluate.md                      #   /evaluate
│   ├── evolve.md                        #   /evolve
│   ├── unstuck.md                       #   /unstuck
│   └── pm.md                            #   /pm
│
├── agents/                              # 에이전트 페르소나 (9개)
│   ├── interviewer.md
│   ├── ontologist.md
│   ├── seed-architect.md
│   ├── evaluator.md
│   ├── contrarian.md
│   ├── simplifier.md
│   ├── researcher.md
│   ├── architect.md
│   └── hacker.md
│
├── gates/                               # CI/CD 게이트
│   ├── check-boundaries.sh              #   의존성 경계 검사
│   ├── check-layers.sh                  #   3-tier 레이어 분리 검사
│   ├── check-secrets.sh                 #   시크릿 탐지
│   ├── check-structure.sh              #   프로젝트 구조 검증
│   ├── check-spec.sh                    #   시드 스펙 완성도
│   ├── check-complexity.sh              #   코드 복잡도
│   ├── check-deps.sh                    #   의존성 취약점
│   ├── install-hooks.sh                 #   git hooks 설치
│   └── rules/
│       ├── boundaries.yaml              #     의존성 제한 규칙
│       └── structure.yaml               #     파일 배치 규칙
│
├── boundaries/                          # Claude Code 권한 설정
│   ├── presets/
│   │   ├── strict.json                  #     프로덕션 (최대 제한)
│   │   ├── standard.json               #     일반 개발 (권장)
│   │   └── permissive.json             #     프로토타이핑 (최소 제한)
│   └── hooks/
│       ├── post-edit-lint.sh            #     편집 후 자동 린트
│       └── pre-commit-gate.sh           #     커밋 전 게이트
│
├── ouroboros/                           # 명세 기반 개발 도구
│   ├── templates/
│   │   └── seed-spec.yaml              #     시드 스펙 템플릿
│   └── scoring/
│       └── ambiguity-checklist.yaml     #     모호성 점수 체크리스트
│
├── feedback/                            # 피드백 루프 도구
│   ├── detect-violations.sh             #     통합 위반 스캐너
│   └── evolve-rules.md                  #     규칙 진화 가이드
│
├── examples/                            # 스택별 예시
│   ├── nextjs-fastapi/CLAUDE.md
│   ├── nextjs-nestjs/CLAUDE.md
│   ├── nextjs-django/CLAUDE.md
│   └── python-only/CLAUDE.md
│
├── pro/                                 # Pro 버전 (Python)
│   ├── install.sh                       #   Pro 설치 스크립트
│   ├── pyproject.toml                   #   Python 패키지 설정
│   ├── README.md                        #   Pro 문서
│   ├── src/harness_pro/
│   │   ├── cli.py                       #     Typer CLI
│   │   ├── interview/engine.py          #     인터뷰 엔진
│   │   ├── scoring/ambiguity.py         #     모호성 점수 계산
│   │   ├── ontology/extractor.py        #     온톨로지 추출
│   │   ├── evaluation/pipeline.py       #     3단계 평가
│   │   ├── persistence/store.py         #     SQLite EventStore
│   │   ├── drift/monitor.py             #     드리프트 측정
│   │   └── testing/scaffold.py          #     테스트 스캐폴드 생성
│   └── hooks/
│       ├── hooks.json                   #     Hook 설정
│       ├── keyword-detector.py          #     커맨드 라우팅
│       ├── drift-monitor.py             #     편집 후 드리프트
│       └── session-start.py             #     세션 초기화
│
└── docs/
    └── CODEBASE-GUIDE.md                # 이 문서
```

### 설치된 프로젝트 구조

```
my-project/
├── CLAUDE.md                       # AI 에이전트 컨텍스트
├── ARCHITECTURE_INVARIANTS.md      # 절대 불변 규칙
├── docs/
│   ├── code-convention.yaml        # 코딩 컨벤션
│   ├── adr.yaml                    # 아키텍처 결정 기록
│   └── TRD.md                      # 기술 설계서 (/trd로 생성)
├── .claude/
│   ├── settings.local.json         # 권한 프리셋
│   ├── commands/*.md               # 슬래시 커맨드 (8개)
│   └── agents/*.md                 # 에이전트 (9개)
├── .harness/
│   ├── gates/*.sh                  # 게이트 스크립트 (7개)
│   ├── gates/rules/*.yaml          # 게이트 규칙
│   ├── hooks/*.sh                  # Git hooks
│   └── detect-violations.sh        # 통합 스캐너
├── .ouroboros/
│   ├── seeds/seed-v*.yaml          # 불변 시드 스펙 (버전별)
│   ├── interviews/*.yaml           # 인터뷰 기록
│   ├── evaluations/*.yaml          # 평가 결과
│   ├── templates/seed-spec.yaml    # 시드 템플릿
│   ├── scoring/ambiguity-checklist.yaml
│   └── session.db                  # Pro: SQLite EventStore
└── .github/
    └── workflows/harness-gates.yaml # CI 워크플로우 (선택)
```

---

## 12. 데이터 흐름

### 명세 기반 개발 전체 흐름

```
[사용자 요구]
    │
    ▼
/interview ─── Interviewer 에이전트
    │           질문 → 답변 → 차원별 명확도 추적
    │           ambiguity ≤ 0.2 → 통과
    ▼
.ouroboros/interviews/YYYY-MM-DD.yaml
    │
    ▼
/seed ──────── Seed Architect 에이전트
    │           인터뷰 → 온톨로지 추출 → 불변 명세
    ▼
.ouroboros/seeds/seed-v1.yaml
    │
    ▼
/trd ───────── 논의 먼저 → 레이어별 설계 → 최종 문서
    │
    ▼
docs/TRD.md
    │
    ▼
/run ───────── Double Diamond
    │           Discover → Define → Design(레이어) → Deliver(D→L→P)
    │           모듈마다 즉시 테스트 작성
    ▼
구현된 코드 + 테스트
    │
    ├── check-layers.sh ──── 레이어 위반 차단
    ├── check-boundaries.sh ── 의존성 위반 차단
    ├── check-secrets.sh ──── 시크릿 유출 차단
    │
    ▼
/evaluate ──── Evaluator 에이전트
    │           Stage 1 (Mechanical) → Stage 2 (Semantic) → Stage 3 (Judgment)
    ▼
.ouroboros/evaluations/eval-seed-v1-date.yaml
    │
    ├── PASS → git commit → pre-commit 게이트 → push → CI 게이트
    │
    └── FAIL → /evolve
                │   Wonder → Reflect → Re-seed
                ▼
           seed-v2.yaml → /run → /evaluate (수렴까지 반복)
```

### 게이트 실행 흐름

```
git commit -m "..."
    ↓
.git/hooks/pre-commit
    ↓
.harness/hooks/pre-commit-gate.sh
    ↓
┌─ check-secrets.sh --staged
│    └─ 35+ regex 패턴 매칭
├─ check-boundaries.sh
│    └─ boundaries.yaml 파싱 → grep 검사
└─ check-structure.sh
     └─ .env 미커밋, SQL 위치 확인
    ↓
ANY FAIL → exit 1 → 커밋 차단
ALL PASS → 커밋 허용
```

### Pro 드리프트 모니터링 흐름

```
Claude Code: Edit/Write 실행
    ↓
PostToolUse Hook → drift-monitor.py
    ↓
DriftMonitor.measure(changed_file)
    ↓
┌─ 온톨로지 정합 (시드 엔티티가 코드에 있는지)
├─ 범위 드리프트 (non_goals 키워드가 파일에 있는지)
└─ 제약 준수 (must_not 키워드가 코드에 있는지)
    ↓
drift_score: 0.0 (정합) ~ 1.0 (완전 이탈)
    ↓
> 0.3 → HIGH DRIFT (경고)
> 0.1 → MODERATE DRIFT
≤ 0.1 → LOW DRIFT (정상)
```

---

## 13. 파일별 역할 레퍼런스

### Shell Scripts

| 파일 | 역할 | 의존성 |
|------|------|--------|
| `init.sh` | Lite 설치 부트스트랩 | lib/*.sh, templates/*, commands/*, agents/*, gates/* |
| `lib/colors.sh` | 터미널 색상 함수 | 없음 |
| `lib/detect-stack.sh` | 기술 스택 감지 | lib/colors.sh |
| `lib/render-template.sh` | Handlebars 템플릿 렌더링 | 없음 |
| `gates/check-boundaries.sh` | 금지 import 검사 | gates/rules/boundaries.yaml, lib/colors.sh |
| `gates/check-layers.sh` | 3-tier 레이어 분리 검사 | lib/colors.sh |
| `gates/check-secrets.sh` | 시크릿 패턴 탐지 | lib/colors.sh |
| `gates/check-structure.sh` | 파일 배치 규칙 검사 | gates/rules/structure.yaml, lib/colors.sh |
| `gates/check-spec.sh` | 시드 스펙 완성도 | .ouroboros/seeds/*.yaml |
| `gates/check-complexity.sh` | 코드 복잡도 측정 | lib/colors.sh |
| `gates/check-deps.sh` | 의존성 취약점 위임 | npm/pip-audit/govulncheck/cargo |
| `gates/install-hooks.sh` | git pre-commit 설치 | .git/hooks/ |
| `boundaries/hooks/pre-commit-gate.sh` | 커밋 전 게이트 실행 | gates/*.sh |
| `boundaries/hooks/post-edit-lint.sh` | 편집 후 자동 린트 | eslint/prettier/ruff/black |
| `feedback/detect-violations.sh` | 전체 게이트 통합 실행 | gates/*.sh |

### Python Modules (Pro)

| 파일 | 역할 | 의존성 |
|------|------|--------|
| `cli.py` | Typer CLI 진입점 | 모든 Pro 모듈 |
| `interview/engine.py` | 인터뷰 + 명확도 점수화 | yaml |
| `scoring/ambiguity.py` | 모호성 수식 계산 | yaml, rich |
| `ontology/extractor.py` | 온톨로지 추출 + 유사도 | yaml, re |
| `evaluation/pipeline.py` | 3단계 평가 파이프라인 | subprocess, yaml, persistence/store |
| `persistence/store.py` | SQLite EventStore + 감사 로그 | sqlite3, json |
| `drift/monitor.py` | 시드 대비 드리프트 측정 | yaml, re |
| `testing/scaffold.py` | AC → 테스트 스캐폴드 | yaml, re |

### Commands (Markdown Prompts)

| 파일 | 커맨드 | 에이전트 | 출력물 |
|------|--------|---------|--------|
| `interview.md` | `/interview` | Interviewer | `.ouroboros/interviews/*.yaml` |
| `seed.md` | `/seed` | Seed Architect | `.ouroboros/seeds/seed-v*.yaml` |
| `trd.md` | `/trd` | (Executor) | `docs/TRD.md` |
| `run.md` | `/run` | Executor | 구현 코드 + 테스트 |
| `evaluate.md` | `/evaluate` | Evaluator | `.ouroboros/evaluations/*.yaml` |
| `evolve.md` | `/evolve` | Evolver | 규칙 업데이트 + seed-v{N+1} |
| `unstuck.md` | `/unstuck` | 5개 에이전트 | 다관점 분석 |
| `pm.md` | `/pm` | PM | PRD 문서 |

### Configuration Files

| 파일 | 형식 | 역할 |
|------|------|------|
| `boundaries.yaml` | YAML | 금지 import 규칙 (스택별) |
| `structure.yaml` | YAML | 파일 배치 규칙 |
| `code-convention.yaml` | YAML | 코딩 컨벤션 (LAYER + 스택별) |
| `adr.yaml` | YAML | 아키텍처 결정 기록 |
| `seed-spec.yaml` | YAML | 시드 스펙 템플릿 |
| `ambiguity-checklist.yaml` | YAML | 모호성 점수 차원/기준 |
| `strict.json` | JSON | Claude Code 프로덕션 권한 |
| `standard.json` | JSON | Claude Code 일반 개발 권한 |
| `permissive.json` | JSON | Claude Code 프로토타이핑 권한 |
| `github-actions-gates.yaml` | YAML | CI 워크플로우 |

---

> 이 문서는 AI Harness Template 코드베이스의 전체 로직을 설명합니다.
> 최종 업데이트: 2026-04-11
