# Methodology System Guide

> 하네스(고정 코어) + 메서드(플러그인) 아키텍처 설명서.

## 핵심 컨셉

```
┌────────────────────────────────────────────────────────────┐
│  METHODOLOGIES (플러그인 — 사용자 선택)                       │
│  ouroboros · living-spec · parallel-change · bmad-lite ·    │
│  exploration · (사용자 정의)                                 │
└────────────────────────────────────────────────────────────┘
                          ↕
┌────────────────────────────────────────────────────────────┐
│  METHODOLOGY DISPATCHER (lib/methodology.sh)                │
│  활성화 / 조합 / 충돌 검증 / 상태 관리                         │
└────────────────────────────────────────────────────────────┘
                          ↕
┌────────────────────────────────────────────────────────────┐
│  HARNESS CORE (고정 — 절대 안 바뀜)                          │
│  Gates · Boundaries · Layers · State · Hooks                │
└────────────────────────────────────────────────────────────┘
```

**원칙:**
- **하네스 코어는 고정**. 게이트·경계·레이어 분리는 메서드와 무관하게 작동.
- **메서드는 플러그인**. 추가/제거/조합이 손쉬운 단위.
- **메서드는 게이트를 *추가하거나 완화*만 함**. 코어 게이트를 끄지 못함.

## 디렉토리 구조

```
ai-harness-template/
├── methodology/
│   ├── _schema/manifest.yaml       # 메서드 매니페스트 스키마
│   ├── _registry.yaml              # 번들 메서드 레지스트리
│   └── _state.template.yaml        # 활성 상태 초기 템플릿
│
├── lib/
│   └── methodology.sh              # 디스패처 (use/compose/list/info...)
│
├── methodologies/                  # 번들 플러그인 (13종)
│   ├── ouroboros/
│   ├── living-spec/
│   ├── parallel-change/
│   ├── bmad-lite/
│   ├── exploration/
│   ├── strangler-fig/
│   ├── incident-review/
│   ├── threat-model-lite/
│   ├── observability-first/
│   ├── rfc-driven/
│   ├── tdd-strict/
│   ├── lean-mvp/
│   └── mikado-method/
│
└── commands/methodology.md         # /methodology 슬래시 커맨드
```

설치 후 (프로젝트에서):

```
.harness/
├── methodology/                    # 디스패처 사본
├── methodologies/                  # 플러그인 사본 (선택된 것만 또는 전부)
├── lib/methodology.sh              # 디스패처 sourcing 진입점
├── state/<methodology-name>.yaml   # 메서드별 상태
└── ...                             # 기존 하네스 코어 (gates/, boundaries/, ...)
```

## 매니페스트 스키마

각 메서드의 `manifest.yaml`은 메서드의 **선언적 계약**.

```yaml
schema_version: 1
name: <slug>                        # 고유 식별자
display_name: "..."
description: "..."
version: "0.1.0"
author: "..."

prerequisites:                      # 활성화 전 검증
  - type: file_exists | command_exists | env_var
    path/command/var: "..."
    message: "활성화 실패 시 사용자에게 보여줄 안내"

conflicts_with: ["other-method"]    # 동시 활성화 금지
requires: ["base-method"]           # 활성화 시 필수 동반

commands: [...]                     # 메서드 제공 슬래시 커맨드
templates: [...]                    # 템플릿 파일
personas: [...]                     # 페르소나 정의 (BMAD-lite 등)
adds_gates: [...]                   # 추가 게이트 (severity, runs_on)
relaxes_gates: [...]                # 완화 대상 (target, paths, reason)

state:
  files: [...]                      # 메서드 상태 저장 위치

hooks: {}                           # post-activate, pre-deactivate 등
tags: [...]
icon: "🎯"
docs_url: "..."

min_harness_version: "0.1.0"
```

자세한 스키마는 [methodology/_schema/manifest.yaml](../methodology/_schema/manifest.yaml).

## 디스패처 명령

```bash
# 단일 메서드 활성화
/methodology use ouroboros

# 다중 조합
/methodology compose ouroboros bmad-lite living-spec

# 현재 활성 메서드
/methodology current

# 사용 가능한 메서드 목록
/methodology list

# 메서드 상세
/methodology info <name>

# 비활성화
/methodology deactivate <name>
```

내부적으로:
- `prerequisites` 검증 (파일/커맨드/환경변수)
- `conflicts_with` 충돌 거부
- `requires` 자동 동반 활성화 (없으면 활성화 거부)
- `.harness/state/<name>.yaml` 생성/업데이트

## 충돌 정책

| 시나리오 | 정책 |
|---------|------|
| `conflicts_with` 메서드 활성화 시도 | **거부** (사용자가 먼저 비활성화 필요) |
| 같은 슬래시 커맨드 두 메서드 제공 | **first-wins** (먼저 활성화된 것 유지) |
| 같은 게이트 파일명 두 메서드 추가 | **거부** (이름 충돌, 매니페스트 수정 필요) |
| `requires`가 활성 아님 | **자동 활성화 시도**, 실패 시 거부 |

## 게이트 추가 / 완화 컨트랙트

### 추가 (`adds_gates`)

