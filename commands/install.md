---
description: Interactive installation wizard for AI Harness Template. Guides through version, track, permissions, gates, and more via step-by-step questions.
argument-hint: [target-project-path]
---

# /install — 설치 마법사

> AI Harness Template을 대화형으로 설치합니다.

## Instructions

이 커맨드는 **AskUserQuestion 도구를 사용하여 단계별 인터뷰를 진행**한 뒤,
사용자의 선택에 따라 `init.sh`를 실행합니다.

### Phase 0: 사전 확인

1. 인자로 받은 경로를 `TARGET_PATH`로 설정
   - **인자가 없으면**: "설치할 프로젝트 경로를 입력해주세요." 라고 AskUserQuestion으로 묻는다
   - **현재 디렉토리가 하네스 레포 자체**이면: 반드시 대상 경로를 묻는다 (하네스 레포에 자기 자신을 설치하면 안 됨)
2. 해당 경로에 이미 `.harness/` 디렉토리가 있는지 확인
   - 있으면: "이미 설치되어 있습니다. 재설치(설정 변경) / 취소 중 선택하세요." 확인
   - 기존 `.harness/ouroboros/seeds/`의 시드 스펙은 보존한다 (불변 원칙)
3. 하네스 저장소 경로를 탐색 (보통 상위 디렉토리 또는 별도 위치)
   - `init.sh` 파일이 있는 디렉토리를 `HARNESS_REPO`로 기록
   - 찾지 못하면: "하네스 저장소 경로를 입력해주세요." 라고 묻는다

### Phase 1: 핵심 선택 (Round 1)

AskUserQuestion을 호출하여 다음 3개 질문을 **한 번에** 묻는다:

```
질문 1: "어떤 버전을 설치하시겠습니까?"
  header: "Version"
  options:
    - label: "Stable (v2.0.0) (Recommended)"
      description: "검증된 안정 버전. 11 게이트, 12 커맨드, 9 에이전트, 3-tier 강제."
    - label: "Experimental (v2.1.0)"
      description: "Stable + Pair Mode (Navigator-Driver 짝프로그래밍, 독립 Test Designer). AC complexity 기반 선택적 활성화."

질문 2: "어떤 트랙을 사용하시겠습니까?"
  header: "Track"
  options:
    - label: "Lite (Recommended)"
      description: "외부 의존성 제로. bash만으로 동작. 게이트, 커맨드, 에이전트 전부 포함."
    - label: "Pro"
      description: "Lite + Python 엔진. 실시간 모호성 점수, 드리프트 모니터링, SQLite 세션, MCP 서버. Python 3.11+ 필요."

질문 3: "권한 프리셋을 선택하세요."
  header: "Permissions"
  options:
    - label: "Standard (Recommended)"
      description: "일반 개발용. 파일 읽기/쓰기/실행 허용, 위험 명령 차단."
    - label: "Strict"
      description: "프로덕션/클라이언트 프로젝트용. 모든 쓰기 작업에 확인 요구."
    - label: "Permissive"
      description: "프로토타이핑/해커톤용. 대부분의 작업 자동 허용."
```

결과를 `VERSION`, `TRACK`, `PRESET` 변수에 저장한다.

### Phase 2: 기능 선택 (Round 2)

VERSION 결과에 따라 질문을 구성한다.

**Experimental(v2.1.0)을 선택한 경우** — 4개 질문:

```
질문 4: "Pair Mode를 어떻게 설정하시겠습니까?"
  header: "Pair Mode"
  options:
    - label: "Auto (Recommended)"
      description: "AC complexity 필드에 따라 자동 판단. medium/high만 Pair Mode 활성화, low는 직접 구현."
    - label: "Always On"
      description: "모든 AC에 Pair Mode 적용. 토큰 소비 증가, 결함 방지 최대화."
    - label: "Off"
      description: "Pair Mode 비활성화. v2.0.0과 동일하게 동작."

질문 5: "추가 게이트를 활성화하시겠습니까?"
  header: "Gates"
  multiSelect: true
  options:
    - label: "기본 7개만 (Recommended)"
      description: "secrets, boundaries, structure, spec, layers, security, deps"
    - label: "+ Complexity"
      description: "함수 길이/중첩 깊이 제한"
    - label: "+ Performance"
      description: "파일 크기/번들 크기 예산"
    - label: "+ AI Antipatterns"
      description: "AI 생성 코드의 환각/반복 패턴 감지"

질문 6: "Git pre-commit hook을 설치하시겠습니까?"
  header: "Git Hooks"
  options:
    - label: "설치 (Recommended)"
      description: "커밋 전 게이트 자동 실행. 시크릿 유출, 레이어 위반 차단."
    - label: "스킵"
      description: "수동으로 게이트를 실행합니다."

질문 7: "GitHub Actions CI를 설치하시겠습니까?"
  header: "CI/CD"
  options:
    - label: "설치 (Recommended)"
      description: "PR마다 게이트 자동 실행. .github/workflows/harness-gates.yaml"
    - label: "스킵"
      description: "CI/CD 없이 로컬만 사용합니다."
```

