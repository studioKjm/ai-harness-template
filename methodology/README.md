# Methodology System

이 디렉토리는 **하네스의 메서드 플러그인 디스패처**입니다. 실제 메서드 본체는 한 단계 위 `methodologies/`(복수형)에 있습니다.

## 디렉토리 역할

| 경로 | 역할 |
|------|------|
| `methodology/` (this dir) | 디스패처 — registry, state, schema 보관 |
| `methodologies/<name>/` | 실 메서드 플러그인 본체 |
| `lib/methodology.sh` | 디스패처 셸 라이브러리 |
| `commands/methodology.md` | `/methodology` 슬래시 명령 정의 |

## 핵심 정신 모델

```
하네스 코어 (게이트·훅·구조)  ← 고정 (사용자 선택 X)
        ↑
메서드 (워크플로우)            ← 선택 (상황별 활성/조합)
        ↑
실제 작업
```

게이트는 OS, 메서드는 앱. 메서드가 바뀌어도 게이트는 항상 강제됨.

## 파일 구성

- `_schema/manifest.yaml` — 메서드 manifest 스키마(v1). 새 메서드 만들 때 참고.
- `_registry.yaml` — 번들된 메서드 목록. 사용자 커스텀 메서드도 여기 추가.
- `_state.template.yaml` — 초기 state 템플릿. `init.sh`가 `.harness/methodology/_state.yaml`로 복사.

## 번들된 메서드 (5종)

| 메서드 | 설명 | 시나리오 |
|--------|------|---------|
| `ouroboros` | Specification-First (default) | 0→1 신규 프로젝트 |
| `living-spec` | Spec evolution | 1→N 추가 개발 (seed-v1 존재) |
| `parallel-change` | Expand/migrate/contract | 호환 깨는 변경 (DB 스키마 등) |
| `bmad-lite` | BMAD persona augmentation | 분석/UX/PM 단계 강화 |
| `exploration` | R&D mode (gates relaxed) | 학습·프로토타이핑 |

## 사용

```
/methodology list                  # 목록
/methodology use living-spec       # 활성화
/methodology compose ouroboros living-spec   # 조합
/methodology current               # 현재 상태
/methodology info <name>           # 상세
/methodology deactivate <name>     # 비활성
```

## 커스텀 메서드 만들기

1. `methodologies/<your-name>/` 디렉토리 생성
2. `manifest.yaml` 작성 (스키마: `_schema/manifest.yaml` 참고)
3. `_registry.yaml`에 항목 추가
4. `/methodology list` 로 확인

권장 구조:
```
methodologies/<your-name>/
├── manifest.yaml
├── commands/                  # 슬래시 명령 .md
├── templates/                 # yaml/markdown 템플릿
├── gates/                     # .sh 게이트 (활성 시 추가됨)
├── personas/                  # 에이전트 페르소나 .md
└── README.md
```

## 의존성

디스패처는 `yq` 또는 `python3 + pyyaml` 중 하나가 있어야 동작합니다. macOS/Linux 표준 환경엔 `python3`이 있으므로 별도 설치 불필요.