```yaml
adds_gates:
  - file: "gates/check-foo.sh"
    severity: "blocking | warning"
    runs_on: ["pre-commit", "post-edit"]
    description: "..."
```

활성화 시:
1. 메서드의 `gates/` 디렉토리에서 게이트 스크립트 찾음
2. 권한 부여 (`chmod +x`)
3. 하네스 코어 게이트 등록부에 임시 등록 (메서드 비활성화 시 자동 해제)

### 완화 (`relaxes_gates`)

```yaml
relaxes_gates:
  - target: "boundaries"           # 어떤 코어 게이트를 완화할지
    paths:
      - ".harness/exploration/spikes/<spike-id>/sandbox/**"
    reason: "..."
```

완화는 **경로 기반**. 코어 게이트가 자기 검사 대상을 결정할 때 `.harness/<methodology>/.gate-relaxation.yaml`을 읽어 자기 `target`에 해당하는 paths를 스킵.

**컨슈머 컨트랙트** (코어 게이트 작성자):

```bash
RELAX_FILE=".harness/exploration/.gate-relaxation.yaml"
if [[ -f "$RELAX_FILE" ]]; then
    # 자기 target("boundaries")에 매치되는 paths 추출
    # 매치되는 파일은 검사 스킵
fi
```

## 상태 파일

각 메서드는 `.harness/state/<name>.yaml`로 활성화/세팅 상태를 영속화.

예: `.harness/state/exploration.yaml`

```yaml
methodology: exploration
activated_at: "2026-04-29T15:00:00Z"
version: "0.1.0"
config: {}
```

전역 활성 메서드 목록: `.harness/state/active.yaml`

```yaml
active:
  - name: ouroboros
    activated_at: "..."
  - name: bmad-lite
    activated_at: "..."
conflict_policy: first-wins
```

## 사용자 정의 메서드 추가

### 1. 매니페스트 작성

```yaml
# methodologies/my-method/manifest.yaml
schema_version: 1
name: my-method
display_name: "My Custom Method"
version: "0.1.0"
prerequisites: []
conflicts_with: []
requires: ["ouroboros"]
commands:
  - name: "/my-cmd"
    file: "commands/my-cmd.md"
    description: "..."
templates: []
personas: []
adds_gates: []
relaxes_gates: []
state: { files: [] }
hooks: {}
tags: []
min_harness_version: "0.1.0"
```

### 2. 레지스트리에 등록

```yaml
# methodology/_registry.yaml
methodologies:
  ...
  - name: my-method
    path: methodologies/my-method
    enabled: true
    bundled: false
```

### 3. 검증

```bash
/methodology list                    # my-method가 보여야 함
/methodology info my-method          # 매니페스트 검증 오류 없어야 함
/methodology use my-method           # 활성화 시도
```

## 디버깅

### 메서드가 활성화 안 됨

```bash
# 1. 매니페스트 스키마 검증
python3 -c "import yaml; print(yaml.safe_load(open('methodologies/my-method/manifest.yaml')))"

# 2. prerequisites 확인
/methodology info my-method | grep -A5 prerequisites

# 3. conflicts 확인
/methodology current
# 충돌하는 메서드가 활성 중이면 deactivate 후 재시도
```

### 게이트가 의외로 작동/미작동

```bash
# 1. 추가 게이트 등록 확인
ls .harness/methodologies/<name>/gates/

# 2. 완화 설정 확인
cat .harness/<name>/.gate-relaxation.yaml

# 3. 게이트 직접 실행
.harness/methodologies/<name>/gates/check-foo.sh
```

## 진화 계획

| 버전 | 추가 |
|-----|------|
| v0.1 (현재) | 13종 번들 (ouroboros~rfc-driven~tdd-strict~lean-mvp~mikado-method), prerequisites/conflicts/requires, adds_gates 동작, relaxes_gates 컨트랙트 정의 |
| v0.2 | relaxes_gates 자동 소비 (코어 게이트 업데이트), 메서드 hot-swap, 메서드 마켓플레이스 후보 |
| v0.3 | 메서드 자동 추천 (`/methodology suggest`), 프로젝트 분석 기반 |

## FAQ

**Q. 메서드 없이 하네스만 쓸 수 있나?**
A. 가능. 메서드는 선택. 단, ouroboros가 기본 활성화되도록 설계되어 있음 (`/methodology deactivate ouroboros`로 끌 수 있지만 비추천).

**Q. 메서드 변경하면 기존 산출물(`.harness/ouroboros/seeds/...`) 어떻게 됨?**
A. 메서드는 산출물을 건드리지 않음. 활성화/비활성화는 워크플로우만 바꿈. 시드/스토리/스파이크는 그대로 남음.

**Q. 여러 메서드의 게이트가 같은 파일을 검사하면 어떻게 됨?**
A. 모두 실행. 하나라도 blocking이면 차단. warning은 모두 출력.

**Q. 메서드 비활성화 후 다시 활성화하면 상태 복구되나?**
A. `state/<name>.yaml`이 보존되어 있으면 복구. 의도적으로 초기화하려면 파일 삭제 후 재활성화.

**Q. 우리 회사 내부용 메서드 만들 수 있나?**
A. 가능. `methodologies/<our-name>/`에 매니페스트+자산 두고 `_registry.yaml`에 등록. `bundled: false`로 표시.