**Stable(v2.0.0)을 선택한 경우** — 질문 4를 스킵하고 5, 6, 7만 묻는다.

결과를 `PAIR_MODE`, `EXTRA_GATES`, `HOOKS`, `CI` 변수에 저장한다.

### Phase 3: 프로젝트 설정 (Round 3)

```
질문 8: "프로젝트 스택을 어떻게 감지하시겠습니까?"
  header: "Stack"
  options:
    - label: "자동 감지 (Recommended)"
      description: "package.json, requirements.txt 등을 분석하여 자동 판별."
      preview: |
        감지 가능한 스택:
        ├── Next.js / React / Vue / Svelte
        ├── Django / FastAPI / Flask
        ├── NestJS / Express
        └── Python only / Node.js only
    - label: "수동 선택"
      description: "스택을 직접 지정합니다."
```

수동 선택 시 추가 질문:

```
질문 8-1: "프로젝트 스택을 선택하세요."
  header: "Stack"
  options:
    - label: "Next.js + Python (Django/FastAPI)"
      description: "풀스택. React 프론트 + Python 백엔드."
    - label: "Next.js + NestJS"
      description: "풀스택. React 프론트 + Node.js 백엔드."
    - label: "Python only"
      description: "Django/FastAPI/Flask 단독. API 서버 또는 스크립트."
    - label: "Node.js only"
      description: "Express/Fastify 단독. 또는 바닐라 프론트엔드."
```

### Phase 4: 확인 및 실행

모든 선택을 요약하여 사용자에게 보여준다:

```
═══ AI Harness 설치 요약 ═══════════════════════

📍 대상: {TARGET_PATH}
📦 버전: {VERSION}
🔧 트랙: {TRACK}
🔐 권한: {PRESET}
🤝 Pair Mode: {PAIR_MODE}
🚧 게이트: {기본 7개 + 추가 목록}
🪝 Git Hooks: {HOOKS}
⚙️ CI/CD: {CI}
📚 스택: {STACK}

이 설정으로 설치를 진행합니다.
```

그 후 `init.sh`를 다음과 같이 실행한다:

```bash
{HARNESS_REPO}/init.sh {TARGET_PATH} \
  --yes \
  --preset {PRESET} \
  --version {VERSION} \
  --pair-mode {PAIR_MODE} \
  --gates {GATES_LIST} \
  --no-hooks      # (HOOKS가 스킵일 때만) \
  --no-ci         # (CI가 스킵일 때만) \
  --stack {STACK}  # (수동 선택일 때만)
```

**TRACK이 Pro인 경우**, init.sh 실행 후 추가로:

```bash
{HARNESS_REPO}/pro/install.sh {TARGET_PATH}
```

### Phase 5: 설치 완료 안내

```
═══ 설치 완료 ════════════════════════════════════

✅ AI Harness Template이 설치되었습니다.

시작하기:
  /interview "만들고 싶은 것"  → 요구사항 인터뷰
  /seed                       → 불변 스펙 생성
  /run                        → Double Diamond 실행

유용한 명령:
  /unstuck                    → 막혔을 때 5개 관점 분석
  /evaluate                   → 구현 검증
  /evolve                     → 학습 및 진화

게이트 수동 실행:
  .harness/gates/check-secrets.sh
  .harness/gates/check-layers.sh
  .harness/detect-violations.sh  (전체)

문서:
  CLAUDE.md                   → 프로젝트 규칙 (수정 가능)
  ARCHITECTURE_INVARIANTS.md  → 아키텍처 불변 규칙
  .harness/gates/GATES.md     → 게이트 상세

{PAIR_MODE가 Auto 또는 Always On일 때:}
Pair Mode:
  /seed에서 AC에 complexity: medium|high를 지정하면
  /run 시 Navigator-Driver 패턴이 자동 활성화됩니다.
```
